from __future__ import annotations

import os
from typing import List, Optional
from datetime import datetime

from fastapi import FastAPI, Form, Request, Depends, HTTPException, Security, Header
from fastapi.responses import PlainTextResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from qs.notify.twilio_client import send_sms
from qs.utils.logger import get_logger
from .commands import handle_command

logger = get_logger(__name__)

try:
    from .auth import get_current_user, verify_api_key, create_api_key, require_permission
    AUTH_AVAILABLE = True
except ImportError:
    AUTH_AVAILABLE = False
    logger.warning("Auth module not available")

# Rate limiting
try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded
    RATE_LIMIT_AVAILABLE = True
except ImportError:
    RATE_LIMIT_AVAILABLE = False
    logger.warning("Rate limiting not available")

# Error tracking
try:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    SENTRY_AVAILABLE = True
except ImportError:
    SENTRY_AVAILABLE = False
    logger.warning("Sentry not available")

ALLOWED_NUMBERS: List[str] = [n.strip() for n in os.getenv("TWILIO_ALLOWED_NUMBERS", "").split(',') if n.strip()]

app = FastAPI(
    title="QS Trading System API",
    description="Quantitative Trading System API with real-time market analysis",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Initialize Sentry (if available)
if SENTRY_AVAILABLE:
    sentry_dsn = os.getenv("SENTRY_DSN")
    if sentry_dsn:
        sentry_sdk.init(
            dsn=sentry_dsn,
            integrations=[FastApiIntegration()],
            traces_sample_rate=0.1,
            environment=os.getenv("ENVIRONMENT", "development")
        )
        logger.info("Sentry error tracking initialized")

# Rate limiting
if RATE_LIMIT_AVAILABLE:
    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    logger.info("Rate limiting enabled")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer(auto_error=False)


@app.get("/health")
def health():
    """Health check endpoint."""
    from qs.db import get_engine
    from qs.config import get_settings
    
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }
    
    # Check database
    try:
        engine = get_engine()
        with engine.begin() as conn:
            conn.execute("SELECT 1")
        health_status["database"] = "connected"
    except Exception as e:
        health_status["database"] = f"error: {str(e)}"
        health_status["status"] = "degraded"
    
    # Check settings
    try:
        settings = get_settings()
        health_status["config"] = "loaded"
    except Exception as e:
        health_status["config"] = f"error: {str(e)}"
        health_status["status"] = "degraded"
    
    status_code = 200 if health_status["status"] == "healthy" else 503
    return JSONResponse(content=health_status, status_code=status_code)


@app.get("/health/detailed")
def health_detailed():
    """Detailed health check with system metrics."""
    from qs.db import get_engine
    from sqlalchemy import text
    import psutil
    import os
    
    health = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "system": {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent
        },
        "database": {},
        "services": {}
    }
    
    # Database metrics
    try:
        engine = get_engine()
        with engine.begin() as conn:
            # Count records
            result = conn.execute(text("SELECT COUNT(*) as cnt FROM prices")).fetchone()
            health["database"]["prices_count"] = result[0] if result else 0
            
            result = conn.execute(text("SELECT COUNT(*) as cnt FROM signals")).fetchone()
            health["database"]["signals_count"] = result[0] if result else 0
            
            # Latest data date
            result = conn.execute(text("SELECT MAX(date) as latest FROM prices")).fetchone()
            health["database"]["latest_date"] = str(result[0]) if result and result[0] else None
            
        health["database"]["status"] = "connected"
    except Exception as e:
        health["database"]["status"] = f"error: {str(e)}"
        health["status"] = "degraded"
    
    # Service checks
    health["services"]["twilio"] = "configured" if os.getenv("TWILIO_ACCOUNT_SID") else "not_configured"
    
    return health


@app.post("/twilio/sms", response_class=PlainTextResponse)
async def twilio_sms(request: Request, From: str = Form(...), Body: str = Form(...)):
    """Twilio webhook endpoint for SMS commands."""
    if ALLOWED_NUMBERS and From not in ALLOWED_NUMBERS:
        return "unauthorized"

    kind, reply = handle_command(Body)
    # Try sending SMS; ignore failure (e.g., creds not configured)
    send_sms(From, reply)
    return reply


@app.get("/api/v1/status")
def api_status(user: dict = Depends(get_current_user) if AUTH_AVAILABLE else None):
    """Get system status (requires authentication)."""
    return {
        "status": "operational",
        "timestamp": datetime.now().isoformat(),
        "user": user.get("user_id") if user else "anonymous"
    }


@app.post("/api/v1/api-keys")
def create_api_key_endpoint(name: str, user: dict = Depends(require_permission("admin")) if AUTH_AVAILABLE else None):
    """Create new API key (admin only)."""
    if not AUTH_AVAILABLE:
        raise HTTPException(status_code=501, detail="Authentication not configured")
    key = create_api_key(name)
    return {"api_key": key, "name": name}


@app.get("/api/v1/signals")
def get_signals(
    request: Request,
    signal_name: str = "xgb_alpha",
    limit: int = 10,
    api_key: Optional[str] = Header(None, alias="X-API-Key")
):
    """Get latest signals (API key or JWT auth)."""
    # Verify authentication (if enabled)
    if AUTH_AVAILABLE:
        if api_key:
            if not verify_api_key(api_key):
                raise HTTPException(status_code=401, detail="Invalid API key")
        else:
            # Try JWT auth
            try:
                user = get_current_user()
            except:
                raise HTTPException(status_code=401, detail="Authentication required")
    
    # Use cache if available
    from qs.cache import get_cache
    
    cache = get_cache()
    cache_key = f"signals:{signal_name}:{limit}"
    cached_result = cache.get(cache_key)
    if cached_result:
        return cached_result
    
    from qs.db import get_engine
    from sqlalchemy import text
    import pandas as pd
    
    engine = get_engine()
    with engine.begin() as conn:
        df = pd.read_sql(
            text("""
                SELECT s.symbol, s.date, s.score, p.adj_close as price
                FROM signals s
                JOIN prices p ON s.symbol = p.symbol AND s.date = p.date
                WHERE s.signal_name = :name
                ORDER BY s.date DESC, s.score DESC
                LIMIT :limit
            """),
            conn,
            params={"name": signal_name, "limit": limit}
        )
    
    result = df.to_dict(orient="records")
    cache.set(cache_key, result, ttl=300)  # Cache for 5 minutes
    return result


# WebSocket endpoints
from fastapi import WebSocket, WebSocketDisconnect
try:
    from qs.websocket.streaming import manager
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False

# Order management endpoints
try:
    from qs.api.orders import router as orders_router
    app.include_router(orders_router)
except ImportError:
    logger.warning("Order management endpoints not available")

# Risk management endpoints
try:
    from qs.api.risk import router as risk_router
    app.include_router(risk_router)
except ImportError:
    logger.warning("Risk management endpoints not available")

import asyncio

@app.websocket("/ws/prices")
async def websocket_prices(websocket: WebSocket):
    """WebSocket endpoint for real-time price streaming."""
    if not WEBSOCKET_AVAILABLE:
        await websocket.close(code=1003, reason="WebSocket not available")
        return
    
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            
            if data.get("action") == "subscribe":
                symbol = data.get("symbol")
                if symbol:
                    manager.subscribe(websocket, symbol)
                    await manager.send_personal_message({
                        "type": "subscribed",
                        "symbol": symbol
                    }, websocket)
            
            elif data.get("action") == "unsubscribe":
                symbol = data.get("symbol")
                if symbol:
                    manager.unsubscribe(websocket, symbol)
                    await manager.send_personal_message({
                        "type": "unsubscribed",
                        "symbol": symbol
                    }, websocket)
            
            elif data.get("action") == "ping":
                await manager.send_personal_message({
                    "type": "pong",
                    "timestamp": datetime.now().isoformat()
                }, websocket)
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


@app.websocket("/ws/signals")
async def websocket_signals(websocket: WebSocket):
    """WebSocket endpoint for real-time signal streaming."""
    if not WEBSOCKET_AVAILABLE:
        await websocket.close(code=1003, reason="WebSocket not available")
        return
    
    await manager.connect(websocket)
    try:
        # Send initial signals
        from qs.db import get_engine
        from sqlalchemy import text
        import pandas as pd
        
        engine = get_engine()
        with engine.begin() as conn:
            df = pd.read_sql(
                text("""
                    SELECT s.symbol, s.score, p.adj_close as price
                    FROM signals s
                    JOIN prices p ON s.symbol = p.symbol AND s.date = p.date
                    WHERE s.signal_name = 'xgb_alpha'
                    AND s.date = (SELECT MAX(date) FROM signals WHERE signal_name = 'xgb_alpha')
                    ORDER BY s.score DESC
                    LIMIT 10
                """),
                conn
            )
        
        await manager.send_personal_message({
            "type": "signals",
            "data": df.to_dict(orient="records"),
            "timestamp": datetime.now().isoformat()
        }, websocket)
        
        # Keep connection alive
        while True:
            await asyncio.sleep(60)  # Send updates every minute
            # Signal updates are handled by background task
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)
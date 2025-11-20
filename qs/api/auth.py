from __future__ import annotations

import os
import jwt
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional
from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from .server import app

# Simple API key storage (in production, use database)
API_KEYS: dict[str, dict] = {}
JWT_SECRET = os.getenv("JWT_SECRET", secrets.token_urlsafe(32))
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

security = HTTPBearer()


def create_api_key(name: str, permissions: list[str] = None) -> str:
    """Create a new API key."""
    api_key = secrets.token_urlsafe(32)
    API_KEYS[api_key] = {
        'name': name,
        'permissions': permissions or ['read', 'write'],
        'created_at': datetime.now()
    }
    return api_key


def verify_api_key(api_key: str) -> bool:
    """Verify API key exists and is valid."""
    return api_key in API_KEYS


def create_jwt_token(user_id: str, permissions: list[str] = None) -> str:
    """Create JWT token."""
    payload = {
        'user_id': user_id,
        'permissions': permissions or ['read'],
        'exp': datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_jwt_token(token: str) -> dict:
    """Verify and decode JWT token."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)) -> dict:
    """Get current authenticated user from JWT."""
    token = credentials.credentials
    payload = verify_jwt_token(token)
    return payload


def require_permission(permission: str):
    """Decorator to require specific permission."""
    def permission_checker(user: dict = Depends(get_current_user)) -> dict:
        if permission not in user.get('permissions', []):
            raise HTTPException(status_code=403, detail=f"Permission '{permission}' required")
        return user
    return permission_checker


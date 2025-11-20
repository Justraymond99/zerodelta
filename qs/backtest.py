from __future__ import annotations

import numpy as np
import pandas as pd
from sqlalchemy import text

from .db import get_engine


def _compute_max_drawdown(equity: pd.Series) -> tuple[float, pd.Series]:
    """Compute max drawdown and drawdown series."""
    peak = equity.cummax()
    drawdown = equity / peak - 1.0
    return float(drawdown.min()), drawdown


def _sharpe_ratio(returns: pd.Series, freq: int = 252) -> float:
    if returns.std(ddof=0) == 0 or returns.empty:
        return 0.0
    return float((returns.mean() / returns.std(ddof=0)) * np.sqrt(freq))


def _sortino_ratio(returns: pd.Series, freq: int = 252, target: float = 0.0) -> float:
    """Sortino ratio (downside deviation only)."""
    downside_returns = returns[returns < target]
    if len(downside_returns) == 0 or downside_returns.std(ddof=0) == 0:
        return 0.0
    downside_std = downside_returns.std(ddof=0)
    return float((returns.mean() - target) / downside_std * np.sqrt(freq))


def _calmar_ratio(returns: pd.Series, max_dd: float, freq: int = 252) -> float:
    """Calmar ratio (annual return / max drawdown)."""
    if max_dd == 0:
        return 0.0
    annual_return = returns.mean() * freq
    return float(annual_return / abs(max_dd))


def _win_rate(returns: pd.Series) -> float:
    """Percentage of positive returns."""
    if len(returns) == 0:
        return 0.0
    return float((returns > 0).sum() / len(returns))


def _average_win_loss(returns: pd.Series) -> dict[str, float]:
    """Average win and average loss."""
    wins = returns[returns > 0]
    losses = returns[returns < 0]
    return {
        'avg_win': float(wins.mean()) if len(wins) > 0 else 0.0,
        'avg_loss': float(losses.mean()) if len(losses) > 0 else 0.0,
        'win_loss_ratio': float(abs(wins.mean() / losses.mean())) if len(losses) > 0 and losses.mean() != 0 else 0.0
    }


def _beta_alpha(portfolio_returns: pd.Series, benchmark_returns: pd.Series, risk_free_rate: float = 0.0, freq: int = 252) -> dict[str, float]:
    """Calculate beta and alpha relative to benchmark."""
    if len(portfolio_returns) != len(benchmark_returns) or len(portfolio_returns) < 2:
        return {'beta': 0.0, 'alpha': 0.0}
    
    # Align indices
    aligned = pd.DataFrame({'portfolio': portfolio_returns, 'benchmark': benchmark_returns}).dropna()
    if len(aligned) < 2:
        return {'beta': 0.0, 'alpha': 0.0}
    
    portfolio = aligned['portfolio']
    benchmark = aligned['benchmark']
    
    # Beta = Cov(portfolio, benchmark) / Var(benchmark)
    covariance = np.cov(portfolio, benchmark)[0, 1]
    benchmark_variance = benchmark.var()
    
    if benchmark_variance == 0:
        beta = 0.0
    else:
        beta = float(covariance / benchmark_variance)
    
    # Alpha = Portfolio return - (Risk-free rate + Beta * (Benchmark return - Risk-free rate))
    portfolio_annual = portfolio.mean() * freq
    benchmark_annual = benchmark.mean() * freq
    alpha = float(portfolio_annual - (risk_free_rate + beta * (benchmark_annual - risk_free_rate)))
    
    return {'beta': beta, 'alpha': alpha}


def _information_ratio(portfolio_returns: pd.Series, benchmark_returns: pd.Series, freq: int = 252) -> float:
    """Information ratio (excess return / tracking error)."""
    if len(portfolio_returns) != len(benchmark_returns):
        return 0.0
    
    aligned = pd.DataFrame({'portfolio': portfolio_returns, 'benchmark': benchmark_returns}).dropna()
    if len(aligned) < 2:
        return 0.0
    
    excess_returns = aligned['portfolio'] - aligned['benchmark']
    tracking_error = excess_returns.std(ddof=0)
    
    if tracking_error == 0:
        return 0.0
    
    return float(excess_returns.mean() / tracking_error * np.sqrt(freq))


def backtest_signal(
    signal_name: str = "xgb_alpha",
    top_n: int = 5,
    fee: float = 0.0005,
    slip: float = 0.0005,
    benchmark_symbol: str | None = None,
    risk_free_rate: float = 0.0,
    return_equity_curve: bool = False,
    realistic_execution: bool = True,
    market_impact: bool = True
) -> dict:
    engine = get_engine()
    with engine.begin() as conn:
        px = pd.read_sql(text("SELECT symbol, date, adj_close FROM prices"), conn)
        sig = pd.read_sql(text("SELECT symbol, date, score FROM signals WHERE signal_name = :name"), conn, params={"name": signal_name})
    if px.empty or sig.empty:
        return {}

    prices = px.pivot(index='date', columns='symbol', values='adj_close').sort_index()
    scores = sig.pivot(index='date', columns='symbol', values='score').reindex(index=prices.index).fillna(0.0)

    # daily returns
    rets = prices.pct_change().fillna(0.0)

    # rank-based weights
    ranks = scores.rank(axis=1, ascending=False, method='first')
    weights = (ranks <= top_n).astype(float)
    weights = weights.div(weights.sum(axis=1), axis=0).fillna(0.0)

    # apply transaction costs on weight changes (approximate turnover cost)
    weight_change = weights.diff().abs().fillna(0.0)
    turnover = weight_change.sum(axis=1)

    gross_port_rets = (weights.shift(1).fillna(0.0) * rets).sum(axis=1)
    
    # Enhanced execution costs
    if realistic_execution:
        # Market impact model
        if market_impact:
            from ..execution.quality import ExecutionQualityAnalyzer
            analyzer = ExecutionQualityAnalyzer()
            
            # Estimate market impact for each trade
            impact_costs = []
            for date in weights.index:
                date_weights = weights.loc[date]
                prev_weights = weights.shift(1).fillna(0.0).loc[date]
                weight_changes = (date_weights - prev_weights).abs()
                
                date_impact = 0
                for symbol in date_weights.index:
                    if weight_changes[symbol] > 0.001:  # Significant change
                        price = prices.loc[date, symbol] if symbol in prices.columns else 0
                        if price > 0:
                            # Estimate quantity
                            portfolio_value = 100000  # Default
                            quantity = (weight_changes[symbol] * portfolio_value) / price
                            impact = analyzer.calculate_market_impact(symbol, quantity, price)
                            date_impact += impact / portfolio_value
                
                impact_costs.append(date_impact)
            
            impact_series = pd.Series(impact_costs, index=weights.index)
        else:
            impact_series = pd.Series(0.0, index=weights.index)
        
        # Combine costs
        costs = turnover * (fee + slip) + impact_series
    else:
        costs = turnover * (fee + slip)
    
    port_rets = gross_port_rets - costs

    equity = (1.0 + port_rets).cumprod()
    max_dd, drawdown_series = _compute_max_drawdown(equity)

    # Basic stats
    stats = {
        'total_return': float(equity.iloc[-1] - 1.0),
        'annualized_return': float(port_rets.mean() * 252),
        'sharpe': _sharpe_ratio(port_rets),
        'sortino': _sortino_ratio(port_rets),
        'calmar': _calmar_ratio(port_rets, max_dd),
        'max_drawdown': max_dd,
        'turnover': float(turnover.mean()),
        'volatility': float(port_rets.std() * np.sqrt(252)),
        'win_rate': _win_rate(port_rets),
        'days': int(len(port_rets)),
    }
    
    # Win/loss stats
    win_loss = _average_win_loss(port_rets)
    stats.update(win_loss)
    
    # Benchmark comparison
    if benchmark_symbol and benchmark_symbol in prices.columns:
        benchmark_rets = prices[benchmark_symbol].pct_change().fillna(0.0)
        benchmark_rets = benchmark_rets.reindex(port_rets.index).fillna(0.0)
        
        beta_alpha = _beta_alpha(port_rets, benchmark_rets, risk_free_rate)
        stats['beta'] = beta_alpha['beta']
        stats['alpha'] = beta_alpha['alpha']
        stats['information_ratio'] = _information_ratio(port_rets, benchmark_rets)
    
    # Return equity curve if requested
    if return_equity_curve:
        stats['equity_curve'] = equity.to_dict()
        stats['drawdown_series'] = drawdown_series.to_dict()
        stats['returns'] = port_rets.to_dict()
        stats['weights'] = weights.to_dict()
    
    return stats
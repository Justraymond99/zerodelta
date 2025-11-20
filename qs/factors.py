from __future__ import annotations

import pandas as pd
import numpy as np
from typing import Dict
from .db import get_engine
from sqlalchemy import text


def fama_french_factors(
    returns: pd.DataFrame,
    market_returns: pd.Series,
    size_factor: pd.Series | None = None,
    value_factor: pd.Series | None = None
) -> Dict[str, float]:
    """
    Calculate Fama-French factor loadings.
    
    Parameters:
    -----------
    returns : pd.DataFrame
        Asset returns (dates x assets)
    market_returns : pd.Series
        Market returns
    size_factor : pd.Series, optional
        Size factor (SMB - Small Minus Big)
    value_factor : pd.Series, optional
        Value factor (HML - High Minus Low)
    
    Returns:
    --------
    dict
        Factor loadings: beta, alpha, smb, hml
    """
    # Align returns
    aligned = pd.DataFrame({
        'asset': returns.mean(axis=1),  # Portfolio return
        'market': market_returns
    }).dropna()
    
    if len(aligned) < 2:
        return {'beta': 0.0, 'alpha': 0.0, 'smb': 0.0, 'hml': 0.0}
    
    # Market model (CAPM)
    covariance = np.cov(aligned['asset'], aligned['market'])[0, 1]
    market_variance = aligned['market'].var()
    beta = covariance / market_variance if market_variance > 0 else 0.0
    
    # Alpha
    alpha = aligned['asset'].mean() - beta * aligned['market'].mean()
    
    result = {'beta': float(beta), 'alpha': float(alpha)}
    
    # Add SMB and HML if provided
    if size_factor is not None:
        aligned_smb = pd.DataFrame({
            'asset': returns.mean(axis=1),
            'smb': size_factor
        }).dropna()
        if len(aligned_smb) > 1:
            smb_cov = np.cov(aligned_smb['asset'], aligned_smb['smb'])[0, 1]
            smb_var = aligned_smb['smb'].var()
            result['smb'] = float(smb_cov / smb_var) if smb_var > 0 else 0.0
        else:
            result['smb'] = 0.0
    
    if value_factor is not None:
        aligned_hml = pd.DataFrame({
            'asset': returns.mean(axis=1),
            'hml': value_factor
        }).dropna()
        if len(aligned_hml) > 1:
            hml_cov = np.cov(aligned_hml['asset'], aligned_hml['hml'])[0, 1]
            hml_var = aligned_hml['hml'].var()
            result['hml'] = float(hml_cov / hml_var) if hml_var > 0 else 0.0
        else:
            result['hml'] = 0.0
    
    return result


def risk_factor_decomposition(
    returns: pd.DataFrame,
    factors: pd.DataFrame
) -> pd.DataFrame:
    """
    Decompose returns into risk factors.
    
    Parameters:
    -----------
    returns : pd.DataFrame
        Asset returns (dates x assets)
    factors : pd.DataFrame
        Factor returns (dates x factors)
    
    Returns:
    --------
    pd.DataFrame
        Factor loadings for each asset
    """
    from sklearn.linear_model import LinearRegression
    
    loadings = []
    
    for asset in returns.columns:
        asset_returns = returns[asset].dropna()
        
        # Align with factors
        aligned = pd.DataFrame({
            'asset': asset_returns,
            **{f: factors[f] for f in factors.columns}
        }).dropna()
        
        if len(aligned) < len(factors.columns) + 1:
            continue
        
        # Regression
        X = aligned[factors.columns].values
        y = aligned['asset'].values
        
        model = LinearRegression()
        model.fit(X, y)
        
        loadings.append({
            'asset': asset,
            **{f: float(model.coef_[i]) for i, f in enumerate(factors.columns)},
            'alpha': float(model.intercept_),
            'r_squared': float(model.score(X, y))
        })
    
    return pd.DataFrame(loadings)


from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.mixture import GaussianMixture
from typing import Literal


def detect_regime(
    returns: pd.Series,
    n_regimes: int = 3,
    method: Literal["gmm", "volatility"] = "gmm"
) -> pd.Series:
    """
    Detect market regime from returns.
    
    Parameters:
    -----------
    returns : pd.Series
        Returns series
    n_regimes : int
        Number of regimes to detect (default: 3)
    method : str
        "gmm" (Gaussian Mixture Model) or "volatility" (volatility-based)
    
    Returns:
    --------
    pd.Series
        Regime labels (0, 1, 2, ...)
    """
    if method == "gmm":
        # Use GMM to cluster returns
        X = returns.values.reshape(-1, 1)
        gmm = GaussianMixture(n_components=n_regimes, random_state=42)
        labels = gmm.fit_predict(X)
        return pd.Series(labels, index=returns.index)
    
    else:  # volatility-based
        # Calculate rolling volatility
        vol = returns.rolling(window=20).std()
        
        # Classify regimes based on volatility percentiles
        vol_low = vol.quantile(0.33)
        vol_high = vol.quantile(0.67)
        
        regimes = pd.Series(0, index=returns.index)  # Low vol
        regimes[vol > vol_high] = 2  # High vol
        regimes[(vol > vol_low) & (vol <= vol_high)] = 1  # Medium vol
        
        return regimes


def regime_characteristics(
    returns: pd.Series,
    regimes: pd.Series
) -> pd.DataFrame:
    """
    Calculate characteristics of each regime.
    
    Parameters:
    -----------
    returns : pd.Series
        Returns series
    regimes : pd.Series
        Regime labels
    
    Returns:
    --------
    pd.DataFrame
        Characteristics per regime
    """
    results = []
    
    for regime_id in sorted(regimes.unique()):
        regime_returns = returns[regimes == regime_id]
        
        results.append({
            'regime': int(regime_id),
            'count': len(regime_returns),
            'mean_return': regime_returns.mean(),
            'volatility': regime_returns.std(),
            'sharpe': regime_returns.mean() / regime_returns.std() if regime_returns.std() > 0 else 0,
            'skewness': regime_returns.skew(),
            'kurtosis': regime_returns.kurtosis()
        })
    
    return pd.DataFrame(results)


def regime_transition_matrix(regimes: pd.Series) -> pd.DataFrame:
    """
    Calculate regime transition probabilities.
    
    Parameters:
    -----------
    regimes : pd.Series
        Regime labels
    
    Returns:
    --------
    pd.DataFrame
        Transition matrix
    """
    transitions = []
    
    for i in range(len(regimes) - 1):
        transitions.append((regimes.iloc[i], regimes.iloc[i + 1]))
    
    transition_df = pd.DataFrame(transitions, columns=['from', 'to'])
    transition_matrix = pd.crosstab(transition_df['from'], transition_df['to'], normalize='index')
    
    return transition_matrix


#!/usr/bin/env python3
from __future__ import annotations

import argparse
import pandas as pd
from sqlalchemy import text

from qs.options import (
    black_scholes,
    black_scholes_greeks,
    monte_carlo_option_price,
    implied_volatility,
    monte_carlo_var
)
from qs.db import get_engine
from qs.config import get_settings


def calculate_historical_volatility(symbol: str, days: int = 30) -> float | None:
    """Calculate historical volatility from price data."""
    engine = get_engine()
    with engine.begin() as conn:
        df = pd.read_sql(
            text("""
                SELECT date, adj_close 
                FROM prices 
                WHERE symbol = :sym 
                ORDER BY date DESC 
                LIMIT :days
            """),
            conn,
            params={"sym": symbol, "days": days + 1}
        )
    
    if len(df) < 2:
        return None
    
    df = df.sort_values('date')
    df['returns'] = df['adj_close'].pct_change()
    
    # Annualized volatility (assuming 252 trading days)
    volatility = df['returns'].std() * (252 ** 0.5)
    return float(volatility)


def main() -> None:
    p = argparse.ArgumentParser(description="Options pricing and analysis tools")
    subparsers = p.add_subparsers(dest='command', help='Command to run')
    
    # Black-Scholes pricing
    bs_parser = subparsers.add_parser('bs', help='Black-Scholes option pricing')
    bs_parser.add_argument('--S', type=float, required=True, help='Current stock price')
    bs_parser.add_argument('--K', type=float, required=True, help='Strike price')
    bs_parser.add_argument('--T', type=float, required=True, help='Time to expiration (years)')
    bs_parser.add_argument('--r', type=float, default=0.05, help='Risk-free rate (default: 0.05)')
    bs_parser.add_argument('--sigma', type=float, help='Volatility (if not provided, will calculate from historical data)')
    bs_parser.add_argument('--symbol', type=str, help='Symbol for historical volatility calculation')
    bs_parser.add_argument('--type', choices=['call', 'put'], default='call', help='Option type')
    bs_parser.add_argument('--greeks', action='store_true', help='Also calculate Greeks')
    
    # Monte Carlo pricing
    mc_parser = subparsers.add_parser('mc', help='Monte Carlo option pricing')
    mc_parser.add_argument('--S', type=float, required=True, help='Current stock price')
    mc_parser.add_argument('--K', type=float, required=True, help='Strike price')
    mc_parser.add_argument('--T', type=float, required=True, help='Time to expiration (years)')
    mc_parser.add_argument('--r', type=float, default=0.05, help='Risk-free rate (default: 0.05)')
    mc_parser.add_argument('--sigma', type=float, help='Volatility')
    mc_parser.add_argument('--symbol', type=str, help='Symbol for historical volatility calculation')
    mc_parser.add_argument('--type', choices=['call', 'put'], default='call', help='Option type')
    mc_parser.add_argument('--simulations', type=int, default=100000, help='Number of simulations')
    
    # Implied volatility
    iv_parser = subparsers.add_parser('iv', help='Calculate implied volatility')
    iv_parser.add_argument('--price', type=float, required=True, help='Market option price')
    iv_parser.add_argument('--S', type=float, required=True, help='Current stock price')
    iv_parser.add_argument('--K', type=float, required=True, help='Strike price')
    iv_parser.add_argument('--T', type=float, required=True, help='Time to expiration (years)')
    iv_parser.add_argument('--r', type=float, default=0.05, help='Risk-free rate (default: 0.05)')
    iv_parser.add_argument('--type', choices=['call', 'put'], default='call', help='Option type')
    
    # VaR calculation
    var_parser = subparsers.add_parser('var', help='Calculate Value at Risk using Monte Carlo')
    var_parser.add_argument('--symbol', type=str, required=True, help='Symbol to analyze')
    var_parser.add_argument('--confidence', type=float, default=0.95, help='Confidence level (default: 0.95)')
    var_parser.add_argument('--horizon', type=int, default=1, help='Time horizon in days (default: 1)')
    var_parser.add_argument('--simulations', type=int, default=10000, help='Number of simulations')
    
    args = p.parse_args()
    
    if args.command == 'bs':
        sigma = args.sigma
        if sigma is None and args.symbol:
            sigma = calculate_historical_volatility(args.symbol)
            if sigma is None:
                print(f"Error: Could not calculate volatility for {args.symbol}")
                return
            print(f"Using historical volatility for {args.symbol}: {sigma:.4f}")
        elif sigma is None:
            print("Error: Must provide --sigma or --symbol")
            return
        
        price = black_scholes(args.S, args.K, args.T, args.r, sigma, args.type)
        print(f"\nBlack-Scholes {args.type.upper()} Option Price: ${price:.4f}")
        print(f"Parameters:")
        print(f"  Stock Price (S): ${args.S:.2f}")
        print(f"  Strike Price (K): ${args.K:.2f}")
        print(f"  Time to Expiry (T): {args.T:.4f} years")
        print(f"  Risk-free Rate (r): {args.r:.4f}")
        print(f"  Volatility (σ): {sigma:.4f}")
        
        if args.greeks:
            greeks = black_scholes_greeks(args.S, args.K, args.T, args.r, sigma, args.type)
            print(f"\nGreeks:")
            print(f"  Delta: {greeks['delta']:.4f}")
            print(f"  Gamma: {greeks['gamma']:.6f}")
            print(f"  Theta: {greeks['theta']:.4f} (per day)")
            print(f"  Vega: {greeks['vega']:.4f} (per 1% vol change)")
            print(f"  Rho: {greeks['rho']:.4f} (per 1% rate change)")
    
    elif args.command == 'mc':
        sigma = args.sigma
        if sigma is None and args.symbol:
            sigma = calculate_historical_volatility(args.symbol)
            if sigma is None:
                print(f"Error: Could not calculate volatility for {args.symbol}")
                return
            print(f"Using historical volatility for {args.symbol}: {sigma:.4f}")
        elif sigma is None:
            print("Error: Must provide --sigma or --symbol")
            return
        
        result = monte_carlo_option_price(
            args.S, args.K, args.T, args.r, sigma, args.type,
            n_simulations=args.simulations
        )
        print(f"\nMonte Carlo {args.type.upper()} Option Price: ${result['price']:.4f}")
        print(f"Standard Error: ${result['std_error']:.4f}")
        print(f"95% Confidence Interval: [${result['confidence_interval_95'][0]:.4f}, ${result['confidence_interval_95'][1]:.4f}]")
        print(f"Parameters:")
        print(f"  Stock Price (S): ${args.S:.2f}")
        print(f"  Strike Price (K): ${args.K:.2f}")
        print(f"  Time to Expiry (T): {args.T:.4f} years")
        print(f"  Risk-free Rate (r): {args.r:.4f}")
        print(f"  Volatility (σ): {sigma:.4f}")
        print(f"  Simulations: {args.simulations:,}")
    
    elif args.command == 'iv':
        iv = implied_volatility(args.price, args.S, args.K, args.T, args.r, args.type)
        if iv is None:
            print("Error: Could not calculate implied volatility. Check inputs.")
            return
        print(f"\nImplied Volatility: {iv:.4f} ({iv*100:.2f}%)")
        print(f"Parameters:")
        print(f"  Market Price: ${args.price:.4f}")
        print(f"  Stock Price (S): ${args.S:.2f}")
        print(f"  Strike Price (K): ${args.K:.2f}")
        print(f"  Time to Expiry (T): {args.T:.4f} years")
        print(f"  Risk-free Rate (r): {args.r:.4f}")
        print(f"  Option Type: {args.type.upper()}")
    
    elif args.command == 'var':
        engine = get_engine()
        with engine.begin() as conn:
            df = pd.read_sql(
                text("""
                    SELECT date, adj_close 
                    FROM prices 
                    WHERE symbol = :sym 
                    ORDER BY date
                """),
                conn,
                params={"sym": args.symbol}
            )
        
        if len(df) < 2:
            print(f"Error: Not enough data for {args.symbol}")
            return
        
        df = df.sort_values('date')
        returns = df['adj_close'].pct_change().dropna().values
        
        result = monte_carlo_var(
            returns,
            confidence_level=args.confidence,
            time_horizon=args.horizon,
            n_simulations=args.simulations
        )
        
        print(f"\nValue at Risk (VaR) for {args.symbol}:")
        print(f"  {args.confidence*100:.1f}% VaR ({args.horizon}-day): {result['var']*100:.2f}%")
        print(f"  Conditional VaR (CVaR): {result['cvar']*100:.2f}%")
        print(f"  Expected Return: {result['mean']*100:.2f}%")
        print(f"  Expected Std Dev: {result['std']*100:.2f}%")
        print(f"  Simulations: {args.simulations:,}")
    
    else:
        p.print_help()


if __name__ == "__main__":
    main()


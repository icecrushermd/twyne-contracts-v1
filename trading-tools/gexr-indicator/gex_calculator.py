#!/usr/bin/env python3
"""
Dealer Gamma Exposure (GEX) calculator.

Pulls a real options chain (open interest + greeks, courtesy of ORATS via the
free Tradier API), computes dealer net gamma exposure per strike, and derives
the level set used by the companion Pine Script indicator:

  - Pivot          : prior session close of the underlying
  - GEX Flip       : zero-gamma price (where aggregate dealer gamma flips sign)
  - Call Wall      : strike with the largest positive call gamma exposure
  - Put Wall       : strike with the largest negative put gamma exposure
  - Max Pain       : strike that minimizes total option holder payout at expiry
  - Upper/Lower DPZ: dealer positioning zone bounding the flip point
  - Vol Trigger Up/Down (VU/VD): next major gamma cluster beyond each wall

This is an independent implementation based on the standard, publicly
documented dealer-gamma-exposure methodology (OI x gamma x spot^2 x 100,
Black-Scholes gamma re-priced across a spot grid to find the zero-gamma
point). It is not a reverse-engineering of any third-party indicator.

Usage:
    export TRADIER_API_TOKEN=xxxxx
    python gex_calculator.py --symbol SPX --max-expiries 4
    python gex_calculator.py --symbol NDX --max-expiries 4 --sandbox
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Optional

import urllib.request
import urllib.parse

CONTRACT_MULTIPLIER = 100.0
RISK_FREE_RATE = 0.05  # approximate, only used as a fallback for BS re-pricing

PROD_BASE = "https://api.tradier.com/v1"
SANDBOX_BASE = "https://sandbox.tradier.com/v1"


class TradierClient:
    def __init__(self, token: str, sandbox: bool = False):
        self.token = token
        self.base = SANDBOX_BASE if sandbox else PROD_BASE

    def _get(self, path: str, params: dict) -> dict:
        url = f"{self.base}{path}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def quote(self, symbol: str) -> dict:
        data = self._get("/markets/quotes", {"symbols": symbol, "greeks": "false"})
        quotes = data.get("quotes", {}).get("quote")
        if isinstance(quotes, list):
            quotes = quotes[0]
        return quotes

    def expirations(self, symbol: str) -> list[str]:
        data = self._get(
            "/markets/options/expirations",
            {"symbol": symbol, "includeAllRoots": "true", "strikes": "false"},
        )
        exp = data.get("expirations", {}).get("date")
        if exp is None:
            return []
        return exp if isinstance(exp, list) else [exp]

    def chain(self, symbol: str, expiration: str) -> list[dict]:
        data = self._get(
            "/markets/options/chains",
            {"symbol": symbol, "expiration": expiration, "greeks": "true"},
        )
        options = data.get("options", {})
        if options is None:
            return []
        opt_list = options.get("option")
        if opt_list is None:
            return []
        return opt_list if isinstance(opt_list, list) else [opt_list]


@dataclass
class StrikeGamma:
    strike: float
    call_gex: float
    put_gex: float

    @property
    def net_gex(self) -> float:
        return self.call_gex + self.put_gex


@dataclass
class GexLevels:
    symbol: str
    spot: float
    pivot: float
    gex_flip: float
    call_wall: float
    put_wall: float
    max_pain: float
    upper_dpz_low: float
    upper_dpz_high: float
    lower_dpz_low: float
    lower_dpz_high: float
    vol_trigger_up: float
    vol_trigger_down: float
    net_gex_total: float
    regime: str
    expiries_used: list[str]
    generated_at: str


def bs_gamma(spot: float, strike: float, t_years: float, iv: float, r: float = RISK_FREE_RATE) -> float:
    """Black-Scholes gamma, used to re-price gamma across a hypothetical spot grid."""
    if t_years <= 0 or iv <= 0 or spot <= 0 or strike <= 0:
        return 0.0
    d1 = (math.log(spot / strike) + (r + 0.5 * iv * iv) * t_years) / (iv * math.sqrt(t_years))
    pdf = math.exp(-0.5 * d1 * d1) / math.sqrt(2 * math.pi)
    return pdf / (spot * iv * math.sqrt(t_years))


def years_to_expiry(expiration: str, now: Optional[datetime] = None) -> float:
    now = now or datetime.now(timezone.utc)
    exp_dt = datetime.strptime(expiration, "%Y-%m-%d").replace(
        hour=21, minute=0, tzinfo=timezone.utc  # approx US market close in UTC
    )
    delta = (exp_dt - now).total_seconds() / (365.0 * 24 * 3600)
    return max(delta, 1.0 / 365.0)


def fetch_contracts(client: TradierClient, symbol: str, max_expiries: int) -> list[dict]:
    expiries = client.expirations(symbol)[:max_expiries]
    if not expiries:
        raise RuntimeError(f"No expirations returned for {symbol}. Check symbol/token.")
    contracts: list[dict] = []
    for exp in expiries:
        contracts.extend(client.chain(symbol, exp))
    return contracts, expiries


def compute_levels(symbol: str, spot: float, prior_close: float, contracts: list[dict], expiries: list[str]) -> GexLevels:
    by_strike: dict[float, StrikeGamma] = {}
    iv_by_strike_expiry: dict[tuple[float, str], float] = {}

    for c in contracts:
        strike = float(c.get("strike", 0))
        oi = float(c.get("open_interest") or 0)
        greeks = c.get("greeks") or {}
        gamma = float(greeks.get("gamma") or 0)
        iv = float(greeks.get("mid_iv") or greeks.get("smv_vol") or 0)
        side = c.get("option_type")  # "call" or "put"
        expiration = c.get("expiration_date")

        if strike <= 0 or oi <= 0 or gamma <= 0:
            continue

        gex = oi * gamma * CONTRACT_MULTIPLIER * spot * spot * 0.01

        entry = by_strike.setdefault(strike, StrikeGamma(strike, 0.0, 0.0))
        if side == "call":
            entry.call_gex += gex
        elif side == "put":
            entry.put_gex -= gex  # dealers assumed short puts -> negative gamma contribution

        if iv > 0 and expiration:
            iv_by_strike_expiry[(strike, expiration)] = iv

    if not by_strike:
        raise RuntimeError("No contracts with open interest + gamma found; cannot compute GEX.")

    strikes_sorted = sorted(by_strike.keys())
    net_gex_total = sum(s.net_gex for s in by_strike.values())

    call_wall = max(by_strike.values(), key=lambda s: s.call_gex).strike
    put_wall = min(by_strike.values(), key=lambda s: s.put_gex).strike

    gex_flip = _zero_gamma_spot(spot, strikes_sorted, contracts, expiries, iv_by_strike_expiry)

    max_pain = _max_pain(strikes_sorted, contracts)

    above = sorted(s for s in strikes_sorted if s > gex_flip)
    below = sorted((s for s in strikes_sorted if s < gex_flip), reverse=True)

    upper_dpz_low = gex_flip
    upper_dpz_high = call_wall if call_wall > gex_flip else (above[0] if above else gex_flip)
    lower_dpz_high = gex_flip
    lower_dpz_low = put_wall if put_wall < gex_flip else (below[0] if below else gex_flip)

    vol_trigger_up = next((s for s in above if s > upper_dpz_high), upper_dpz_high)
    vol_trigger_down = next((s for s in below if s < lower_dpz_low), lower_dpz_low)

    regime = "Positive Gamma (mean-reverting)" if net_gex_total > 0 else "Negative Gamma (trending)"

    return GexLevels(
        symbol=symbol,
        spot=round(spot, 2),
        pivot=round(prior_close, 2),
        gex_flip=round(gex_flip, 2),
        call_wall=round(call_wall, 2),
        put_wall=round(put_wall, 2),
        max_pain=round(max_pain, 2),
        upper_dpz_low=round(upper_dpz_low, 2),
        upper_dpz_high=round(upper_dpz_high, 2),
        lower_dpz_low=round(lower_dpz_low, 2),
        lower_dpz_high=round(lower_dpz_high, 2),
        vol_trigger_up=round(vol_trigger_up, 2),
        vol_trigger_down=round(vol_trigger_down, 2),
        net_gex_total=round(net_gex_total, 2),
        regime=regime,
        expiries_used=expiries,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )


def _zero_gamma_spot(spot, strikes, contracts, expiries, iv_by_strike_expiry) -> float:
    """Scan a hypothetical spot grid (+/-10%) and re-price gamma at each point
    using Black-Scholes to find where aggregate dealer gamma crosses zero."""
    grid = [spot * (0.90 + 0.005 * i) for i in range(41)]  # 90%-110% in 0.5% steps
    best_spot = spot
    best_abs = None

    for hyp_spot in grid:
        total = 0.0
        for c in contracts:
            strike = float(c.get("strike", 0))
            oi = float(c.get("open_interest") or 0)
            expiration = c.get("expiration_date")
            side = c.get("option_type")
            iv = iv_by_strike_expiry.get((strike, expiration), 0.0)
            if strike <= 0 or oi <= 0 or iv <= 0 or not expiration:
                continue
            t = years_to_expiry(expiration)
            gamma = bs_gamma(hyp_spot, strike, t, iv)
            gex = oi * gamma * CONTRACT_MULTIPLIER * hyp_spot * hyp_spot * 0.01
            total += gex if side == "call" else -gex

        if best_abs is None or abs(total) < best_abs:
            best_abs = abs(total)
            best_spot = hyp_spot

    return best_spot


def _max_pain(strikes: list[float], contracts: list[dict]) -> float:
    by_strike_oi = {}
    for c in contracts:
        strike = float(c.get("strike", 0))
        oi = float(c.get("open_interest") or 0)
        side = c.get("option_type")
        if strike <= 0 or oi <= 0:
            continue
        by_strike_oi.setdefault(strike, {"call": 0.0, "put": 0.0})
        by_strike_oi[strike][side] += oi

    best_strike = strikes[len(strikes) // 2]
    best_payout = None
    for candidate in strikes:
        payout = 0.0
        for strike, ois in by_strike_oi.items():
            if candidate > strike:
                payout += (candidate - strike) * ois["call"]
            if candidate < strike:
                payout += (strike - candidate) * ois["put"]
        if best_payout is None or payout < best_payout:
            best_payout = payout
            best_strike = candidate
    return best_strike


def pine_input_block(levels: GexLevels) -> str:
    return f"""
// Paste these into the GEXR indicator's manual inputs each morning
// Source: {levels.symbol}  |  Generated: {levels.generated_at}
// Expiries used: {", ".join(levels.expiries_used)}
Pivot           = {levels.pivot}
GEX Flip        = {levels.gex_flip}
Call Wall       = {levels.call_wall}
Put Wall        = {levels.put_wall}
Max Pain        = {levels.max_pain}
Upper DPZ       = [{levels.gex_flip}-{levels.upper_dpz_high}]
Lower DPZ       = [{levels.lower_dpz_low}-{levels.gex_flip}]
Vol Trigger Up  = {levels.vol_trigger_up}
Vol Trigger Down= {levels.vol_trigger_down}
Net GEX Total   = {levels.net_gex_total}
Regime          = {levels.regime}
""".strip()


def pine_csv_line(levels: GexLevels, basis_offset: float = 0.0) -> str:
    """One-line CSV for the indicator's Easy Mode paste field.
    Order: offset,pivot,gexFlip,callWall,putWall,maxPain,upperDpz,lowerDpz,volUp,volDn,regime"""
    regime = "P" if levels.net_gex_total > 0 else "N"
    return ",".join(str(x) for x in [
        basis_offset,
        levels.pivot,
        levels.gex_flip,
        levels.call_wall,
        levels.put_wall,
        levels.max_pain,
        levels.upper_dpz_high,
        levels.lower_dpz_low,
        levels.vol_trigger_up,
        levels.vol_trigger_down,
        regime,
    ])


def main():
    parser = argparse.ArgumentParser(description="Compute real dealer GEX levels from Tradier options data.")
    parser.add_argument("--symbol", required=True, help="Underlying symbol, e.g. SPX, SPY, NDX, QQQ")
    parser.add_argument("--max-expiries", type=int, default=4, help="Number of nearest expiries to aggregate")
    parser.add_argument("--sandbox", action="store_true", help="Use Tradier sandbox endpoint")
    parser.add_argument("--out", default=None, help="Write JSON output to this path")
    parser.add_argument("--basis-offset", type=float, default=0.0, help="Cash-index -> futures offset for the CSV line")
    args = parser.parse_args()

    token = os.environ.get("TRADIER_API_TOKEN")
    if not token:
        print("ERROR: set TRADIER_API_TOKEN (free at https://developer.tradier.com/)", file=sys.stderr)
        sys.exit(1)

    client = TradierClient(token, sandbox=args.sandbox)

    quote = client.quote(args.symbol)
    if not quote:
        print(f"ERROR: could not fetch quote for {args.symbol}", file=sys.stderr)
        sys.exit(1)
    spot = float(quote.get("last") or quote.get("close") or 0)
    prior_close = float(quote.get("prevclose") or spot)

    contracts, expiries = fetch_contracts(client, args.symbol, args.max_expiries)
    levels = compute_levels(args.symbol, spot, prior_close, contracts, expiries)

    print(json.dumps(asdict(levels), indent=2))
    print()
    print(pine_input_block(levels))
    print()
    print("=== EASY MODE: copy this ONE line into the indicator's 'Paste Levels (CSV)' field ===")
    print(pine_csv_line(levels, args.basis_offset))

    if args.out:
        with open(args.out, "w") as f:
            json.dump(asdict(levels), f, indent=2)


if __name__ == "__main__":
    main()

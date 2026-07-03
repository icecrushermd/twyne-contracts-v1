#!/usr/bin/env python3
"""GEX-Level aus der kostenlosen CBOE-Optionskette berechnen.

Lädt die Delayed-Quotes-Optionskette von cdn.cboe.com (kostenlos, kein
API-Key, 15 Min. verzögert — Open Interest aktualisiert ohnehin nur über
Nacht) und berechnet daraus die Level für den GEXR-Style-Matrix-Indikator:

  GEX Flip   : Nulldurchgang des kumulierten Netto-GEX über die Strikes
  Call Wall  : Strike mit dem größten positiven GEX
  Put Wall   : Strike mit dem größten negativen GEX
  Abs GEX    : Strike mit dem größten absoluten GEX
  Max Pain   : Strike mit minimalem Auszahlungswert (nächster Verfall)

Verwendung:
  python3 fetch_gex_levels.py SPY
  python3 fetch_gex_levels.py _SPX --days 30
  python3 fetch_gex_levels.py SPY --patch GEXR_Style_Matrix.pine

Mit --patch werden die Werte direkt als Voreinstellung in die Pine-Datei
geschrieben — danach nur noch den Dateiinhalt in den Pine Editor kopieren.

GEX-Formel (Standard, vgl. perfiliev.com): pro Kontrakt
  GEX = Gamma × OI × 100 × Spot² × 0.01   (Calls +, Puts −)
Annahme: Dealer sind long Calls / short Puts der Kunden (Vorzeichen-Konvention).

Nur Python-Standardbibliothek, keine Abhängigkeiten. Kein Anlagerat.
"""

import argparse
import datetime as dt
import json
import math
import re
import sys
import urllib.request

CBOE_URL = "https://cdn.cboe.com/api/global/delayed_quotes/options/{symbol}.json"
# Index-Symbole brauchen bei CBOE einen Unterstrich-Präfix
INDEX_SYMBOLS = {"SPX", "NDX", "RUT", "VIX", "XSP", "DJX", "OEX"}
OPT_RE = re.compile(r"^(?P<root>.+?)(?P<date>\d{6})(?P<cp>[CP])(?P<strike>\d{8})$")


def fetch_chain(symbol: str) -> dict:
    sym = symbol.upper()
    if sym in INDEX_SYMBOLS:
        sym = "_" + sym
    url = CBOE_URL.format(symbol=sym)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def parse_options(raw: dict, max_days: int):
    """Liefert (spot, Liste[(expiry, strike, cp, oi, gamma, iv, T_jahre)])."""
    data = raw.get("data", raw)
    spot = None
    for key in ("current_price", "close", "last", "price"):
        if data.get(key):
            spot = float(data[key])
            break
    if not spot:
        sys.exit("Fehler: Spot-Preis nicht im JSON gefunden.")

    today = dt.date.today()
    out = []
    for o in data.get("options", []):
        m = OPT_RE.match(o.get("option", ""))
        if not m:
            continue
        d = m.group("date")
        expiry = dt.date(2000 + int(d[:2]), int(d[2:4]), int(d[4:6]))
        days = (expiry - today).days
        if days < 0 or days > max_days:
            continue
        strike = int(m.group("strike")) / 1000.0
        oi = float(o.get("open_interest") or 0)
        gamma = float(o.get("gamma") or 0)
        iv = float(o.get("iv") or 0)
        if iv > 3:          # falls in Prozent geliefert
            iv /= 100.0
        t_years = max(days, 0.5) / 365.0
        out.append((expiry, strike, m.group("cp"), oi, gamma, iv, t_years))
    if not out:
        sys.exit("Fehler: keine passenden Optionen gefunden (Zeitfenster zu klein?).")
    return spot, out


def bs_gamma(s: float, k: float, sigma: float, t: float) -> float:
    """Black-Scholes-Gamma (r≈0) — identisch für Calls und Puts."""
    if s <= 0 or k <= 0 or sigma <= 0 or t <= 0:
        return 0.0
    d1 = (math.log(s / k) + 0.5 * sigma * sigma * t) / (sigma * math.sqrt(t))
    return math.exp(-0.5 * d1 * d1) / math.sqrt(2 * math.pi) / (s * sigma * math.sqrt(t))


def gamma_flip(spot: float, options: list):
    """Zero-Gamma-Level: Netto-Dealer-GEX als Funktion des Kurses (±10%),
    Nulldurchgang nächst am Spot (Perfiliev-Methode)."""
    usable = [(k, cp, oi, iv, t) for _, k, cp, oi, _, iv, t in options
              if oi > 0 and iv > 0 and t > 0]
    if not usable:
        return None
    flip, best_dist = None, float("inf")
    prev_s, prev_g = None, None
    for i in range(41):
        s = spot * (0.90 + i * 0.005)
        tot = 0.0
        for k, cp, oi, iv, t in usable:
            g = bs_gamma(s, k, iv, t) * oi * 100 * s * s * 0.01
            tot += g if cp == "C" else -g
        if prev_g is not None and prev_g * tot < 0:
            frac = abs(prev_g) / (abs(prev_g) + abs(tot))
            cross = prev_s + frac * (s - prev_s)
            if abs(cross - spot) < best_dist:
                best_dist = abs(cross - spot)
                flip = cross
        prev_s, prev_g = s, tot
    return flip


def compute_levels(spot: float, options: list):
    # Netto-GEX je Strike (Calls +, Puts −) am aktuellen Spot
    gex_by_strike: dict[float, float] = {}
    for _, strike, cp, oi, gamma, _, _ in options:
        gex = gamma * oi * 100 * spot * spot * 0.01
        gex_by_strike[strike] = gex_by_strike.get(strike, 0.0) + (gex if cp == "C" else -gex)

    strikes = sorted(gex_by_strike)
    call_wall = max(strikes, key=lambda k: gex_by_strike[k])
    put_wall = min(strikes, key=lambda k: gex_by_strike[k])
    abs_gex = max(strikes, key=lambda k: abs(gex_by_strike[k]))

    # GEX Flip über das Gamma-Profil (korrekt); Fallback: kumulierte Strikes
    flip = gamma_flip(spot, options)
    if flip is None:
        cum = 0.0
        prev_cum, prev_k = None, None
        best_dist = float("inf")
        for k in strikes:
            cum += gex_by_strike[k]
            if prev_cum is not None and prev_cum * cum < 0:
                frac = abs(prev_cum) / (abs(prev_cum) + abs(cum))
                cross = prev_k + frac * (k - prev_k)
                if abs(cross - spot) < best_dist:
                    best_dist = abs(cross - spot)
                    flip = cross
            prev_cum, prev_k = cum, k

    # Max Pain: nur der nächste Verfall
    nearest_exp = min(e for e, *_ in options)
    near = [(s, cp, oi) for e, s, cp, oi, _, _, _ in options if e == nearest_exp]
    near_strikes = sorted({s for s, _, _ in near})

    def pain(price: float) -> float:
        total = 0.0
        for s, cp, oi in near:
            if cp == "C":
                total += oi * max(0.0, price - s)
            else:
                total += oi * max(0.0, s - price)
        return total

    max_pain = min(near_strikes, key=pain)

    return {
        "spot": spot,
        "gex_flip": flip,
        "call_wall": call_wall,
        "put_wall": put_wall,
        "abs_gex": abs_gex,
        "max_pain": max_pain,
        "nearest_expiry": nearest_exp,
        "net_gex_bn": sum(gex_by_strike.values()) / 1e9,
    }


BASE_PATCH_MAP = {  # Indikator-Inputname → Level-Schlüssel
    "Max Pain": "max_pain",
    "GEX Flip": "gex_flip",
    "Call Wall": "call_wall",
    "Put Wall": "put_wall",
    "Abs GEX Strike": "abs_gex",
}


def patch_map_for(symbol: str) -> dict:
    """SPY/SPX-Level gehören in den ES-Block, QQQ/NDX in den NQ-Block."""
    s = symbol.upper().lstrip("_")
    prefix = "ES " if s in ("SPY", "SPX", "XSP") else "NQ " if s in ("QQQ", "NDX") else ""
    return {prefix + name: key for name, key in BASE_PATCH_MAP.items()}


def patch_pine(path: str, levels: dict, symbol: str) -> None:
    with open(path, encoding="utf-8") as f:
        src = f.read()
    for name, key in patch_map_for(symbol).items():
        val = levels.get(key)
        if val is None:
            continue
        pattern = re.compile(r'(input\.float\()[0-9.]+(,\s*"' + re.escape(name) + '")')
        src, n = pattern.subn(rf"\g<1>{val:g}\g<2>", src)
        if n == 0:
            print(f"Warnung: Input '{name}' nicht in {path} gefunden.")
    with open(path, "w", encoding="utf-8") as f:
        f.write(src)
    print(f"\n✔ Werte als Voreinstellung in {path} geschrieben —")
    print("  Dateiinhalt komplett in den TradingView Pine Editor kopieren, fertig.")


def main() -> None:
    ap = argparse.ArgumentParser(description="GEX-Level aus CBOE-Daten berechnen")
    ap.add_argument("symbol", help="Ticker, z.B. SPY, QQQ, _SPX (Indizes mit _)")
    ap.add_argument("--days", type=int, default=60, help="Max. Tage bis Verfall (Standard 60)")
    ap.add_argument("--patch", metavar="PINE", help="Pine-Datei mit den Werten patchen")
    args = ap.parse_args()

    raw = fetch_chain(args.symbol)
    spot, options = parse_options(raw, args.days)
    lv = compute_levels(spot, options)

    f = lambda x: f"{x:.2f}" if x is not None else "n/a"
    print(f"\n{args.symbol.upper()}  ·  Spot {f(lv['spot'])}  ·  "
          f"Netto-GEX {lv['net_gex_bn']:+.2f} Mrd$/1%  ·  "
          f"Max Pain auf Verfall {lv['nearest_expiry']}")
    print("─" * 52)
    print(f"  GEX Flip       : {f(lv['gex_flip'])}")
    print(f"  Call Wall      : {f(lv['call_wall'])}")
    print(f"  Put Wall       : {f(lv['put_wall'])}")
    print(f"  Max Pain       : {f(lv['max_pain'])}")
    print(f"  Abs GEX Strike : {f(lv['abs_gex'])}")
    print("─" * 52)
    print("→ Werte in TradingView unter 'Options-Level' eintragen")
    print("  (Pivot/VU/VD auf 0 lassen = automatisch)")

    if args.patch:
        patch_pine(args.patch, lv, args.symbol)


if __name__ == "__main__":
    main()

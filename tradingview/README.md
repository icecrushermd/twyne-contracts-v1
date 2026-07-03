# GEXR-Style Matrix PRO — Zero-Config (Pine Script v5)

Open-Source-Indikator für TradingView im Stil des geschützten "GEXR Matrix"
(TheRealDrip2Rip) — gleicher Funktionsumfang, plus Automatik-Extras.

## Installation

1. TradingView öffnen → unten **Pine Editor** aufklappen
2. Inhalt von `GEXR_Style_Matrix.pine` einfügen
3. **Speichern** → **Zum Chart hinzufügen** — fertig, keine Einstellungen nötig

## Zero-Config: erkennt das Symbol selbst

Der Indikator liest das Chart-Symbol und wählt automatisch den passenden
Options-Referenzmarkt, IV-Index und Modus — egal ob Future, Micro,
Index-CFD oder ETF:

| Chart | Referenz | IV-Index |
|---|---|---|
| ES / MES / SPX / US500 / SPY | SPY | VIX1D / VIX |
| NQ / MNQ / NDX / NAS100 / US100 / QQQ | QQQ | VXN |
| RTY / M2K / RUT / US2000 / IWM | IWM | RVX |
| YM / MYM / DJI / US30 / DIA | DIA | VXD |
| GC / MGC / GLD (Gold) | GLD | GVZ |
| SI / SIL / SLV (Silber) | SLV | VXSLV |
| CL / MCL / USO (Öl) | USO | OVX |
| BTC / MBT / BTC-Spot / IBIT | IBIT | Statistik |
| ETH / MET / ETH-Spot / ETHA | ETHA | Statistik |
| alles andere (Aktien, Forex, …) | Chart selbst | Statistik |

Futures-Level werden über das Vortagesschluss-Verhältnis zum Referenz-ETF
skaliert (inkl. Basis). Ohne passenden IV-Index schaltet der Indikator
selbstständig auf volumengewichtete Statistik-Level um. Session, Opening
Range und Dealer-Zonen ankern am US-Cash-Open (09:30 NY); Symbole ohne
NY-Handel nutzen automatisch den Tageswechsel. Das Panel zeigt unter
**"Profil:"** an, was erkannt wurde.

**Die einzigen Einstellungen:** Panel an/aus, Trend-Ribbon an/aus,
Signale an/aus, Panel-Position. Alles andere ist Automatik oder
bewährter Festwert.

## Level-Quellen (Priorität)

1. **Manuell eingetragen** (empfohlen): echte Open-Interest-Level, per
   Fetcher-Skript aus der kostenlosen CBOE-Optionskette berechnet
2. **CBOE-IV-Schätzung**: Expected Move aus VIX1D/VXN/GVZ/OVX…, SKEW-
   Asymmetrie, Put/Call-Bias — Level stehen ab der Eröffnung fest,
   kein Repaint
3. **Statistik**: volumengewichteter Flow-Anker ± Sigma-Bänder

## Morgen-Routine (2 Minuten)

```
python3 fetch_gex_levels.py SPY --patch GEXR_Style_Matrix.pine
python3 fetch_gex_levels.py QQQ --patch GEXR_Style_Matrix.pine
```

Das Skript lädt die CBOE-Kette (kostenlos, kein Account), berechnet
GEX Flip, Call/Put Wall, Max Pain und Abs GEX und schreibt sie in den
passenden Eingabe-Block (SPY→ES-Block, QQQ→NQ-Block, alles andere→
generischer Block). Danach Dateiinhalt in den Pine Editor kopieren,
speichern — ES und NQ sind gleichzeitig versorgt. Manuelle Level immer
in **Referenz-Preisen** eintragen (SPY 680, nicht ES 6800); die
Umrechnung macht der Indikator. Andere Märkte genauso, z.B.
`python3 fetch_gex_levels.py GLD --patch …` für Gold oder `IBIT` für
Bitcoin.

## Komponenten

- **Level-Matrix**: PAIN, VU, CALL, UDL, GEX, LDL, PIVOT, PUT, VD als
  beschriftete Linien; Opening-Range (ORZ H/L) intraday
- **Matrix-Panel**: FLOW (Profil, Pressure, Break, Corridor, Options,
  ATR Story, Alignment), SCENARIO ENGINE (Open/Action/Read), THE PATH
  (Bias/Sequence/Next), THE TURN (Flip-Bedingungen), LIVE STATUS,
  DEALER (Upper/Lower DPZ, Abs GEX)
- **Dealer Pressure Zones**: volumengewichteter Preis der Session-Trades
  innerhalb des oberen/unteren Gamma-Korridors
- **Trend-Ribbon + Signale**: LONG/SHORT nur bei Konfluenz aus
  Gamma-Regime, Levelbruch (GEX/UDL/LDL), Trend und RSI — mit Cooldown
- **Alerts**: Long/Short-Setup, GEX Flip verloren/zurückerobert, Pivot
  verloren/zurückerobert, Call/Put Wall getestet

## Hinweis

Kein Anlagerat. IV- und Statistik-Level sind Näherungen — für präzise
Walls morgens die Fetcher-Werte eintragen (echtes Open Interest).

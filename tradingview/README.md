# GEXR-Style Matrix PRO (Pine Script v5)

Open-Source-Indikator für TradingView im Stil des geschützten "GEXR Matrix"
(TheRealDrip2Rip) — gleicher Funktionsumfang, plus Extras.

## Installation

1. TradingView öffnen → unten **Pine Editor** aufklappen
2. Inhalt von `GEXR_Style_Matrix.pine` einfügen
3. **Speichern** → **Zum Chart hinzufügen**

## Bedienung

### Options-Level eintragen (empfohlen)

Pine Script hat keinen Zugriff auf Options-Open-Interest. Trage daher die
Level täglich aus deiner GEX-Datenquelle (z.B. GEXBot, TanukiTrade,
SpotGamma, unusualwhales) in den Indikator-Einstellungen unter
**"Options-Level"** ein:

| Feld | Bedeutung |
|---|---|
| Max Pain | Max-Pain-Strike (Magnetlevel) |
| GEX Flip | Zero-Gamma-Level — darüber positives, darunter negatives Gamma |
| Dealer Pivot | Struktureller Entscheidungslevel |
| Call Wall / Put Wall | Größte positive/negative GEX-Strikes |
| VU / VD | Volatilitäts-Trigger oben/unten (Korridor-Ränder) |
| Abs GEX Strike | Strike mit dem größten absoluten GEX |

### Auto-Modus

Felder, die auf **0** stehen, werden automatisch als statistischer Proxy
berechnet (volumengewichteter Flow-Anker ± Sigma-Bänder, klassischer
Tagespivot). So funktioniert der Indikator auch ganz ohne manuelle Eingabe —
das kann das Original nicht.

## Komponenten

- **Level-Matrix**: PAIN, VU, CALL, UDL, GEX, LDL, PIVOT, PUT, VD als
  beschriftete Linien; dazu Opening-Range-Zone (ORZ H/L) intraday
- **Matrix-Panel**: FLOW, SCENARIO ENGINE (Open/Action/Read), THE PATH
  (Bias/Sequence/Next), THE TURN (Flip-Bedingungen), LIVE STATUS, DEALER
  (Upper/Lower DPZ, Abs GEX) — Texte aktualisieren sich live
- **Dealer Pressure Zones**: volumengewichteter Preis der Trades innerhalb
  des oberen/unteren Gamma-Korridors der laufenden Session
- **Trend-Ribbon + Signale**: LONG/SHORT nur bei Konfluenz aus Gamma-Regime,
  Levelbruch (GEX/UDL/LDL), Trend und RSI — mit Cooldown
- **Alerts**: Long/Short-Setup, GEX Flip verloren/zurückerobert, Pivot
  verloren/zurückerobert, Call/Put Wall getestet

## Hinweis

Kein Anlagerat. Die Auto-Level sind statistische Näherungen, keine echten
Options-Flow-Daten — für präzise GEX-Level immer eine echte Datenquelle
eintragen.

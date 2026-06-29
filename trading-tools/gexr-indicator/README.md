# Dealer Gamma Levels (independent GEX toolkit)

A small toolkit to display **real**, options-derived dealer-gamma-exposure
levels on a TradingView chart, and to backtest a simple rule set built on
top of them.

This was built from scratch using the standard, publicly documented
dealer-gamma-exposure methodology. It is **not** a copy of, or reverse
engineering of, any third-party "protected source script" (e.g. the
commercial "GEXR Matrix" indicator on the TradingView marketplace). That
script's source is locked, so there is no way to verify what data it
actually uses internally — see "Why not just copy that script?" below.

## Why a Python step at all?

Pine Script has no outbound HTTP access. It cannot fetch an options chain
on its own — it can only read native TradingView symbol data, or data
published as a custom daily ticker ("Pine Seeds"). Real per-strike open
interest + gamma has to be fetched and computed *outside* TradingView, then
brought in.

This toolkit ships the simplest version of that pipeline:

1. `gex_calculator.py` fetches a real options chain (open interest + greeks)
   from the [Tradier](https://developer.tradier.com/) API — free, greeks
   courtesy of ORATS — and computes the level set below.
2. You paste the printed values into the Pine indicator's manual inputs
   each morning.
3. The Pine script does the rest live: draws the levels and narrates price
   action against them every bar.

A fully automated version (no manual paste) is possible via TradingView
**Pine Seeds**, see "Automating the data feed" below — it just requires a
one-time manual registration step on TradingView's side that I can't do on
your behalf.

## Why ES/NQ need a proxy underlying

ES and NQ are *futures*, not optionable in the same chain as the index
options most free data sources cover. The practical, free path is:

| Futures chart | Use options on | Why |
|---|---|---|
| ES (S&P 500 e-mini) | **SPX** or **SPY** | Same index, ES trades close to SPX cash (small basis) |
| NQ (Nasdaq-100 e-mini) | **NDX** or **QQQ** | Same index family (Nasdaq-100), *not* SPX/SPY |

Tradier's free API covers SPX, SPY, NDX and QQQ option chains. Use the
`Basis Offset` input in the Pine scripts to nudge the cash-index levels
onto the futures price scale if the futures/cash basis matters for your
timeframe (usually only relevant intraday on expiration-sensitive days).

## Methodology

For each contract in the nearest N expiries (`--max-expiries`, default 4):

- **Net GEX per strike** = `OI x gamma x spot^2 x 0.01 x 100`, calls
  counted positive (dealers assumed long calls / short gamma hedgers),
  puts counted negative.
- **GEX Flip (zero gamma)**: re-price gamma with Black-Scholes across a
  spot grid (90%-110% of current price, 0.5% steps) using each contract's
  own IV and time-to-expiry, sum signed GEX at each hypothetical spot, and
  take the spot where the aggregate crosses zero. This is the standard
  "zero gamma" construction used across the retail dealer-gamma literature.
- **Call Wall / Put Wall**: strike with the largest positive call GEX /
  largest negative put GEX (i.e. where dealer hedging flows concentrate).
- **Max Pain**: strike that minimizes total OI-weighted option holder
  payout at expiry (classic max-pain calculation).
- **Pivot**: prior session close of the underlying.
- **Upper/Lower DPZ**: zone between the GEX Flip and the next wall in each
  direction.
- **Vol Trigger Up/Down**: the next OI cluster beyond each wall — i.e.
  where, if price gets there, dealer hedging flow is expected to
  accelerate rather than pin.

None of this requires a paid data feed. It does require an options chain
with real OI + greeks, which is the part Tradier provides for free.

## GEX is a behaviour framework, not a direction signal

This is the most important idea and it drives the strategy logic. GEX tells
you whether dealer hedging is likely to **dampen or amplify** moves — it
does *not* tell you up vs down:

| Regime (vs Zero Gamma) | Dealer hedging | Expected behaviour | Tactic |
|---|---|---|---|
| **Positive gamma** (above) | sell rallies, buy dips | chop, mean reversion, lower vol | **fade the walls** back to Flip |
| **Negative gamma** (below) | buy rallies, sell dips | trend days, higher vol | **trade breakouts** to the wall |
| **Zero gamma** (near Flip) | hedging can flip | regime change, indecision | stand aside / low conviction |

GEX works best with high open interest on index products (SPY/QQQ/IWM) and
during OpEx weeks / volatility-regime transitions. It is less reliable in
thin liquidity, around major macro news, or on illiquid single names.

The Pine strategy encodes this directly: in **Auto** mode it reads the
`Net GEX Regime` value from the calculator and trades breakouts in negative
gamma but fades the walls in positive gamma. You can also force either
tactic. The indicator's status table shows the live "Expected Behaviour"
read so you can see which regime you're in at a glance.

## Setup

1. Sign up for a free Tradier Brokerage account and create an API token:
   https://developer.tradier.com/ (sandbox token works for market data
   and costs nothing — no funding required).
2. ```bash
   export TRADIER_API_TOKEN=your_token_here
   python3 gex_calculator.py --symbol NDX --max-expiries 4
   ```
   Use `--symbol SPX` (or `SPY`) for the ES chart, `--symbol NDX` (or
   `QQQ`) for the NQ chart. Add `--sandbox` if you're using a sandbox-only
   token instead of a live brokerage token.
3. Copy the printed "Paste these into the GEXR indicator" block.
4. In TradingView, add `GEXR_Indicator.pine` (Pine Editor -> New blank
   indicator -> paste -> Add to chart), open its settings, and paste the
   values into the matching inputs.
5. Re-run step 2 once per session (premarket) — dealer OI-based levels are
   a daily snapshot, not an intraday-changing feed, which is also how real
   GEX desks operate.

## Files

- `gex_calculator.py` — fetches the chain, computes the levels, prints
  JSON + a ready-to-paste Pine input block. Standard library only, no
  third-party Python packages required.
- `GEXR_Indicator.pine` — Pine v5 indicator: plots all levels, shades the
  dealer positioning zones, and renders a live status table (regime, bias,
  open/action/read narration, checkpoint state) computed from real-time
  price action against the levels you entered.
- `GEXR_Strategy.pine` — Pine v5 `strategy()` version of the same levels
  with a concrete, backtestable rule set: enter on a GEX-Flip
  reclaim/loss confirmed by the Pivot, target the opposing wall, stop
  beyond the dealer positioning zone (or an ATR fallback), flatten if the
  Flip is lost again before the stop is hit. Use TradingView's Strategy
  Tester to evaluate it before risking anything live.

I have not been able to compile-test the `.pine` files in TradingView's
own editor from this environment — paste them in and report any compiler
errors back; they're quick to fix.

## Automating the data feed (optional, later)

To remove the daily manual paste step:

1. Create a public GitHub repo following TradingView's
   [Pine Seeds](https://github.com/tradingview/pine_seeds_example) format.
2. Have `gex_calculator.py` (run on a schedule, e.g. a GitHub Action)
   commit each day's levels as a daily OHLC row per level (one "ticker" per
   level, e.g. `GEXFLIPNDX`, `CALLWALLNDX`, ...).
3. Submit your seed prefix to TradingView for approval (manual, one-time,
   on their end — see the Pine Seeds repo's README for the request
   process).
4. Once approved, the Pine script can pull each level via
   `request.security("SEED_yourprefix:GEXFLIPNDX", "1D", close)` instead of
   a manual input, refreshing automatically once per day.

This is genuinely daily-resolution only (Pine Seeds doesn't support
intraday pushes), but that matches how the levels actually behave anyway —
they're computed from end-of-day open interest and held static through the
session.

## Disclaimer

This is a tool for studying dealer positioning, not financial advice. The
zero-gamma/wall/max-pain levels are theoretical constructs based on
options open interest and standard Black-Scholes greeks — they describe
*where dealers are likely to hedge*, not a guarantee of where price will
go. Backtest the strategy thoroughly across many underlyings and regimes,
paper-trade it, and understand the drawdown before using real capital.

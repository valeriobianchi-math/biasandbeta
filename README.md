# Narrative Fallacy Beta

A quantitative equity strategy that exploits the gap between a stock's **market-observed beta** and its **fundamentals-derived synthetic beta**, grounded in Taleb's *narrative fallacy* and Kahneman's WYSIATI bias.

---

## Motivation

Markets assign risk to stocks based on a persistent narrative: sector label, historical behaviour, analyst consensus. When a company's actual business mix diverges from that narrative, the market is slow to update its beta estimate. This lag is not random noise: it is a predictable, systematic bias that creates exploitable mispricing.

> *"We see only what we have decided to look at."*  
> — Nassim Nicholas Taleb, *The Black Swan*

The standard approach to estimating beta (regressing returns against an index over a fixed window) is based on on a narrative, not on fundamentals. This project measures that gap and trades it.

---

## Strategy

### Core idea

Construct a **synthetic beta** from the bottom up by weighting sector betas against a company's revenue breakdown:

```
β_synthetic = Σ  weight_i × β_sector_i
```

where `weight_i` is segment *i*'s share of total revenue and `β_sector_i` is the median beta of that pure-play sector (source: Damodaran annual dataset).

The **signal** is the gap between market beta and synthetic beta:

```
gap = β_market − β_synthetic
```

A large positive gap means the market overestimates systematic risk, hence the stock is underpriced relative to its true risk profile. A large negative gap means, of course, the opposite.

### Portfolio construction

| Leg | Selection | Rationale |
|---|---|---|
| Long | Lowest gap (β_market ≪ β_synthetic) | Market underestimates risk (stock is cheap) |
| Short | Highest gap (β_market ≫ β_synthetic) | Market overestimates risk (stock is expensive) |

Rebalancing: quarterly. Transaction cost: 15bps per leg.

---

## Backtest results

Simulated universe: 200 stocks × 40 quarters (2013–2022 proxy), with realistic market regimes (bull / bear / flat), cross-sectional noise, and gradual business-mix migration.

| Metric | Value |
|---|---|
| Annualised return (L/S) | +11.1% |
| Annualised volatility | 6.4% |
| Sharpe ratio | 1.72 |
| Max drawdown | −4.0% |
| Alpha (annualised) | +10.9% |
| Beta vs market | −0.01 |
| IC (mean) | −0.071 |
| IC t-stat | −5.85 |
| IC win rate | 84.6% |

### Performance by market regime

| Regime | Mean quarterly return | Win rate | Periods |
|---|---|---|---|
| Bear | +3.13% | 100% | 7 |
| Flat | +4.14% | 87.5% | 8 |
| Bull | +2.12% | 75.0% | 24 |

The strategy performs best in bear and flat regimes. This is consistent with the hypothesis that narrative crystallisation (and thus the exploitable gap) is most extreme during market stress.

---

## Repository structure

```
narrative-fallacy-beta/
│
├── narrative_fallacy_beta.py   # Core engine: universe generation, backtest, metrics
├── README.md
│
├── data/                       # (not included — see Data sources below)
│   ├── revenue_segments.csv    # Compustat segment data
│   ├── sector_betas.csv        # Damodaran annual betas
│   └── prices.csv              # Daily adjusted closes
│
└── notebooks/
    └── exploration.ipynb       # Interactive analysis (optional)
```

---

## Installation

```bash
git clone https://github.com/your-username/narrative-fallacy-beta.git
cd narrative-fallacy-beta
pip install numpy pandas scipy
```

No other dependencies for the simulation mode. For live data, see below.

---

## Usage

### Run the simulation (no data required)

```python
python narrative_fallacy_beta.py
```

This runs the full synthetic backtest and prints performance metrics to stdout. It also saves four CSV files locally: `backtest_results.csv`, `universe_data.csv`, `ic_data.csv`, `cumulative_data.csv`.

### Plug in real data

Replace `generate_universe()` with your own data loader. The function must return a DataFrame with these columns:

| Column | Type | Description |
|---|---|---|
| `ticker` | str | Stock identifier |
| `period` | int | Time period index (quarterly) |
| `beta_market` | float | OLS beta from trailing price history |
| `beta_synthetic` | float | Revenue-weighted sector beta |
| `beta_gap` | float | `beta_market − beta_synthetic` |
| `forward_return` | float | Next-period total return |
| `market_return` | float | Index return for the same period |

Then call:

```python
from narrative_fallacy_beta import run_backtest, compute_metrics, ic_analysis

res     = run_backtest(df, n_long=25, n_short=25, tc=0.0015)
metrics = compute_metrics(res)
ic_df   = ic_analysis(df)
```

---

## Data sources (for production use)

| Data | Source | Notes |
|---|---|---|
| Revenue segment breakdown | [Compustat via WRDS](https://wrds-www.wharton.upenn.edu/) | Segment-level SIC codes + revenue |
| Sector betas | [Damodaran Online](https://pages.stern.nyu.edu/~adamodar/) | Updated annually, free |
| Adjusted prices | [yfinance](https://pypi.org/project/yfinance/) / [polygon.io](https://polygon.io/) | Daily OHLCV |
| Geographic revenue | 10-K filings (SEC EDGAR) | Requires NLP parser for structured extraction |

---

## Limitations and known caveats

**Simulation assumptions.** The synthetic universe assumes a specific functional form for the narrative lag and business-mix migration. Real data will have more complex dynamics including M&A-driven discontinuities and segment reclassifications.

**Lookahead bias risk.** In production, revenue segment data from Compustat must be point-in-time (using `datadate` + reporting lag). Using as-reported data without a proper as-of date introduces lookahead bias.

**Sector beta instability.** Damodaran sector betas are annual snapshots. In volatile periods, intra-year beta shifts are not captured. Consider using rolling 12-month sector betas as an alternative.

**Liquidity and capacity.** The L/S signal is most acute in mid/small-cap names with complex business structures, i.e. where liquidity is lower. Transaction cost assumptions should be stress-tested for realistic bid-ask spreads.

**Short-selling constraints.** The short leg assumes frictionless shorting. In practice, borrow costs and availability vary significantly across names.

---

## Related literature

- Damodaran, A. (2023). *Equity Risk Premiums: Determinants, Estimation and Implications*. Stern NYU.
- Kahneman, D. (2011). *Thinking, Fast and Slow*. Farrar, Straus and Giroux.
- Taleb, N. N. (2007). *The Black Swan*. Random House.
- Greenwood, R. & Shleifer, A. (2014). Expectations of Returns and Expected Returns. *Review of Financial Studies*, 27(3), 714–746.
- Ang, A. & Chen, J. (2007). CAPM Over the Long Run: 1926–2001. *Journal of Empirical Finance*, 14(1), 1–40.

---

## License

MIT

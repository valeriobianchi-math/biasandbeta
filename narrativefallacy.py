"""
Narrative Fallacy Beta
"""
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats
import warnings
warnings.filterwarnings("ignore")

np.random.seed(1)

SECTOR_BETAS = {
    "Technology":       1.28,
    "Healthcare":       0.76,
    "Financials":       1.15,
    "Energy":           1.05,
    "Consumer Staples": 0.58,
    "Industrials":      1.02,
    "Utilities":        0.42,
    "Real Estate":      0.85,
    "Materials":        1.10,
    "Telecom":          0.72,
}
SECTORS = list(SECTOR_BETAS.keys())
N_STOCKS   = 200
N_QUARTERS = 40

# Market regimes
# We simulate 40 trimesters with 3 regimes: bull (70%), bear (15%), flat (15%)
def generate_market_regime(n_periods, rng):
    regimes = []
    regime  = "bull"
    for t in range(n_periods):
        if regime == "bull":
            r = rng.choice(["bull","bear","flat"], p=[0.82, 0.10, 0.08])
        elif regime == "bear":
            r = rng.choice(["bull","bear","flat"], p=[0.45, 0.40, 0.15])
        else:
            r = rng.choice(["bull","bear","flat"], p=[0.55, 0.15, 0.30])
        regime = r
        regimes.append(r)
    return regimes

def regime_market_return(regime, rng):
    if regime == "bull":
        return rng.normal(0.035, 0.055)   # ~14% ann
    elif regime == "bear":
        return rng.normal(-0.045, 0.095)  # -18% ann
    else:
        return rng.normal(0.005, 0.040)


# Generate universe
def generate_universe(n_stocks=N_STOCKS, n_periods=N_QUARTERS):
    rng = np.random.default_rng(42)
    regimes = generate_market_regime(n_periods, rng)

    primary_sector = rng.choice(SECTORS, size=n_stocks)
    market_beta_base = np.array([SECTOR_BETAS[s] for s in primary_sector])

    # Heterogeneous migration speeds
    migration_speeds = rng.uniform(0.005, 0.06, size=n_stocks)

    records = []

    for t in range(n_periods):
        mkt_ret = regime_market_return(regimes[t], rng)

        # Common factor (market) + sectorial
        factor_shock = rng.normal(0, 0.025)

        for i in range(n_stocks):
            ms = migration_speeds[i]
            base_weight = max(0.25, 0.85 - ms * t)

            other_sectors = [s for s in SECTORS if s != primary_sector[i]]
            other_w = rng.dirichlet(np.ones(3) * 0.5)
            chosen   = rng.choice(other_sectors, size=3, replace=False)

            weights = {primary_sector[i]: base_weight}
            for j, sec in enumerate(chosen):
                weights[sec] = (1 - base_weight) * other_w[j]

            # Synthetic beta
            beta_syn = sum(w * SECTOR_BETAS[sec] for sec, w in weights.items())

            # Market beta 
            narrative_w = max(0.15, 0.88 - 0.018 * t)
            beta_mkt = (narrative_w * market_beta_base[i] +
                        (1 - narrative_w) * beta_syn +
                        rng.normal(0, 0.12))   

            beta_gap = beta_mkt - beta_syn

            # Very weak signal, lots of noise
            alpha_signal  = -0.045 * beta_gap
            idio_noise    = rng.normal(0, 0.095)   # ~38% ann idio vol
            common_noise  = beta_syn * (mkt_ret + factor_shock)

            forward_ret = common_noise + alpha_signal + idio_noise

            records.append({
                "ticker":         f"STK_{i:03d}",
                "period":         t,
                "regime":         regimes[t],
                "primary_sector": primary_sector[i],
                "beta_market":    round(beta_mkt, 4),
                "beta_synthetic": round(beta_syn, 4),
                "beta_gap":       round(beta_gap, 4),
                "forward_return": round(forward_ret, 4),
                "market_return":  round(mkt_ret, 4),
            })

    return pd.DataFrame(records)


# Backtest
def run_backtest(df, n_long=25, n_short=25, tc=0.0015):
    results = []
    for t in sorted(df["period"].unique())[:-1]:
        sub = df[df["period"] == t].copy().sort_values("beta_gap")
        longs  = sub.head(n_long)
        shorts = sub.tail(n_short)

        long_ret  = longs["forward_return"].mean()  - tc
        short_ret = shorts["forward_return"].mean() - tc
        ls_ret    = long_ret - short_ret
        mkt_ret   = sub["market_return"].mean()

        results.append({
            "period":       t,
            "regime":       sub["regime"].iloc[0],
            "long_return":  long_ret,
            "short_return": short_ret,
            "ls_return":    ls_ret,
            "market_return":mkt_ret,
            "long_avg_gap": longs["beta_gap"].mean(),
            "short_avg_gap":shorts["beta_gap"].mean(),
        })
    return pd.DataFrame(results)


# Metrics
def compute_metrics(res):
    ls  = res["ls_return"]
    mkt = res["market_return"]
    cum_ls  = (1 + ls).cumprod()
    cum_mkt = (1 + mkt).cumprod()

    ann_ret = (cum_ls.iloc[-1] ** (4 / len(ls))) - 1
    ann_vol = ls.std() * np.sqrt(4)
    sharpe  = ann_ret / ann_vol if ann_vol > 0 else 0

    running_max = cum_ls.cummax()
    max_dd = ((cum_ls - running_max) / running_max).min()

    slope, intercept, r, p, _ = stats.linregress(mkt, ls)

    # Calman ratio (ann_ret / avg_drawdown) — proxy
    avg_dd = ((cum_ls - running_max) / running_max).mean()
    calmar = ann_ret / abs(max_dd) if max_dd != 0 else np.nan

    return {
        "ann_return_%":   round(ann_ret * 100, 2),
        "ann_vol_%":      round(ann_vol * 100, 2),
        "sharpe_ratio":   round(sharpe, 3),
        "calmar_ratio":   round(calmar, 3),
        "max_drawdown_%": round(max_dd * 100, 2),
        "alpha_ann_%":    round(intercept * 4 * 100, 2),
        "beta_vs_mkt":    round(slope, 3),
        "cum_return_ls_%":round((cum_ls.iloc[-1] - 1) * 100, 2),
        "cum_mkt_%":      round((cum_mkt.iloc[-1] - 1) * 100, 2),
        "p_value_alpha":  round(p, 4),
        "n_periods":      len(ls),
    }


def ic_analysis(df):
    rows = []
    for t in sorted(df["period"].unique())[:-1]:
        sub = df[df["period"] == t]
        ic, pv = stats.pearsonr(sub["beta_gap"], sub["forward_return"])
        rows.append({"period": t, "ic": ic, "p_value": pv, "regime": sub["regime"].iloc[0]})
    return pd.DataFrame(rows)


def regime_breakdown(res):
    return res.groupby("regime")["ls_return"].agg(
        mean_return=lambda x: round(x.mean()*100, 3),
        win_rate=lambda x: round((x > 0).mean()*100, 1),
        count="count"
    ).reset_index()


# Main
if __name__ == "__main__":
    print("Generating universe (200 stocks × 40 trimesters)...")
    df = generate_universe()

    print("Running backtest L/S...")
    res = run_backtest(df)
    metrics = compute_metrics(res)
    ic_df   = ic_analysis(df)
    reg_df  = regime_breakdown(res)

    ic_mean = ic_df["ic"].mean()
    ic_tstat = ic_mean / (ic_df["ic"].std() / np.sqrt(len(ic_df)))

    print("\n" + "="*52)
    print("NARRATIVE FALLACY BETA - RESULTS")
    print("="*52)
    for k, v in metrics.items():
        print(f"  {k:<24} {v}")
    print(f"\n  Average IC:               {ic_mean:.4f}")
    print(f"  IC t-stat:              {ic_tstat:.3f}")
    print(f"  IC% positive periods:   {(ic_df['ic']<0).mean()*100:.1f}%")
    print("\n  Breakdown by regime:")
    print(reg_df.to_string(index=False))
    print("="*52)

    out_dir = Path(__file__).resolve().parent / "output"
    out_dir.mkdir(parents=True, exist_ok=True)

    res.to_csv(out_dir / "backtest_results.csv", index=False)
    df.to_csv(out_dir / "universe_data.csv", index=False)
    ic_df.to_csv(out_dir / "ic_data.csv", index=False)
    reg_df.to_csv(out_dir / "regime_data.csv", index=False)

    cum_data = pd.DataFrame({
        "period":     res["period"],
        "cum_ls":     (1 + res["ls_return"]).cumprod().values,
        "cum_mkt":    (1 + res["market_return"]).cumprod().values,
        "ls_return":  res["ls_return"].values,
        "regime":     res["regime"].values,
    })
    cum_data.to_csv(out_dir / "cumulative_data.csv", index=False)

    print(f"\nDati salvati in: {out_dir}")

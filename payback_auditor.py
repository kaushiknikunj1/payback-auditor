#!/usr/bin/env python3
"""Payback Auditor - the LTV:CAC on the slide and the payback in the data, side by side.

1. Synthesize 12 monthly acquisition cohorts across 5 channels (paid search, paid social,
   affiliates, referral, organic): spend, users acquired, and monthly net revenue for up
   to 18 months of age, with channel-specific retention and ARPU curves.
2. Engine, per channel: the HEADLINE LTV:CAC the way growth decks compute it (first-quarter
   ARPU / first-quarter monthly churn, no margin, no discounting, no horizon) and the
   HONEST one (Weibull survival fitted to observed retention, extrapolated to 36 months,
   margin-adjusted, discounted); the CAC payback month, "never within 36 months" allowed;
   and a decomposition of the gap between the two numbers.
3. Evidence pack per channel, plus a portfolio pack: blended ratio, best/worst channel,
   spend-weighted spread, share of spend sitting in flagged channels.
4. Narrate: with GEMINI_API_KEY or ANTHROPIC_API_KEY set, an LLM writes two lines per
   channel and a three-line portfolio summary. Every number it writes is checked against
   the evidence pack; if it invents one, the deterministic template is used instead.
   Without a key you get the template. The engine owns the arithmetic; the LLM only
   owns the sentences.

Run:  python payback_auditor.py
Out:  audit.md, payback.png
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import llm  # noqa: E402

MARGIN = 0.62        # gross margin on net revenue
DISCOUNT = 0.01      # monthly discount rate (~12.7% a year)
HORIZON = 36         # months the honest LTV is allowed to run
N_COHORTS, OBS_MONTHS = 12, 18
FIRST_COHORT = "2025-04"

# cac: INR per acquired user · users: per cohort-month · ARPU(t) = floor + (arpu0 - floor) * decay^t
# retention(t) = exp(-(t/scale)^shape): shape < 1 churn decelerates, shape > 1 a cliff (promo ends)
CHANNELS = {
    "Paid search": dict(cac=820, users=7500,  arpu0=120, floor=100, decay=0.90, scale=14.0, shape=1.30),
    "Paid social": dict(cac=640, users=13000, arpu0=165, floor=70,  decay=0.85, scale=7.0,  shape=1.70),
    "Affiliates":  dict(cac=225, users=10000, arpu0=240, floor=65,  decay=0.30, scale=1.2,  shape=0.60),
    "Referral":    dict(cac=190, users=9000,  arpu0=80,  floor=80,  decay=1.00, scale=22.0, shape=0.70),
    "Organic":     dict(cac=120, users=12000, arpu0=70,  floor=70,  decay=1.00, scale=14.0, shape=0.75),
}
COLOURS = ["#4A6FA5", "#d9534f", "#e0a030", "#5a9e6f", "#8e6bb8"]


def weibull(t, scale: float, shape: float) -> np.ndarray:
    return np.exp(-(np.asarray(t, float) / scale) ** shape)


def make_cohorts(seed: int = 11) -> pd.DataFrame:
    """One row per channel x cohort x observed age: users, spend, active users, net revenue (INR)."""
    rng = np.random.default_rng(seed)
    months = pd.period_range(FIRST_COHORT, periods=N_COHORTS, freq="M").strftime("%Y-%m")
    rows = []
    for ch, p in CHANNELS.items():
        for k, month in enumerate(months):
            users = int(rng.normal(p["users"], 0.08 * p["users"]))
            spend = int(users * p["cac"] * rng.normal(1, 0.05))
            ages = np.arange(OBS_MONTHS - k)                 # younger cohorts are observed less
            surv = weibull(ages, p["scale"], p["shape"])
            active = users
            for a in ages:
                if a:
                    active = int(rng.binomial(active, surv[a] / surv[a - 1]))
                arpu = p["floor"] + (p["arpu0"] - p["floor"]) * p["decay"] ** a
                rows.append((ch, month, users, spend, int(a), active,
                             int(active * arpu * rng.normal(1, 0.04))))
    return pd.DataFrame(rows, columns=["channel", "cohort", "users", "spend", "age", "active", "revenue"])


# ----------------------------------------------------------------------------- engine
def pooled_curve(d: pd.DataFrame) -> pd.DataFrame:
    """Per age: retention and ARPU per active user, pooled over cohorts old enough to be seen there."""
    g = d.groupby("age").agg(acquired=("users", "sum"), active=("active", "sum"), revenue=("revenue", "sum"))
    g["retention"] = g.active / g.acquired
    g["arpu"] = g.revenue / g.active
    return g.reset_index()


def fit_weibull(ages: np.ndarray, retention: np.ndarray, weights: np.ndarray) -> tuple[float, float]:
    """Weighted least squares on ln(-ln R) = shape*ln t - shape*ln scale. Returns (scale, shape)."""
    m = (ages > 0) & (retention > 0) & (retention < 1)
    slope, intercept = np.polyfit(np.log(ages[m]), np.log(-np.log(retention[m])), 1, w=np.sqrt(weights[m]))
    return float(np.exp(-intercept / slope)), float(slope)


def headline_ltv(curve: pd.DataFrame) -> tuple[float, float, float]:
    """The deck's maths: first-quarter ARPU per active user / first-quarter monthly churn. Forever."""
    q1 = curve[curve.age <= 2]
    arpu = q1.revenue.sum() / q1.active.sum()
    churn = (1 - curve.loc[curve.age == 3, "retention"].item()) / 3
    return arpu, churn, arpu / churn


def honest_cashflows(curve: pd.DataFrame, scale: float, shape: float) -> tuple[np.ndarray, np.ndarray]:
    """Margin-adjusted expected revenue per acquired user by month of life, over HORIZON months."""
    r = weibull(np.arange(HORIZON), scale, shape)
    obs = curve.arpu.values
    arpu = np.concatenate([obs, np.full(HORIZON - len(obs), obs[-3:].mean())])   # hold late ARPU flat
    return MARGIN * arpu * r, r


def discounted(monthly: np.ndarray) -> float:
    return float((monthly / (1 + DISCOUNT) ** np.arange(len(monthly))).sum())


def payback_month(cumulative: np.ndarray, cac: float) -> int | None:
    """1-indexed month in which cumulative margin-adjusted revenue first covers CAC; None = never."""
    hits = np.flatnonzero(cumulative >= cac)
    return int(hits[0]) + 1 if len(hits) else None


def gap_steps(head_ltv: float, arpu_q1: float, r: np.ndarray, monthly: np.ndarray) -> dict:
    """Walk from the headline LTV to the honest one; each step as % of the headline."""
    l1 = head_ltv * MARGIN
    l2 = MARGIN * arpu_q1 * r.sum()
    l3 = monthly.sum()
    l4 = discounted(monthly)
    steps = {"margin": l1 - head_ltv, "retention_curve": l2 - l1, "arpu_fade": l3 - l2, "discounting": l4 - l3}
    return {k: round(v / head_ltv * 100, 1) for k, v in steps.items()}


def audit_channel(ch: str, d: pd.DataFrame) -> dict:
    curve = pooled_curve(d)
    spend = int(d.drop_duplicates("cohort").spend.sum())
    users = int(d.drop_duplicates("cohort").users.sum())
    cac = spend / users
    arpu_q1, churn_q1, head_ltv = headline_ltv(curve)
    scale, shape = fit_weibull(curve.age.values, curve.retention.values, curve.acquired.values)
    monthly, r = honest_cashflows(curve, scale, shape)
    cum = monthly.cumsum()
    ltv = discounted(monthly)
    pb = payback_month(cum, cac)
    head_ratio, honest_ratio = head_ltv / cac, ltv / cac
    flag = None
    if head_ratio >= 3 > honest_ratio:
        flag = f"headline {head_ratio:.1f}:1 clears the 3:1 bar, honest {honest_ratio:.1f}:1 does not"
    if pb is None or pb > 18:
        flag = (flag + "; " if flag else "") + ("payback never arrives within 36 months" if pb is None
                                                 else f"payback takes {pb} months, past the 18-month limit")
    return {
        "channel": ch, "cohorts": int(d.cohort.nunique()), "spend_inr": spend,
        "spend_cr": round(spend / 1e7, 2), "users": users, "cac_inr": round(cac),
        "headline": {"arpu_q1_inr": round(arpu_q1), "monthly_churn_q1_pct": round(churn_q1 * 100, 1),
                     "implied_months_of_life": round(1 / churn_q1, 1), "ltv_inr": round(head_ltv),
                     "ltv_to_cac": round(head_ratio, 1)},
        "honest": {"margin_pct": round(MARGIN * 100), "monthly_discount_pct": round(DISCOUNT * 100, 1),
                   "horizon_months": HORIZON, "fitted_scale": round(scale, 1), "fitted_shape": round(shape, 2),
                   "fitted_months_of_life": round(float(r.sum()), 1), "ltv_inr": round(ltv),
                   "ltv_to_cac": round(honest_ratio, 1)},
        "payback_month": pb, "payback_label": f"paid back in month {pb}" if pb else f"never paid back within {HORIZON} months",
        "cumulative_margin_per_user_36m_inr": round(float(cum[-1])),
        "retention_12m_observed_pct": round(float(curve.loc[curve.age == 12, "retention"].item()) * 100, 1),
        "retention_12m_fitted_pct": round(float(r[12]) * 100, 1),
        "gap_pct_of_headline": gap_steps(head_ltv, arpu_q1, r, monthly),
        "flag": flag,
        "_cum": cum.round(1).tolist(),
    }


def audit_portfolio(packs: list[dict]) -> dict:
    spend = np.array([p["spend_inr"] for p in packs], float)
    users = np.array([p["users"] for p in packs], float)
    head = np.array([p["headline"]["ltv_to_cac"] for p in packs])
    hon = np.array([p["honest"]["ltv_to_cac"] for p in packs])
    w = spend / spend.sum()
    blended_hon = float((users * [p["honest"]["ltv_inr"] for p in packs]).sum() / spend.sum())
    blended_head = float((users * [p["headline"]["ltv_inr"] for p in packs]).sum() / spend.sum())
    best, worst = packs[int(hon.argmax())], packs[int(hon.argmin())]
    flagged = [p for p in packs if p["flag"]]
    return {
        "channels": len(packs), "spend_cr": round(spend.sum() / 1e7, 2), "users": int(users.sum()),
        "blended_cac_inr": round(spend.sum() / users.sum()),
        "blended_headline_ltv_to_cac": round(blended_head, 1), "blended_honest_ltv_to_cac": round(blended_hon, 1),
        "best": {"channel": best["channel"], "honest_ltv_to_cac": best["honest"]["ltv_to_cac"],
                 "payback_label": best["payback_label"], "spend_cr": best["spend_cr"]},
        "worst": {"channel": worst["channel"], "honest_ltv_to_cac": worst["honest"]["ltv_to_cac"],
                  "payback_label": worst["payback_label"], "spend_cr": worst["spend_cr"],
                  "cac_inr": worst["cac_inr"]},
        "spend_weighted_spread": {"min": float(hon.min()), "max": float(hon.max()),
                                  "sd": round(float(np.sqrt((w * (hon - blended_hon) ** 2).sum())), 2)},
        "flagged_channels": [p["channel"] for p in flagged],
        "share_of_spend_flagged_pct": round(float(w[[p["flag"] is not None for p in packs]].sum() * 100)),
        "share_of_spend_below_1x_pct": round(float(w[hon < 1].sum() * 100)),
        "share_of_spend_above_3x_pct": round(float(w[hon >= 3].sum() * 100)),
    }


# ----------------------------------------------------------------------------- narrative
def public(ev: dict) -> dict:
    return {k: v for k, v in ev.items() if not k.startswith("_")}


def template_channel(ev: dict) -> str:
    h, o, g = ev["headline"], ev["honest"], ev["gap_pct_of_headline"]
    line1 = (f"{ev['channel']}: headline LTV:CAC {h['ltv_to_cac']}:1, honest {o['ltv_to_cac']}:1; "
             f"CAC of Rs {ev['cac_inr']:,} is {ev['payback_label']}.")
    rest = {k: v for k, v in g.items() if k != "margin"}       # margin is the same haircut everywhere
    worst = min(rest, key=rest.get)
    if g["retention_curve"] > 0:
        line2 = (f"The curve works in its favour (+{g['retention_curve']}%: churn decelerates, fitted shape "
                 f"{o['fitted_shape']}); the whole gap is margin ({g['margin']}%) and discounting ({g['discounting']}%).")
    elif worst == "retention_curve":
        line2 = (f"Beyond the {o['margin_pct']}% margin haircut, the gap is the retention curve: "
                 f"{h['monthly_churn_q1_pct']}% first-quarter churn implies {h['implied_months_of_life']} months of life, "
                 f"the fitted curve (scale {o['fitted_scale']}, shape {o['fitted_shape']}) delivers "
                 f"{o['fitted_months_of_life']} within {o['horizon_months']} ({g['retention_curve']}% of the headline LTV).")
    elif worst == "arpu_fade":
        line2 = (f"Beyond the {o['margin_pct']}% margin haircut, the gap is ARPU: Rs {h['arpu_q1_inr']} per active user "
                 f"in the first quarter does not last ({g['arpu_fade']}% of the headline LTV).")
    else:
        line2 = (f"Beyond the {o['margin_pct']}% margin haircut, the gap is discounting at "
                 f"{o['monthly_discount_pct']}% a month ({g['discounting']}% of the headline LTV).")
    return f"{line1}\n{line2}"


def template_portfolio(ev: dict) -> str:
    b, w, s = ev["best"], ev["worst"], ev["spend_weighted_spread"]
    flagged = ", ".join(ev["flagged_channels"]) or "none"
    return "\n".join([
        f"Blended LTV:CAC is {ev['blended_headline_ltv_to_cac']}:1 on the slide and "
        f"{ev['blended_honest_ltv_to_cac']}:1 in the data, across {ev['channels']} channels and Rs {ev['spend_cr']} Cr of spend.",
        f"The blend hides a spread from {s['min']}:1 ({w['channel']}) to {s['max']}:1 ({b['channel']}); "
        f"{ev['share_of_spend_flagged_pct']}% of spend sits in flagged channels ({flagged}), "
        f"{ev['share_of_spend_above_3x_pct']}% in channels that honestly clear 3:1.",
        f"The money is going wrong in {w['channel']}: Rs {w['spend_cr']} Cr at a CAC of Rs {w['cac_inr']:,} that is "
        f"{w['payback_label']}, while {b['channel']} is {b['payback_label']} on Rs {b['spend_cr']} Cr.",
    ])


SYSTEM_CHANNEL = """You write a two-line unit-economics note for a growth review at a consumer fintech.
Line 1: the channel, its headline LTV:CAC vs the honest LTV:CAC, and the CAC payback month (or that it never pays back within the horizon).
Line 2: the single biggest reason the two numbers differ, in plain English, using the gap decomposition.
Use ONLY numbers present in the evidence. Never compute, re-round, or add new numbers. Amounts are INR. No jargon about models."""

SYSTEM_PORTFOLIO = """You write a three-line portfolio summary for a growth review at a consumer fintech.
Line 1: blended headline vs honest LTV:CAC, total spend.  Line 2: the spread the blend hides and the share of spend in flagged channels.
Line 3: where the spend is going wrong and where it is working, naming channels.
Use ONLY numbers present in the evidence. Never compute, re-round, or add new numbers. Amounts are INR."""


def narrate(ev: dict, system: str, template) -> tuple[str, str]:
    """Returns (text, source). Source is 'llm (<provider>)' or 'template (<reason>)'."""
    text = llm.complete(system, json.dumps(public(ev), indent=2), max_tokens=300)
    if text is None:
        return template(ev), "template (no API key)"
    bad = llm.unpinned(text, public(ev))
    if bad:
        return template(ev), f"template (LLM invented numbers: {sorted(bad)})"
    return text, f"llm ({llm.provider()})"


# ----------------------------------------------------------------------------- output
def plot(packs: list[dict], path: str = "payback.png") -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.2), gridspec_kw={"width_ratios": [1.5, 1]})
    t = np.arange(1, HORIZON + 1)
    for p, c in zip(packs, COLOURS):
        cum = np.array(p["_cum"])
        ax1.plot(t, cum, color=c, lw=2, label=p["channel"])
        ax1.axhline(p["cac_inr"], color=c, lw=1, ls=":", alpha=0.8)
        ax1.annotate(f"{p['channel']} CAC Rs {p['cac_inr']:,}", (HORIZON + 0.6, p["cac_inr"]), fontsize=7.5,
                     color="#444", va="center", bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none"))
        if p["payback_month"]:
            ax1.plot(p["payback_month"], cum[p["payback_month"] - 1], "o", color=c, ms=7,
                     markeredgecolor="white", markeredgewidth=1.5)
    ax1.set_xlim(1, HORIZON + 11)
    ax1.set_xticks([1, 6, 12, 18, 24, 30, 36])
    ax1.set_xlabel("month of life")
    ax1.set_ylabel("cumulative margin-adjusted revenue per user (Rs)")
    ax1.set_title("Payback: cumulative margin per user vs CAC (dot = payback month)", fontsize=10)
    ax1.legend(fontsize=8, frameon=False, loc="upper left")
    ax1.grid(alpha=0.2)
    for s in ("top", "right"):
        ax1.spines[s].set_visible(False)

    x = np.arange(len(packs))
    head = [p["headline"]["ltv_to_cac"] for p in packs]
    hon = [p["honest"]["ltv_to_cac"] for p in packs]
    ax2.bar(x - 0.2, head, 0.38, color="#c9d2e0", label="headline (deck maths)")
    ax2.bar(x + 0.2, hon, 0.38, color=["#d9534f" if p["flag"] else "#4A6FA5" for p in packs],
            label="honest (fitted, margin, discounted)")
    for i, (a, b) in enumerate(zip(head, hon)):
        ax2.text(i - 0.2, a + 0.08, f"{a}", ha="center", fontsize=8, color="#444")
        ax2.text(i + 0.2, b + 0.08, f"{b}", ha="center", fontsize=8, color="#444")
    ax2.axhline(3, color="#888", lw=1, ls="--")
    ax2.text(-0.55, 3.08, "3:1 bar", fontsize=8, color="#666", ha="left")
    ax2.set_xticks(x, [p["channel"] for p in packs], fontsize=8.5)
    ax2.set_ylabel("LTV : CAC")
    ax2.set_title("Headline vs honest LTV:CAC (red = flagged)", fontsize=10)
    ax2.legend(fontsize=8, frameon=False, loc="upper left")
    ax2.grid(axis="y", alpha=0.2)
    for s in ("top", "right"):
        ax2.spines[s].set_visible(False)
    plt.tight_layout()
    plt.savefig(path, dpi=130)


def section(title: str, text: str, src: str, ev: dict) -> list[str]:
    return [f"## {title}", "", text, "", f"*source: {src}*", "",
            "<details><summary>evidence</summary>", "", "```json", json.dumps(public(ev), indent=2), "```",
            "</details>", ""]


def main() -> None:
    d = make_cohorts()
    packs = [audit_channel(ch, d[d.channel == ch]) for ch in CHANNELS]
    portfolio = audit_portfolio(packs)
    print(f"{N_COHORTS} cohorts x {len(CHANNELS)} channels · {OBS_MONTHS} months observed · "
          f"Rs {portfolio['spend_cr']} Cr spend · margin {MARGIN:.0%} · discount {DISCOUNT:.0%}/month · "
          f"LLM provider: {llm.provider()}\n")
    out = ["# Unit-economics audit", "",
           f"Headline LTV:CAC the way decks compute it vs honest LTV:CAC (fitted Weibull retention to {HORIZON} months, "
           f"{MARGIN:.0%} margin, {DISCOUNT:.0%}/month discount) and CAC payback, per channel. "
           f"Narratives written by: {llm.provider()}; every number verified against the evidence pack.", ""]
    for ev in packs:
        text, src = narrate(ev, SYSTEM_CHANNEL, template_channel)
        print(f"── {ev['channel']}  [{src}]{'  FLAG: ' + ev['flag'] if ev['flag'] else ''}")
        print(text, "\n")
        out += section(ev["channel"], text, src, ev)
    text, src = narrate(portfolio, SYSTEM_PORTFOLIO, template_portfolio)
    print(f"── Portfolio  [{src}]")
    print(text, "\n")
    out += section("Portfolio", text, src, portfolio)
    Path("audit.md").write_text("\n".join(out), encoding="utf-8")
    plot(packs)
    print("wrote audit.md and payback.png")


if __name__ == "__main__":
    main()

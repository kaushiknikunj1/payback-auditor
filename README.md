# Payback Auditor

A 3:1 LTV:CAC on the slide and a 23-month payback in the data can both be true at the same time. I have sat in the growth review where that happened. The deck was not lying — it took first-quarter ARPU, divided by first-quarter churn, and called the answer lifetime value. No margin, no discounting, no end to the lifetime. The data was not lying either. They were answering different questions, and the room spent forty minutes arguing about arithmetic instead of assumptions.

This is the auditor I wanted in that room. It recomputes both numbers per acquisition channel — the headline ratio the way decks compute it, and an honest one from a fitted retention curve, margin-adjusted and discounted — puts them side by side with the CAC payback month, and flags the channels where the two disagree. Then it writes the two lines a human would have to write anyway, without letting the language model touch the numbers.

```
── Paid search  [template (no API key)]  FLAG: headline 3.5:1 clears the 3:1 bar, honest 1.0:1 does not; payback takes 23 months, past the 18-month limit
Paid search: headline LTV:CAC 3.5:1, honest 1.0:1; CAC of Rs 824 is paid back in month 23.
Beyond the 62% margin haircut, the gap is the retention curve: 4.2% first-quarter churn implies 23.9 months of life, the fitted curve (scale 14.0, shape 1.31) delivers 13.1 within 36 (-27.9% of the headline LTV).

── Portfolio  [template (no API key)]
Blended LTV:CAC is 3.8:1 on the slide and 1.4:1 in the data, across 5 channels and Rs 24.12 Cr of spend.
The blend hides a spread from 0.8:1 (Paid social) to 4.4:1 (Organic); 84% of spend sits in flagged channels (Paid search, Paid social, Affiliates), 16% in channels that honestly clear 3:1.
The money is going wrong in Paid social: Rs 10.0 Cr at a CAC of Rs 634 that is never paid back within 36 months, while Organic is paid back in month 4 on Rs 1.65 Cr.
```

That is the deterministic template. With an API key the same evidence pack goes to an LLM, which writes it in plainer English — and is then checked.

## How it works

1. **Data.** Twelve monthly acquisition cohorts across five channels — paid search, paid social, affiliates, referral, organic — with spend, users acquired, and monthly net revenue for up to 18 months of age. Synthetic, fixed seed, consumer-fintech shape: affiliates bring a big first-month transaction and vanish, paid social retains well for exactly as long as the welcome offer runs and then falls off a cliff, referral keeps users longest. Gross margin 62%, discount rate 1% a month.
2. **Engine.** Per channel, two LTVs. The *headline*: first-quarter ARPU per active user divided by first-quarter monthly churn, no margin, no discount, no horizon — the deck's maths. The *honest*: a Weibull survival curve fitted to pooled observed retention (weighted least squares on the log-log form), extrapolated to 36 months and stopped there, times observed ARPU by month of life, times margin, discounted. Plus the CAC payback month — the month cumulative margin-adjusted revenue per user first covers CAC, with "never within 36 months" as a legal answer — and a walk from the headline LTV to the honest one in four steps: margin, retention curve, ARPU fade, discounting.
3. **Evidence pack.** Per channel: spend, users, CAC, both ratios, payback month, fitted curve parameters, 12-month observed vs fitted retention, the gap decomposition, and the flag (headline at or above 3:1 while honest is below, or payback past 18 months). Per portfolio: blended headline vs honest ratio, best and worst channel, spend-weighted spread, and the share of spend sitting in flagged channels — the blended-average trap, stated as a number.
4. **Write + verify.** The pack goes to an LLM with a two-line brief per channel and a three-line brief for the portfolio. Every number in the reply is parsed and checked against the pack; if any was invented or re-rounded, the deterministic template is used instead and the output says so.

Step 4 matters more here than in most of my projects, because unit economics are *made of* rounding decisions. A model that writes "about 1:1" when the pack says 0.8:1, or "pays back in under two years" when the number is 23 months, has quietly moved a budget line. The whole point of the auditor is that the room argues about the assumptions — margin, horizon, the shape of the curve — and never about whether the arithmetic was done right.

## Run it

```bash
pip install -r requirements.txt
python payback_auditor.py
python test_payback_auditor.py
```

Works with no API key — you get the template narratives. For LLM-written ones set one of:

```bash
export GEMINI_API_KEY=...        # preferred; uses gemini-2.5-flash via REST
export ANTHROPIC_API_KEY=...     # uses the official anthropic SDK, claude-opus-5-5
```

Outputs: `audit.md` (narratives + collapsible evidence packs per channel and for the portfolio) and `payback.png` (payback curves against each channel's CAC, and headline vs honest LTV:CAC bars).

## What I'd change for production

- Fit the curve per cohort, not pooled, and show the band. The pooled Weibull hides the question a CFO will ask first: is the latest cohort retaining like the old ones, or is the channel getting worse as it scales?
- Replace the flat late-ARPU assumption with the finance team's revenue-per-active forecast, and put contribution margin by channel into the pack instead of one blended 62%. Affiliate-sourced users have different payment mix and different support cost; one margin flatters the worst channel.
- Add the incrementality adjustment. Organic and referral look best here partly because they carry the least attributed spend. A channel's honest CAC should be spend over *incremental* users, and that number comes from a geo or holdout test, not the attribution tool.

Companion reading: [LTV:CAC Is Lying to You](https://nikunjkaushik.com/blog/ltv-cac-truth.html), and the follow-up [The CAC Payback Trap](https://nikunjkaushik.com/blog/cac-payback-trap.html). Part of the [Building with AI](https://nikunjkaushik.com/projects.html) set on my site.

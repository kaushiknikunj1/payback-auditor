# Unit-economics audit

Headline LTV:CAC the way decks compute it vs honest LTV:CAC (fitted Weibull retention to 36 months, 62% margin, 1%/month discount) and CAC payback, per channel. Narratives written by: none; every number verified against the evidence pack.

## Paid search

Paid search: headline LTV:CAC 3.5:1, honest 1.0:1; CAC of Rs 824 is paid back in month 23.
Beyond the 62% margin haircut, the gap is the retention curve: 4.2% first-quarter churn implies 23.9 months of life, the fitted curve (scale 14.0, shape 1.31) delivers 13.1 within 36 (-27.9% of the headline LTV).

*source: template (no API key)*

<details><summary>evidence</summary>

```json
{
  "channel": "Paid search",
  "cohorts": 12,
  "spend_inr": 77842528,
  "spend_cr": 7.78,
  "users": 94435,
  "cac_inr": 824,
  "headline": {
    "arpu_q1_inr": 120,
    "monthly_churn_q1_pct": 4.2,
    "implied_months_of_life": 23.9,
    "ltv_inr": 2854,
    "ltv_to_cac": 3.5
  },
  "honest": {
    "margin_pct": 62,
    "monthly_discount_pct": 1.0,
    "horizon_months": 36,
    "fitted_scale": 14.0,
    "fitted_shape": 1.31,
    "fitted_months_of_life": 13.1,
    "ltv_inr": 828,
    "ltv_to_cac": 1.0
  },
  "payback_month": 23,
  "payback_label": "paid back in month 23",
  "cumulative_margin_per_user_36m_inr": 902,
  "retention_12m_observed_pct": 44.2,
  "retention_12m_fitted_pct": 44.0,
  "gap_pct_of_headline": {
    "margin": -38.0,
    "retention_curve": -27.9,
    "arpu_fade": -2.5,
    "discounting": -2.6
  },
  "flag": "headline 3.5:1 clears the 3:1 bar, honest 1.0:1 does not; payback takes 23 months, past the 18-month limit"
}
```
</details>

## Paid social

Paid social: headline LTV:CAC 3.4:1, honest 0.8:1; CAC of Rs 634 is never paid back within 36 months.
Beyond the 62% margin haircut, the gap is the retention curve: 7.0% first-quarter churn implies 14.2 months of life, the fitted curve (scale 7.0, shape 1.71) delivers 6.7 within 36 (-32.7% of the headline LTV).

*source: template (no API key)*

<details><summary>evidence</summary>

```json
{
  "channel": "Paid social",
  "cohorts": 12,
  "spend_inr": 99975393,
  "spend_cr": 10.0,
  "users": 157579,
  "cac_inr": 634,
  "headline": {
    "arpu_q1_inr": 150,
    "monthly_churn_q1_pct": 7.0,
    "implied_months_of_life": 14.2,
    "ltv_inr": 2133,
    "ltv_to_cac": 3.4
  },
  "honest": {
    "margin_pct": 62,
    "monthly_discount_pct": 1.0,
    "horizon_months": 36,
    "fitted_scale": 7.0,
    "fitted_shape": 1.71,
    "fitted_months_of_life": 6.7,
    "ltv_inr": 511,
    "ltv_to_cac": 0.8
  },
  "payback_month": null,
  "payback_label": "never paid back within 36 months",
  "cumulative_margin_per_user_36m_inr": 528,
  "retention_12m_observed_pct": 8.0,
  "retention_12m_fitted_pct": 8.0,
  "gap_pct_of_headline": {
    "margin": -38.0,
    "retention_curve": -32.7,
    "arpu_fade": -4.6,
    "discounting": -0.8
  },
  "flag": "headline 3.4:1 clears the 3:1 bar, honest 0.8:1 does not; payback never arrives within 36 months"
}
```
</details>

## Affiliates

Affiliates: headline LTV:CAC 3.0:1, honest 1.0:1; CAC of Rs 223 is paid back in month 22.
Beyond the 62% margin haircut, the gap is the retention curve: 27.4% first-quarter churn implies 3.6 months of life, the fitted curve (scale 1.2, shape 0.6) delivers 2.4 within 36 (-20.5% of the headline LTV).

*source: template (no API key)*

<details><summary>evidence</summary>

```json
{
  "channel": "Affiliates",
  "cohorts": 12,
  "spend_inr": 25822992,
  "spend_cr": 2.58,
  "users": 115662,
  "cac_inr": 223,
  "headline": {
    "arpu_q1_inr": 186,
    "monthly_churn_q1_pct": 27.4,
    "implied_months_of_life": 3.6,
    "ltv_inr": 679,
    "ltv_to_cac": 3.0
  },
  "honest": {
    "margin_pct": 62,
    "monthly_discount_pct": 1.0,
    "horizon_months": 36,
    "fitted_scale": 1.2,
    "fitted_shape": 0.6,
    "fitted_months_of_life": 2.4,
    "ltv_inr": 222,
    "ltv_to_cac": 1.0
  },
  "payback_month": 22,
  "payback_label": "paid back in month 22",
  "cumulative_margin_per_user_36m_inr": 224,
  "retention_12m_observed_pct": 1.8,
  "retention_12m_fitted_pct": 1.9,
  "gap_pct_of_headline": {
    "margin": -38.0,
    "retention_curve": -20.5,
    "arpu_fade": -8.5,
    "discounting": -0.4
  },
  "flag": "headline 3.0:1 clears the 3:1 bar, honest 1.0:1 does not; payback takes 22 months, past the 18-month limit"
}
```
</details>

## Referral

Referral: headline LTV:CAC 5.8:1, honest 4.0:1; CAC of Rs 190 is paid back in month 5.
The curve works in its favour (+16.4%: churn decelerates, fitted shape 0.7); the whole gap is margin (-38.0%) and discounting (-9.6%).

*source: template (no API key)*

<details><summary>evidence</summary>

```json
{
  "channel": "Referral",
  "cohorts": 12,
  "spend_inr": 21024078,
  "spend_cr": 2.1,
  "users": 110649,
  "cac_inr": 190,
  "headline": {
    "arpu_q1_inr": 81,
    "monthly_churn_q1_pct": 7.3,
    "implied_months_of_life": 13.6,
    "ltv_inr": 1098,
    "ltv_to_cac": 5.8
  },
  "honest": {
    "margin_pct": 62,
    "monthly_discount_pct": 1.0,
    "horizon_months": 36,
    "fitted_scale": 21.9,
    "fitted_shape": 0.7,
    "fitted_months_of_life": 17.2,
    "ltv_inr": 758,
    "ltv_to_cac": 4.0
  },
  "payback_month": 5,
  "payback_label": "paid back in month 5",
  "cumulative_margin_per_user_36m_inr": 863,
  "retention_12m_observed_pct": 51.9,
  "retention_12m_fitted_pct": 51.9,
  "gap_pct_of_headline": {
    "margin": -38.0,
    "retention_curve": 16.4,
    "arpu_fade": 0.3,
    "discounting": -9.6
  },
  "flag": null
}
```
</details>

## Organic

Organic: headline LTV:CAC 6.5:1, honest 4.4:1; CAC of Rs 120 is paid back in month 4.
The curve works in its favour (+13.4%: churn decelerates, fitted shape 0.75); the whole gap is margin (-38.0%) and discounting (-8.2%).

*source: template (no API key)*

<details><summary>evidence</summary>

```json
{
  "channel": "Organic",
  "cohorts": 12,
  "spend_inr": 16499253,
  "spend_cr": 1.65,
  "users": 137259,
  "cac_inr": 120,
  "headline": {
    "arpu_q1_inr": 70,
    "monthly_churn_q1_pct": 9.0,
    "implied_months_of_life": 11.1,
    "ltv_inr": 776,
    "ltv_to_cac": 6.5
  },
  "honest": {
    "margin_pct": 62,
    "monthly_discount_pct": 1.0,
    "horizon_months": 36,
    "fitted_scale": 13.9,
    "fitted_shape": 0.75,
    "fitted_months_of_life": 13.6,
    "ltv_inr": 530,
    "ltv_to_cac": 4.4
  },
  "payback_month": 4,
  "payback_label": "paid back in month 4",
  "cumulative_margin_per_user_36m_inr": 593,
  "retention_12m_observed_pct": 40.7,
  "retention_12m_fitted_pct": 40.9,
  "gap_pct_of_headline": {
    "margin": -38.0,
    "retention_curve": 13.4,
    "arpu_fade": 1.1,
    "discounting": -8.2
  },
  "flag": null
}
```
</details>

## Portfolio

Blended LTV:CAC is 3.8:1 on the slide and 1.4:1 in the data, across 5 channels and Rs 24.12 Cr of spend.
The blend hides a spread from 0.8:1 (Paid social) to 4.4:1 (Organic); 84% of spend sits in flagged channels (Paid search, Paid social, Affiliates), 16% in channels that honestly clear 3:1.
The money is going wrong in Paid social: Rs 10.0 Cr at a CAC of Rs 634 that is never paid back within 36 months, while Organic is paid back in month 4 on Rs 1.65 Cr.

*source: template (no API key)*

<details><summary>evidence</summary>

```json
{
  "channels": 5,
  "spend_cr": 24.12,
  "users": 615584,
  "blended_cac_inr": 392,
  "blended_headline_ltv_to_cac": 3.8,
  "blended_honest_ltv_to_cac": 1.4,
  "best": {
    "channel": "Organic",
    "honest_ltv_to_cac": 4.4,
    "payback_label": "paid back in month 4",
    "spend_cr": 1.65
  },
  "worst": {
    "channel": "Paid social",
    "honest_ltv_to_cac": 0.8,
    "payback_label": "never paid back within 36 months",
    "spend_cr": 10.0,
    "cac_inr": 634
  },
  "spend_weighted_spread": {
    "min": 0.8,
    "max": 4.4,
    "sd": 1.19
  },
  "flagged_channels": [
    "Paid search",
    "Paid social",
    "Affiliates"
  ],
  "share_of_spend_flagged_pct": 84,
  "share_of_spend_below_1x_pct": 41,
  "share_of_spend_above_3x_pct": 16
}
```
</details>

#!/usr/bin/env python3
"""Run: python test_payback_auditor.py"""
from __future__ import annotations

import unittest

import numpy as np

import llm
import payback_auditor as pa


class PaybackMonth(unittest.TestCase):
    def test_hand_computed_three_month_example(self):
        # ARPU 100, 80, 60 · retention 1.0, 0.5, 0.4 · margin 50%
        # margin revenue per acquired user: 50, 20, 12 -> cumulative 50, 70, 82
        cum = np.array([50.0, 70.0, 82.0])
        self.assertEqual(pa.payback_month(cum, cac=65), 2)      # crosses 65 in month 2
        self.assertEqual(pa.payback_month(cum, cac=50), 1)      # exactly covered in month 1
        self.assertIsNone(pa.payback_month(cum, cac=100))       # never within the horizon


class WeibullFit(unittest.TestCase):
    def test_recovers_known_parameters(self):
        ages = np.arange(18)
        ret = pa.weibull(ages, 9.0, 1.2)
        scale, shape = pa.fit_weibull(ages, ret, np.full(18, 1000.0))
        self.assertAlmostEqual(scale, 9.0, places=3)
        self.assertAlmostEqual(shape, 1.2, places=3)


class Engine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        d = pa.make_cohorts()
        cls.packs = {ch: pa.audit_channel(ch, d[d.channel == ch]) for ch in pa.CHANNELS}
        cls.portfolio = pa.audit_portfolio(list(cls.packs.values()))

    def test_headline_always_exceeds_honest(self):
        for p in self.packs.values():
            self.assertGreater(p["headline"]["ltv_to_cac"], p["honest"]["ltv_to_cac"], p["channel"])

    def test_paid_channels_flagged_and_organic_referral_clean(self):
        for ch in ("Paid search", "Paid social", "Affiliates"):
            self.assertIsNotNone(self.packs[ch]["flag"], ch)
        for ch in ("Referral", "Organic"):
            self.assertIsNone(self.packs[ch]["flag"], ch)
            self.assertLessEqual(self.packs[ch]["payback_month"], 6)
        self.assertIsNone(self.packs["Paid social"]["payback_month"])      # never within 36 months
        self.assertGreater(self.packs["Paid search"]["payback_month"], 18)

    def test_fitted_curve_tracks_observed_retention(self):
        for p in self.packs.values():
            self.assertLess(abs(p["retention_12m_fitted_pct"] - p["retention_12m_observed_pct"]), 2.0, p["channel"])

    def test_blended_sits_inside_the_spread_and_spend_shares_add_up(self):
        s = self.portfolio["spend_weighted_spread"]
        b = self.portfolio["blended_honest_ltv_to_cac"]
        self.assertTrue(s["min"] < b < s["max"])
        self.assertGreater(self.portfolio["share_of_spend_flagged_pct"], 50)
        self.assertLessEqual(self.portfolio["share_of_spend_flagged_pct"]
                             + self.portfolio["share_of_spend_above_3x_pct"], 101)

    def test_templates_render(self):
        for p in self.packs.values():
            text = pa.template_channel(p)
            self.assertEqual(len(text.split("\n")), 2)
            self.assertIn(p["channel"], text)
            self.assertIn(p["payback_label"], text)
        self.assertIn("works in its favour", pa.template_channel(self.packs["Referral"]))
        self.assertEqual(len(pa.template_portfolio(self.portfolio).split("\n")), 3)

    def test_unpinned_catches_an_invented_number(self):
        ev = pa.public(self.packs["Paid social"])
        clean = pa.template_channel(ev)
        self.assertEqual(llm.unpinned(clean, ev), set())
        self.assertIn("2.9", llm.unpinned(clean.replace(str(ev["honest"]["ltv_to_cac"]), "2.9", 1), ev))


if __name__ == "__main__":
    unittest.main(verbosity=2)

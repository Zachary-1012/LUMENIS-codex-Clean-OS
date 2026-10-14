# -*- coding: utf-8 -*-
"""Pure date-range checks for the scope-authorized report facade."""
from __future__ import annotations

import pytest

from lumenis.shared.reporting import export_api as reports


@pytest.mark.parametrize("period", ["daily", "weekly", "monthly", "yearly"])
def test_report_period_resolves_to_an_ordered_iso_range(period):
    kind, start, end = reports._report_period(period, "2026-10-02", "2026-10-02")

    assert kind == period
    assert start == end == "2026-10-02"

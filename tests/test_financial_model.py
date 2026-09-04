"""Tests for the core LBO financial mechanics."""

from __future__ import annotations

import pytest

from model import DEFAULT_SCENARIOS, run_lbo
from model.returns import calculate_exit_equity, calculate_irr, calculate_moic
from model.sensitivity import (
    entry_exit_irr_sensitivity,
    exit_multiple_ebitda_growth_sensitivity,
)


@pytest.fixture(scope="module")
def base_case():
    return run_lbo()


def test_sources_and_uses_balance(base_case):
    sources = base_case.sources_uses.loc[
        base_case.sources_uses["Type"] == "Source", "Amount"
    ].sum()
    uses = base_case.sources_uses.loc[
        base_case.sources_uses["Type"] == "Use", "Amount"
    ].sum()
    assert sources == pytest.approx(uses, abs=0.01)
    assert float(base_case.returns["Entry Equity"]) > 0


def test_debt_roll_forward(base_case):
    schedule = base_case.debt_schedule
    for tranche in base_case.debt_assumptions.tranches:
        expected_closing = (
            schedule[f"{tranche.name} Opening"]
            + schedule[f"{tranche.name} PIK Interest"]
            - schedule[f"{tranche.name} Mandatory Amortization"]
            - schedule[f"{tranche.name} Cash Sweep"]
        )
        assert schedule[f"{tranche.name} Closing"].tolist() == pytest.approx(
            expected_closing.tolist(), abs=0.01
        )
        assert schedule[f"{tranche.name} Closing"].min() >= 0


def test_pik_calculation(base_case):
    schedule = base_case.debt_schedule
    tranche = next(
        item
        for item in base_case.debt_assumptions.tranches
        if item.pik_interest_rate > 0
    )
    expected_pik = schedule[f"{tranche.name} Opening"] * tranche.pik_interest_rate
    assert schedule[f"{tranche.name} PIK Interest"].tolist() == pytest.approx(
        expected_pik.tolist(), abs=0.01
    )
    assert schedule[f"{tranche.name} Cash Interest"].sum() == pytest.approx(0.0)


def test_exit_equity_calculation():
    bridge = calculate_exit_equity(
        exit_ebitda=100.0,
        exit_multiple=8.0,
        closing_debt=250.0,
        closing_cash=20.0,
        exit_fee_pct=0.01,
    )
    assert bridge["Exit Enterprise Value"] == pytest.approx(800.0)
    assert bridge["Less: Exit Fees"] == pytest.approx(8.0)
    assert bridge["Sponsor Equity Value"] == pytest.approx(562.0)


def test_moic_and_irr():
    assert calculate_moic(100.0, 250.0) == pytest.approx(2.5)
    assert calculate_irr(100.0, 250.0, 5) == pytest.approx(2.5 ** (1 / 5) - 1)


def test_sensitivity_base_case_consistency(base_case):
    base_entry_multiple = base_case.entry.entry_multiple
    base_exit_multiple = DEFAULT_SCENARIOS["Base"].exit_multiple
    entry_exit = entry_exit_irr_sensitivity(
        [base_entry_multiple], [base_exit_multiple]
    )
    assert entry_exit.iloc[0, 0] == pytest.approx(
        float(base_case.returns["IRR"]), abs=1e-12
    )

    base_ebitda_cagr = (
        float(base_case.returns["Exit EBITDA"]) / base_case.entry.entry_ebitda
    ) ** (1 / base_case.entry.holding_period) - 1
    growth_sensitivity = exit_multiple_ebitda_growth_sensitivity(
        [base_ebitda_cagr], [base_exit_multiple]
    )
    assert growth_sensitivity.iloc[0, 0] == pytest.approx(
        float(base_case.returns["IRR"]), abs=1e-12
    )


def test_all_financial_checks_pass(base_case):
    assert set(base_case.checks["Status"]) == {"PASS"}

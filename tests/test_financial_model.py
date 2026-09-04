"""Tests for the core LBO financial mechanics."""

from __future__ import annotations

import pytest

from model import (
    DEFAULT_SCENARIOS,
    EntryAssumptions,
    OperatingAssumptions,
    run_lbo,
)
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


def test_ev_to_equity_purchase_price_bridge_with_existing_debt_and_cash():
    entry = EntryAssumptions(
        existing_debt=20_000_000.0,
        existing_cash=10_000_000.0,
        minimum_cash=5_000_000.0,
    )
    result = run_lbo(entry=entry)
    uses = result.sources_uses.set_index("Item")
    assert entry.equity_purchase_price == pytest.approx(
        entry.entry_enterprise_value - entry.existing_debt + entry.existing_cash
    )
    assert uses.loc["Equity purchase price", "Amount"] == pytest.approx(
        entry.equity_purchase_price
    )
    assert uses.loc["Refinance existing debt", "Amount"] == pytest.approx(
        entry.existing_debt
    )
    assert uses.loc["Minimum cash funding", "Amount"] == pytest.approx(0.0)
    assert result.debt_schedule.iloc[0]["Opening Cash"] == pytest.approx(
        entry.existing_cash
    )


def test_primary_scenarios_keep_financing_policy_constant():
    sweep_rates = {scenario.cash_sweep_pct for scenario in DEFAULT_SCENARIOS.values()}
    assert len(sweep_rates) == 1
    assert next(iter(sweep_rates)) == pytest.approx(0.75)


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


def test_cash_sweep_never_exceeds_available_principal(base_case):
    schedule = base_case.debt_schedule
    for tranche in base_case.debt_assumptions.tranches:
        available = (
            schedule[f"{tranche.name} Opening"]
            - schedule[f"{tranche.name} Mandatory Amortization"]
        ).clip(lower=0.0)
        sweep = schedule[f"{tranche.name} Cash Sweep"]
        assert (sweep <= available + 0.01).all()


def test_pik_calculation_and_multiyear_compounding(base_case):
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
    assert schedule.loc[2, f"{tranche.name} Opening"] == pytest.approx(
        schedule.loc[1, f"{tranche.name} Closing"]
    )
    assert schedule.loc[2, f"{tranche.name} PIK Interest"] > schedule.loc[
        1, f"{tranche.name} PIK Interest"
    ]


def test_minimum_liquidity_is_preserved(base_case):
    assert (base_case.debt_schedule["Closing Cash"] >= base_case.entry.minimum_cash).all()
    assert (base_case.debt_schedule["Liquidity Headroom"] >= -0.01).all()


def test_weak_cash_flow_case_raises_liquidity_shortfall():
    stressed_operating = OperatingAssumptions(capex_pct_revenue=0.30)
    with pytest.raises(ValueError, match="Liquidity shortfall"):
        run_lbo(operating=stressed_operating)


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


def test_entry_and_exit_multiple_sensitivity_is_directionally_correct():
    table = entry_exit_irr_sensitivity(
        entry_multiples=[7.0, 8.0],
        exit_multiples=[7.0, 8.0],
    )
    assert table.loc[7.0, 8.0] > table.loc[7.0, 7.0]
    assert table.loc[8.0, 7.0] < table.loc[7.0, 7.0]


def test_bear_base_bull_returns_are_ordered():
    results = {
        name: run_lbo(scenario=scenario)
        for name, scenario in DEFAULT_SCENARIOS.items()
    }
    assert float(results["Bear"].returns["IRR"]) < float(results["Base"].returns["IRR"])
    assert float(results["Base"].returns["IRR"]) < float(results["Bull"].returns["IRR"])


def test_value_creation_bridge_reconciles_to_exit_equity(base_case):
    bridge_exit = float(
        base_case.value_creation.loc[
            base_case.value_creation["Component"] == "Sponsor equity value at exit",
            "Amount",
        ].iloc[0]
    )
    assert bridge_exit == pytest.approx(
        float(base_case.returns["Sponsor Equity Value"]), abs=0.01
    )


def test_all_financial_checks_pass(base_case):
    assert set(base_case.checks["Status"]) == {"PASS"}

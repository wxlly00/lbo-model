"""Orchestration and independent financial consistency checks."""

from __future__ import annotations

from dataclasses import dataclass, replace

import pandas as pd

from .assumptions import (
    DEFAULT_DEBT,
    DEFAULT_ENTRY,
    DEFAULT_OPERATING,
    DEFAULT_SCENARIOS,
    DebtAssumptions,
    EntryAssumptions,
    OperatingAssumptions,
    Scenario,
    validate_assumptions,
)
from .debt import build_debt_schedule, build_sources_and_uses, initial_debt_amounts
from .operating_model import build_operating_model
from .returns import build_value_creation_bridge, calculate_returns


@dataclass
class LBOResult:
    """All schedules and outputs for one scenario."""

    entry: EntryAssumptions
    operating_assumptions: OperatingAssumptions
    debt_assumptions: DebtAssumptions
    scenario: Scenario
    sources_uses: pd.DataFrame
    operating_model: pd.DataFrame
    debt_schedule: pd.DataFrame
    returns: dict[str, float | str]
    value_creation: pd.DataFrame
    checks: pd.DataFrame


def _run_checks(
    entry: EntryAssumptions,
    debt: DebtAssumptions,
    sources_uses: pd.DataFrame,
    operating_model: pd.DataFrame,
    debt_schedule: pd.DataFrame,
    returns: dict[str, float | str],
) -> pd.DataFrame:
    """Run independent reconciliations on key financial mechanics."""

    tolerance = 1.0
    total_sources = float(
        sources_uses.loc[sources_uses["Type"] == "Source", "Amount"].sum()
    )
    total_uses = float(
        sources_uses.loc[sources_uses["Type"] == "Use", "Amount"].sum()
    )
    debt_rollforward_error = 0.0
    minimum_debt_balance = float("inf")
    for tranche in debt.tranches:
        opening = debt_schedule[f"{tranche.name} Opening"]
        pik = debt_schedule[f"{tranche.name} PIK Interest"]
        amortization = debt_schedule[f"{tranche.name} Mandatory Amortization"]
        sweep = debt_schedule[f"{tranche.name} Cash Sweep"]
        closing = debt_schedule[f"{tranche.name} Closing"]
        difference = opening + pik - amortization - sweep - closing
        debt_rollforward_error = max(
            debt_rollforward_error, float(difference.abs().max())
        )
        minimum_debt_balance = min(minimum_debt_balance, float(closing.min()))

    cash_flow_error = (
        debt_schedule["EBITDA"]
        - debt_schedule["CapEx"]
        - debt_schedule["Change in NWC"]
        - debt_schedule["Cash Interest"]
        - debt_schedule["Cash Taxes"]
        - debt_schedule["FCF Before Debt Paydown"]
    ).abs().max()
    cash_rollforward_error = (
        debt_schedule["Opening Cash"]
        + debt_schedule["FCF Before Debt Paydown"]
        - debt_schedule["Mandatory Amortization"]
        - debt_schedule["Cash Sweep"]
        - debt_schedule["Closing Cash"]
    ).abs().max()
    exit_equity_error = abs(
        float(returns["Exit Enterprise Value"])
        - float(returns["Less: Closing Debt"])
        + float(returns["Add: Closing Cash"])
        - float(returns["Less: Exit Fees"])
        - float(returns["Sponsor Equity Value"])
    )
    entry_ev_error = abs(
        entry.entry_enterprise_value - entry.entry_ebitda * entry.entry_multiple
    )
    expected_initial_debt = sum(initial_debt_amounts(entry, debt).values())
    actual_initial_debt = float(
        sources_uses.loc[
            (sources_uses["Type"] == "Source")
            & (sources_uses["Item"] != "Sponsor equity"),
            "Amount",
        ].sum()
    )
    scenario_error = abs(
        float(returns["Exit EBITDA"])
        - float(operating_model.loc[entry.holding_period, "EBITDA"])
    )

    tests = [
        (
            "Sources equal Uses",
            total_sources - total_uses,
            tolerance,
            "Acquisition funding balances.",
        ),
        (
            "Entry EV reconciliation",
            entry_ev_error,
            tolerance,
            "Entry EBITDA multiplied by the entry multiple equals entry EV.",
        ),
        (
            "Initial debt sizing",
            actual_initial_debt - expected_initial_debt,
            tolerance,
            "Debt sources match tranche leverage assumptions.",
        ),
        (
            "Debt roll-forward",
            debt_rollforward_error,
            tolerance,
            "Opening debt plus PIK less amortization and sweep equals closing debt.",
        ),
        (
            "Non-negative debt",
            min(minimum_debt_balance, 0.0),
            tolerance,
            "No tranche is repaid below zero.",
        ),
        (
            "Free cash flow bridge",
            float(cash_flow_error),
            tolerance,
            "EBITDA converts to FCF after CapEx, NWC, cash interest and taxes.",
        ),
        (
            "Cash roll-forward",
            float(cash_rollforward_error),
            tolerance,
            "Opening cash plus FCF less debt repayment equals closing cash.",
        ),
        (
            "Exit EV to equity bridge",
            exit_equity_error,
            tolerance,
            "Exit EV less debt plus cash and less fees equals sponsor equity value.",
        ),
        (
            "Scenario output consistency",
            scenario_error,
            tolerance,
            "Exit returns use the selected scenario's exit EBITDA.",
        ),
    ]
    rows = []
    for name, difference, check_tolerance, description in tests:
        rows.append(
            {
                "Check": name,
                "Difference": difference,
                "Tolerance": check_tolerance,
                "Status": "PASS" if abs(difference) <= check_tolerance else "FAIL",
                "Description": description,
            }
        )
    return pd.DataFrame(rows)


def run_lbo(
    entry: EntryAssumptions = DEFAULT_ENTRY,
    operating: OperatingAssumptions = DEFAULT_OPERATING,
    debt: DebtAssumptions = DEFAULT_DEBT,
    scenario: Scenario = DEFAULT_SCENARIOS["Base"],
    *,
    holding_period: int | None = None,
    entry_multiple: float | None = None,
    exit_multiple: float | None = None,
    target_ebitda_cagr: float | None = None,
) -> LBOResult:
    """Run a complete LBO case, with optional sensitivity overrides."""

    if holding_period is not None:
        entry = replace(entry, holding_period=holding_period)
    if entry_multiple is not None:
        entry = replace(entry, entry_multiple=entry_multiple)
    if exit_multiple is not None:
        scenario = replace(scenario, exit_multiple=exit_multiple)
    if target_ebitda_cagr is not None:
        exit_revenue = entry.entry_revenue * (1 + scenario.revenue_growth) ** entry.holding_period
        target_exit_ebitda = entry.entry_ebitda * (
            1 + target_ebitda_cagr
        ) ** entry.holding_period
        target_exit_margin = target_exit_ebitda / exit_revenue
        margin_expansion = (
            target_exit_margin - entry.entry_ebitda_margin
        ) / entry.holding_period
        scenario = replace(scenario, annual_margin_expansion=margin_expansion)

    validate_assumptions(entry, operating, debt, scenario)
    sources_uses = build_sources_and_uses(entry, debt)
    operating_model = build_operating_model(entry, operating, scenario)
    debt_schedule = build_debt_schedule(
        entry, operating, debt, scenario, operating_model
    )
    returns = calculate_returns(
        entry, scenario, sources_uses, operating_model, debt_schedule
    )
    value_creation = build_value_creation_bridge(entry, sources_uses, returns)
    checks = _run_checks(
        entry, debt, sources_uses, operating_model, debt_schedule, returns
    )
    return LBOResult(
        entry=entry,
        operating_assumptions=operating,
        debt_assumptions=debt,
        scenario=scenario,
        sources_uses=sources_uses,
        operating_model=operating_model,
        debt_schedule=debt_schedule,
        returns=returns,
        value_creation=value_creation,
        checks=checks,
    )


def run_scenarios(
    entry: EntryAssumptions = DEFAULT_ENTRY,
    operating: OperatingAssumptions = DEFAULT_OPERATING,
    debt: DebtAssumptions = DEFAULT_DEBT,
    scenarios: dict[str, Scenario] = DEFAULT_SCENARIOS,
) -> dict[str, LBOResult]:
    """Run the Bear, Base and Bull cases on a consistent capital structure."""

    return {
        name: run_lbo(entry=entry, operating=operating, debt=debt, scenario=scenario)
        for name, scenario in scenarios.items()
    }

"""Scenario-derived return sensitivity tables."""

from __future__ import annotations

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
)
from .engine import LBOResult, run_lbo


def entry_exit_irr_sensitivity(
    entry_multiples: list[float],
    exit_multiples: list[float],
    entry: EntryAssumptions = DEFAULT_ENTRY,
    operating: OperatingAssumptions = DEFAULT_OPERATING,
    debt: DebtAssumptions = DEFAULT_DEBT,
    scenario: Scenario = DEFAULT_SCENARIOS["Base"],
) -> pd.DataFrame:
    """Re-run the full model for entry- and exit-multiple combinations."""

    values = []
    for entry_multiple in entry_multiples:
        row = []
        for exit_multiple in exit_multiples:
            result = run_lbo(
                entry=entry,
                operating=operating,
                debt=debt,
                scenario=scenario,
                entry_multiple=entry_multiple,
                exit_multiple=exit_multiple,
            )
            row.append(float(result.returns["IRR"]))
        values.append(row)
    frame = pd.DataFrame(values, index=entry_multiples, columns=exit_multiples)
    frame.index.name = "Entry Multiple"
    frame.columns.name = "Exit Multiple"
    return frame


def exit_multiple_ebitda_growth_sensitivity(
    ebitda_cagrs: list[float],
    exit_multiples: list[float],
    entry: EntryAssumptions = DEFAULT_ENTRY,
    operating: OperatingAssumptions = DEFAULT_OPERATING,
    debt: DebtAssumptions = DEFAULT_DEBT,
    scenario: Scenario = DEFAULT_SCENARIOS["Base"],
) -> pd.DataFrame:
    """Re-run cash flow and debt mechanics for exit EBITDA CAGR outcomes."""

    values = []
    for ebitda_cagr in ebitda_cagrs:
        row = []
        for exit_multiple in exit_multiples:
            result = run_lbo(
                entry=entry,
                operating=operating,
                debt=debt,
                scenario=scenario,
                target_ebitda_cagr=ebitda_cagr,
                exit_multiple=exit_multiple,
            )
            row.append(float(result.returns["IRR"]))
        values.append(row)
    frame = pd.DataFrame(values, index=ebitda_cagrs, columns=exit_multiples)
    frame.index.name = "Exit EBITDA CAGR"
    frame.columns.name = "Exit Multiple"
    return frame


def holding_period_sensitivity(
    holding_periods: list[int],
    entry: EntryAssumptions = DEFAULT_ENTRY,
    operating: OperatingAssumptions = DEFAULT_OPERATING,
    debt: DebtAssumptions = DEFAULT_DEBT,
    scenario: Scenario = DEFAULT_SCENARIOS["Base"],
) -> pd.DataFrame:
    """Compare returns and deleveraging across alternative exit years."""

    rows = []
    for holding_period in holding_periods:
        result = run_lbo(
            entry=entry,
            operating=operating,
            debt=debt,
            scenario=scenario,
            holding_period=holding_period,
        )
        rows.append(
            {
                "Holding Period": holding_period,
                "Exit EBITDA": float(result.returns["Exit EBITDA"]),
                "Exit Equity Value": float(result.returns["Sponsor Equity Value"]),
                "MOIC": float(result.returns["MOIC"]),
                "IRR": float(result.returns["IRR"]),
                "Exit Net Debt / EBITDA": float(
                    result.returns["Exit Net Debt / EBITDA"]
                ),
            }
        )
    return pd.DataFrame(rows).set_index("Holding Period")


def default_sensitivities(
    base_result: LBOResult | None = None,
) -> dict[str, pd.DataFrame]:
    """Build the three standard sensitivity outputs used in the deliverables."""

    entry_multiples = [6.5, 7.0, 7.5, 8.0, 8.5]
    exit_multiples = [6.5, 7.0, 7.5, 8.0, 8.5]
    if base_result is None:
        base = run_lbo()
    else:
        base = base_result
    years = int(base.entry.holding_period)
    base_cagr = (
        float(base.returns["Exit EBITDA"]) / base.entry.entry_ebitda
    ) ** (1 / years) - 1
    ebitda_cagrs = [base_cagr + shift for shift in (-0.02, -0.01, 0.0, 0.01, 0.02)]
    return {
        "Entry x Exit IRR": entry_exit_irr_sensitivity(
            entry_multiples,
            exit_multiples,
            entry=base.entry,
            operating=base.operating_assumptions,
            debt=base.debt_assumptions,
            scenario=base.scenario,
        ),
        "Exit x EBITDA Growth IRR": exit_multiple_ebitda_growth_sensitivity(
            ebitda_cagrs,
            exit_multiples,
            entry=base.entry,
            operating=base.operating_assumptions,
            debt=base.debt_assumptions,
            scenario=base.scenario,
        ),
        "Holding Period": holding_period_sensitivity(
            [3, 4, 5, 6, 7],
            entry=base.entry,
            operating=base.operating_assumptions,
            debt=base.debt_assumptions,
            scenario=base.scenario,
        ),
    }

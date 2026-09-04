"""Exit valuation, sponsor returns and equity value creation."""

from __future__ import annotations

import math

import pandas as pd

from .assumptions import EntryAssumptions, Scenario
from .debt import sponsor_equity_from_sources_uses


def calculate_moic(entry_equity: float, exit_equity: float) -> float:
    """Calculate sponsor multiple on invested capital."""

    if entry_equity <= 0:
        raise ValueError("Entry equity must be positive.")
    return exit_equity / entry_equity


def calculate_irr(entry_equity: float, exit_equity: float, years: int) -> float:
    """Calculate annualized sponsor IRR with no interim distributions."""

    if entry_equity <= 0 or exit_equity < 0 or years < 1:
        raise ValueError("IRR inputs are invalid.")
    return (exit_equity / entry_equity) ** (1 / years) - 1


def calculate_exit_equity(
    exit_ebitda: float,
    exit_multiple: float,
    closing_debt: float,
    closing_cash: float,
    exit_fee_pct: float,
) -> dict[str, float]:
    """Reconcile exit enterprise value to sponsor equity proceeds."""

    exit_enterprise_value = exit_ebitda * exit_multiple
    exit_fees = exit_enterprise_value * exit_fee_pct
    sponsor_equity_value = (
        exit_enterprise_value - closing_debt + closing_cash - exit_fees
    )
    return {
        "Exit EBITDA": exit_ebitda,
        "Exit Multiple": exit_multiple,
        "Exit Enterprise Value": exit_enterprise_value,
        "Less: Closing Debt": closing_debt,
        "Add: Closing Cash": closing_cash,
        "Less: Exit Fees": exit_fees,
        "Sponsor Equity Value": sponsor_equity_value,
    }


def calculate_returns(
    entry: EntryAssumptions,
    scenario: Scenario,
    sources_uses: pd.DataFrame,
    operating_model: pd.DataFrame,
    debt_schedule: pd.DataFrame,
) -> dict[str, float | str]:
    """Calculate the selected scenario's exit bridge and sponsor returns."""

    exit_year = entry.holding_period
    exit_ebitda = float(operating_model.loc[exit_year, "EBITDA"])
    closing_debt = float(debt_schedule.loc[exit_year, "Total Debt"])
    closing_cash = float(debt_schedule.loc[exit_year, "Closing Cash"])
    bridge = calculate_exit_equity(
        exit_ebitda=exit_ebitda,
        exit_multiple=scenario.exit_multiple,
        closing_debt=closing_debt,
        closing_cash=closing_cash,
        exit_fee_pct=entry.exit_fee_pct,
    )
    entry_equity = sponsor_equity_from_sources_uses(sources_uses)
    exit_equity = bridge["Sponsor Equity Value"]
    if exit_equity < 0:
        moic = exit_equity / entry_equity
        irr = math.nan
    else:
        moic = calculate_moic(entry_equity, exit_equity)
        irr = calculate_irr(entry_equity, exit_equity, exit_year)

    debt_source_names = {
        item
        for item in sources_uses.loc[
            sources_uses["Type"] == "Source", "Item"
        ].tolist()
        if item != "Sponsor equity"
    }
    initial_debt = float(
        sources_uses.loc[
            (sources_uses["Type"] == "Source")
            & (sources_uses["Item"].isin(debt_source_names)),
            "Amount",
        ].sum()
    )
    return {
        "Scenario": scenario.name,
        "Entry Equity": entry_equity,
        **bridge,
        "MOIC": moic,
        "IRR": irr,
        "Gross Debt Paydown": initial_debt - closing_debt,
        "Exit Net Debt": closing_debt - closing_cash,
        "Exit Net Debt / EBITDA": float(
            debt_schedule.loc[exit_year, "Net Debt / EBITDA"]
        ),
    }


def build_value_creation_bridge(
    entry: EntryAssumptions,
    sources_uses: pd.DataFrame,
    returns: dict[str, float | str],
) -> pd.DataFrame:
    """Bridge sponsor equity invested to equity value at exit."""

    uses = sources_uses.loc[sources_uses["Type"] == "Use"].set_index("Item")
    entry_equity = float(returns["Entry Equity"])
    exit_ebitda = float(returns["Exit EBITDA"])
    exit_multiple = float(returns["Exit Multiple"])
    closing_debt = float(returns["Less: Closing Debt"])
    closing_cash = float(returns["Add: Closing Cash"])
    initial_debt = float(
        sources_uses.loc[
            (sources_uses["Type"] == "Source")
            & (sources_uses["Item"] != "Sponsor equity"),
            "Amount",
        ].sum()
    )
    entry_fees = float(
        uses.loc["Transaction fees", "Amount"] + uses.loc["Financing fees", "Amount"]
    )
    contributions = [
        ("Sponsor equity invested", entry_equity),
        (
            "EBITDA growth",
            (exit_ebitda - entry.entry_ebitda) * entry.entry_multiple,
        ),
        (
            "Multiple expansion / (contraction)",
            exit_ebitda * (exit_multiple - entry.entry_multiple),
        ),
        ("Gross debt paydown", initial_debt - closing_debt),
        ("Change in cash", closing_cash - entry.opening_cash),
        ("Entry fees", -entry_fees),
        ("Exit fees", -float(returns["Less: Exit Fees"])),
    ]
    rows = [{"Component": name, "Amount": amount} for name, amount in contributions]
    rows.append(
        {
            "Component": "Sponsor equity value at exit",
            "Amount": sum(amount for _, amount in contributions),
        }
    )
    return pd.DataFrame(rows)

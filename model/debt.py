"""Sources & Uses and debt-service schedules."""

from __future__ import annotations

import pandas as pd

from .assumptions import (
    DebtAssumptions,
    EntryAssumptions,
    OperatingAssumptions,
    Scenario,
)


def initial_debt_amounts(
    entry: EntryAssumptions, debt: DebtAssumptions
) -> dict[str, float]:
    """Size debt tranches from entry EBITDA and leverage multiples."""

    return {
        tranche.name: entry.entry_ebitda * tranche.leverage_multiple
        for tranche in debt.tranches
    }


def build_sources_and_uses(
    entry: EntryAssumptions, debt: DebtAssumptions
) -> pd.DataFrame:
    """Build a standard PE acquisition Sources & Uses schedule.

    Equity purchase price is bridged from enterprise value using existing debt
    and cash. Existing debt is then refinanced as a separate use. The default
    fictional case is cash-free / debt-free, but the bridge remains explicit so
    the transaction logic is visible.
    """

    debt_amounts = initial_debt_amounts(entry, debt)
    total_new_debt = sum(debt_amounts.values())
    transaction_fees = entry.entry_enterprise_value * entry.transaction_fee_pct
    financing_fees = total_new_debt * entry.financing_fee_pct
    total_uses = (
        entry.equity_purchase_price
        + entry.existing_debt
        + transaction_fees
        + financing_fees
        + entry.minimum_cash_funding
    )
    sponsor_equity = total_uses - total_new_debt
    if sponsor_equity <= 0:
        raise ValueError("Debt sources cannot exceed total acquisition uses.")

    rows: list[dict[str, str | float]] = [
        {"Type": "Use", "Item": "Equity purchase price", "Amount": entry.equity_purchase_price},
        {"Type": "Use", "Item": "Refinance existing debt", "Amount": entry.existing_debt},
        {"Type": "Use", "Item": "Transaction fees", "Amount": transaction_fees},
        {"Type": "Use", "Item": "Financing fees", "Amount": financing_fees},
        {"Type": "Use", "Item": "Minimum cash funding", "Amount": entry.minimum_cash_funding},
    ]
    rows.extend(
        {"Type": "Source", "Item": name, "Amount": amount}
        for name, amount in debt_amounts.items()
    )
    rows.append({"Type": "Source", "Item": "Sponsor equity", "Amount": sponsor_equity})
    return pd.DataFrame(rows)


def sponsor_equity_from_sources_uses(sources_uses: pd.DataFrame) -> float:
    """Return the sponsor-equity source from the transaction schedule."""

    row = sources_uses.loc[
        (sources_uses["Type"] == "Source")
        & (sources_uses["Item"] == "Sponsor equity"),
        "Amount",
    ]
    if len(row) != 1:
        raise ValueError("Sources & Uses must contain exactly one sponsor-equity row.")
    return float(row.iloc[0])


def build_debt_schedule(
    entry: EntryAssumptions,
    operating_assumptions: OperatingAssumptions,
    debt: DebtAssumptions,
    scenario: Scenario,
    operating_model: pd.DataFrame,
) -> pd.DataFrame:
    """Model cash interest, PIK, amortization and an end-of-year cash sweep.

    Cash interest uses the average scheduled balance before the year-end cash
    sweep. PIK accrues on opening principal and is assumed tax-deductible for
    this simplified portfolio model. Jurisdiction-specific interest deduction
    limits and NOL carryforwards are intentionally outside scope.

    The model does not silently permit a liquidity deficit. If operating FCF
    and mandatory amortization would push cash below the required minimum, the
    case raises a liquidity-shortfall error. A real underwriting model would
    normally add a revolver or another committed liquidity facility.
    """

    original_balances = initial_debt_amounts(entry, debt)
    balances = dict(original_balances)
    opening_cash = entry.opening_cash
    rows: list[dict[str, float | int]] = []

    for year in range(1, entry.holding_period + 1):
        row: dict[str, float | int] = {
            "Year": year,
            "Opening Cash": opening_cash,
            "EBITDA": float(operating_model.loc[year, "EBITDA"]),
            "EBIT": float(operating_model.loc[year, "EBIT"]),
            "CapEx": float(operating_model.loc[year, "CapEx"]),
            "Change in NWC": float(operating_model.loc[year, "Change in NWC"]),
        }
        tranche_work: dict[str, dict[str, float]] = {}
        total_cash_interest = 0.0
        total_pik_interest = 0.0
        total_mandatory = 0.0

        for tranche in debt.tranches:
            opening = balances[tranche.name]
            mandatory = min(
                original_balances[tranche.name]
                * tranche.mandatory_amortization_pct,
                opening,
            )
            average_pre_sweep_balance = opening - mandatory / 2
            cash_interest = average_pre_sweep_balance * tranche.cash_interest_rate
            pik_interest = opening * tranche.pik_interest_rate
            tranche_work[tranche.name] = {
                "Opening": opening,
                "Cash Interest": cash_interest,
                "PIK Interest": pik_interest,
                "Mandatory Amortization": mandatory,
                "Cash Sweep": 0.0,
            }
            total_cash_interest += cash_interest
            total_pik_interest += pik_interest
            total_mandatory += mandatory

        ebt = row["EBIT"] - total_cash_interest - total_pik_interest
        cash_taxes = max(float(ebt) * operating_assumptions.tax_rate, 0.0)
        fcf_before_debt_paydown = (
            row["EBITDA"]
            - row["CapEx"]
            - row["Change in NWC"]
            - total_cash_interest
            - cash_taxes
        )
        cash_before_sweep = opening_cash + fcf_before_debt_paydown - total_mandatory
        liquidity_shortfall = max(entry.minimum_cash - cash_before_sweep, 0.0)
        if liquidity_shortfall > 0.01:
            raise ValueError(
                f"Liquidity shortfall in Year {year}: "
                f"cash before optional sweep is {cash_before_sweep:,.2f} versus "
                f"minimum cash of {entry.minimum_cash:,.2f}. "
                "Add a revolver or revise the underwriting assumptions."
            )

        excess_cash = max(cash_before_sweep - entry.minimum_cash, 0.0)
        sweep_budget = excess_cash * scenario.cash_sweep_pct

        for tranche in sorted(debt.tranches, key=lambda item: item.sweep_priority):
            if not tranche.cash_sweep_eligible or sweep_budget <= 0:
                continue
            available_principal = max(
                tranche_work[tranche.name]["Opening"]
                - tranche_work[tranche.name]["Mandatory Amortization"],
                0.0,
            )
            sweep = min(available_principal, sweep_budget)
            tranche_work[tranche.name]["Cash Sweep"] = sweep
            sweep_budget -= sweep

        total_sweep = sum(item["Cash Sweep"] for item in tranche_work.values())
        closing_cash = cash_before_sweep - total_sweep

        for tranche in debt.tranches:
            values = tranche_work[tranche.name]
            closing = (
                values["Opening"]
                + values["PIK Interest"]
                - values["Mandatory Amortization"]
                - values["Cash Sweep"]
            )
            balances[tranche.name] = max(closing, 0.0)
            for metric, amount in values.items():
                row[f"{tranche.name} {metric}"] = amount
            row[f"{tranche.name} Closing"] = balances[tranche.name]

        total_debt = sum(balances.values())
        net_debt = total_debt - closing_cash
        row.update(
            {
                "Cash Interest": total_cash_interest,
                "PIK Interest": total_pik_interest,
                "EBT": ebt,
                "Cash Taxes": cash_taxes,
                "FCF Before Debt Paydown": fcf_before_debt_paydown,
                "Mandatory Amortization": total_mandatory,
                "Cash Before Sweep": cash_before_sweep,
                "Cash Sweep": total_sweep,
                "Closing Cash": closing_cash,
                "Minimum Cash": entry.minimum_cash,
                "Liquidity Headroom": closing_cash - entry.minimum_cash,
                "Total Debt": total_debt,
                "Net Debt": net_debt,
                "Net Debt / EBITDA": net_debt / row["EBITDA"],
            }
        )
        rows.append(row)
        opening_cash = closing_cash

    return pd.DataFrame(rows).set_index("Year")

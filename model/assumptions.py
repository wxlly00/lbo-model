"""Model assumptions and the fictional Northstar Components case."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EntryAssumptions:
    """Purchase price, fees, liquidity and holding-period assumptions."""

    company: str = "Northstar Components"
    currency: str = "EUR"
    entry_revenue: float = 300_000_000.0
    entry_ebitda_margin: float = 0.20
    entry_multiple: float = 7.50
    transaction_fee_pct: float = 0.02
    financing_fee_pct: float = 0.02
    minimum_cash: float = 5_000_000.0
    exit_fee_pct: float = 0.01
    holding_period: int = 5

    @property
    def entry_ebitda(self) -> float:
        return self.entry_revenue * self.entry_ebitda_margin

    @property
    def entry_enterprise_value(self) -> float:
        return self.entry_ebitda * self.entry_multiple


@dataclass(frozen=True)
class OperatingAssumptions:
    """Operating and cash conversion assumptions shared by all scenarios."""

    da_pct_revenue: float = 0.04
    capex_pct_revenue: float = 0.03
    nwc_pct_revenue: float = 0.15
    tax_rate: float = 0.28


@dataclass(frozen=True)
class DebtTranche:
    """Terms for one debt tranche, sized as a multiple of entry EBITDA."""

    name: str
    leverage_multiple: float
    cash_interest_rate: float
    pik_interest_rate: float = 0.0
    mandatory_amortization_pct: float = 0.0
    cash_sweep_eligible: bool = True
    sweep_priority: int = 1


@dataclass(frozen=True)
class DebtAssumptions:
    """Debt package used to fund the acquisition."""

    tranches: tuple[DebtTranche, ...]


@dataclass(frozen=True)
class Scenario:
    """Operating and exit assumptions for one underwriting case."""

    name: str
    revenue_growth: float
    annual_margin_expansion: float
    exit_multiple: float
    cash_sweep_pct: float


DEFAULT_ENTRY = EntryAssumptions()
DEFAULT_OPERATING = OperatingAssumptions()
DEFAULT_DEBT = DebtAssumptions(
    tranches=(
        DebtTranche(
            name="Term Loan A",
            leverage_multiple=3.00,
            cash_interest_rate=0.060,
            mandatory_amortization_pct=0.050,
            sweep_priority=1,
        ),
        DebtTranche(
            name="Term Loan B",
            leverage_multiple=1.00,
            cash_interest_rate=0.070,
            mandatory_amortization_pct=0.010,
            sweep_priority=2,
        ),
        DebtTranche(
            name="Subordinated PIK Note",
            leverage_multiple=0.50,
            cash_interest_rate=0.000,
            pik_interest_rate=0.100,
            mandatory_amortization_pct=0.000,
            cash_sweep_eligible=False,
            sweep_priority=99,
        ),
    )
)

# The capital structure is held constant across cases so that the operating and
# exit risks remain comparable. The cash-sweep percentage is the debt-policy
# variable that changes by scenario.
DEFAULT_SCENARIOS = {
    "Bear": Scenario(
        name="Bear",
        revenue_growth=0.030,
        annual_margin_expansion=0.000,
        exit_multiple=6.50,
        cash_sweep_pct=0.50,
    ),
    "Base": Scenario(
        name="Base",
        revenue_growth=0.070,
        annual_margin_expansion=0.005,
        exit_multiple=7.50,
        cash_sweep_pct=0.75,
    ),
    "Bull": Scenario(
        name="Bull",
        revenue_growth=0.100,
        annual_margin_expansion=0.0075,
        exit_multiple=8.50,
        cash_sweep_pct=1.00,
    ),
}


def validate_assumptions(
    entry: EntryAssumptions,
    operating: OperatingAssumptions,
    debt: DebtAssumptions,
    scenario: Scenario,
) -> None:
    """Reject assumptions that would make the model misleading or undefined."""

    if entry.entry_revenue <= 0 or entry.entry_ebitda_margin <= 0:
        raise ValueError("Entry revenue and EBITDA margin must be positive.")
    if entry.entry_multiple <= 0 or entry.holding_period < 1:
        raise ValueError("Entry multiple and holding period must be positive.")
    if entry.minimum_cash < 0:
        raise ValueError("Minimum cash cannot be negative.")
    for rate in (
        entry.transaction_fee_pct,
        entry.financing_fee_pct,
        entry.exit_fee_pct,
        operating.da_pct_revenue,
        operating.capex_pct_revenue,
        operating.nwc_pct_revenue,
        operating.tax_rate,
        scenario.cash_sweep_pct,
    ):
        if not 0 <= rate <= 1:
            raise ValueError("Percentage assumptions must fall between 0% and 100%.")
    if scenario.revenue_growth <= -1 or scenario.exit_multiple <= 0:
        raise ValueError("Scenario growth and exit multiple are invalid.")
    if not debt.tranches:
        raise ValueError("At least one debt tranche is required.")
    names = [tranche.name for tranche in debt.tranches]
    if len(names) != len(set(names)):
        raise ValueError("Debt tranche names must be unique.")
    for tranche in debt.tranches:
        if min(
            tranche.leverage_multiple,
            tranche.cash_interest_rate,
            tranche.pik_interest_rate,
            tranche.mandatory_amortization_pct,
        ) < 0:
            raise ValueError(f"Debt terms cannot be negative: {tranche.name}.")

"""Operating forecast for the fictional target company."""

from __future__ import annotations

import pandas as pd

from .assumptions import EntryAssumptions, OperatingAssumptions, Scenario


def build_operating_model(
    entry: EntryAssumptions,
    operating: OperatingAssumptions,
    scenario: Scenario,
) -> pd.DataFrame:
    """Project the income statement and core cash-conversion drivers."""

    rows: list[dict[str, float | int]] = []
    prior_revenue = entry.entry_revenue
    prior_nwc = entry.entry_revenue * operating.nwc_pct_revenue

    rows.append(
        {
            "Year": 0,
            "Revenue Growth": 0.0,
            "Revenue": entry.entry_revenue,
            "EBITDA Margin": entry.entry_ebitda_margin,
            "EBITDA": entry.entry_ebitda,
            "D&A": entry.entry_revenue * operating.da_pct_revenue,
            "EBIT": entry.entry_ebitda
            - entry.entry_revenue * operating.da_pct_revenue,
            "CapEx": 0.0,
            "NWC": prior_nwc,
            "Change in NWC": 0.0,
        }
    )

    for year in range(1, entry.holding_period + 1):
        revenue = prior_revenue * (1 + scenario.revenue_growth)
        margin = entry.entry_ebitda_margin + scenario.annual_margin_expansion * year
        if not 0 < margin < 1:
            raise ValueError(f"EBITDA margin is invalid in Year {year}: {margin:.1%}.")
        ebitda = revenue * margin
        da = revenue * operating.da_pct_revenue
        nwc = revenue * operating.nwc_pct_revenue
        rows.append(
            {
                "Year": year,
                "Revenue Growth": scenario.revenue_growth,
                "Revenue": revenue,
                "EBITDA Margin": margin,
                "EBITDA": ebitda,
                "D&A": da,
                "EBIT": ebitda - da,
                "CapEx": revenue * operating.capex_pct_revenue,
                "NWC": nwc,
                "Change in NWC": nwc - prior_nwc,
            }
        )
        prior_revenue = revenue
        prior_nwc = nwc

    return pd.DataFrame(rows).set_index("Year")

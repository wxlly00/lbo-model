# LBO Investment Model

A transparent Python and Excel leveraged buyout model for a fictional European industrial components distributor. The case connects operating performance, cash conversion, debt repayment and exit valuation to sponsor returns across Bear, Base and Bull scenarios.

## Investment Case

Northstar Components is a fictional distributor serving recurring maintenance and replacement demand across fragmented industrial end markets. The underwriting case assumes that revenue growth, measured margin improvement and disciplined cash conversion can reduce leverage while preserving strategic flexibility.

The central risks are slower end-market growth, failure to deliver margin improvement, PIK accumulation, liquidity pressure and exit-multiple contraction. The model holds the entry capital structure and cash-sweep policy constant across Bear, Base and Bull so that the primary scenario comparison isolates operating performance and exit valuation.

## Transaction Overview

All amounts are fictional and shown in EUR. The default case assumes a cash-free / debt-free acquisition at signing, while the model explicitly supports existing debt and cash through an EV-to-equity purchase price bridge.

| Metric | Amount |
|---|---:|
| Entry Revenue | €300.0M |
| Entry EBITDA | €60.0M |
| Entry EBITDA Margin | 20.0% |
| Entry Multiple | 7.5x |
| Entry Enterprise Value | €450.0M |
| Initial Gross Debt | €270.0M |
| Initial Gross Leverage | 4.5x |
| Sponsor Equity | €199.4M |

Sources & Uses now follows a standard PE transaction bridge:

```text
Enterprise Value
− Existing Debt
+ Existing Cash
= Equity Purchase Price

Equity Purchase Price
+ Refinance Existing Debt
+ Transaction Fees
+ Financing Fees
+ Minimum Cash Funding
= Total Uses
```

The default case includes €9.0M of transaction fees, €5.4M of financing fees and €5.0M of minimum cash funding. Debt comprises a €180.0M Term Loan A, a €60.0M Term Loan B and a €30.0M subordinated PIK note.

## Operating Case

| Assumption | Bear | Base | Bull |
|---|---:|---:|---:|
| Annual Revenue Growth | 3.0% | 7.0% | 10.0% |
| Annual EBITDA Margin Expansion | 0 bps | 50 bps | 75 bps |
| Exit EBITDA Margin | 20.0% | 22.5% | 23.8% |
| Exit Multiple | 6.5x | 7.5x | 8.5x |
| Cash Sweep | 75% | 75% | 75% |

The common operating assumptions are D&A at 4.0% of revenue, CapEx at 3.0% of revenue, NWC at 15.0% of revenue and a 28.0% cash tax rate. Change in NWC is calculated from the annual NWC balance rather than as a percentage of total revenue.

![Revenue and EBITDA evolution](assets/revenue_ebitda.png)

## Value Creation

The Base Case increases sponsor equity value from €199.4M at entry to €618.9M at exit.

| Component | Contribution |
|---|---:|
| EBITDA Growth | €260.0M |
| Multiple Expansion / (Contraction) | €0.0M |
| Gross Debt Paydown | €167.4M |
| Change in Cash | €13.6M |
| Entry and Exit Fees | (€21.5M) |

The value-creation bridge reconciles to exit sponsor equity. With the Base Case exit multiple equal to the entry multiple, returns are driven by EBITDA growth and deleveraging rather than multiple expansion.

![Sponsor equity value creation](assets/equity_value_creation.png)

## Returns

| Scenario | Exit EBITDA | Exit Equity Value | Debt Paydown | Exit Net Leverage | MOIC | IRR |
|---|---:|---:|---:|---:|---:|---:|
| Bear | €69.6M | €326.5M | €134.9M | 1.74x | 1.64x | 10.4% |
| Base | €94.7M | €618.9M | €167.4M | 0.89x | 3.10x | 25.4% |
| Bull | €114.7M | €908.1M | €190.5M | 0.50x | 4.55x | 35.4% |

IRR assumes one sponsor outflow at entry, no interim dividends and one realization at exit. Financing policy is deliberately held constant across the three underwriting cases.

## Deleveraging

The debt schedule calculates cash interest on average scheduled pre-sweep balances, mandatory amortization by tranche, PIK interest on opening principal and an end-of-year cash sweep. The PIK note grows from €30.0M to €48.3M in the Base Case while cash-pay debt is reduced more quickly.

| Base Case | Year 1 | Year 2 | Year 3 | Year 4 | Year 5 |
|---|---:|---:|---:|---:|---:|
| Gross Debt | €249.3M | €221.5M | €188.0M | €148.6M | €102.6M |
| Closing Cash | €9.7M | €12.1M | €14.2M | €16.3M | €18.6M |
| Net Debt | €239.6M | €209.4M | €173.8M | €132.3M | €84.1M |
| Net Debt / EBITDA | 3.64x | 2.90x | 2.20x | 1.53x | 0.89x |

The model enforces a minimum-liquidity requirement before any optional cash sweep. If operating FCF and mandatory amortization would push cash below the minimum, the case stops with an explicit liquidity-shortfall error rather than silently running with negative or insufficient cash. In a real transaction, that shortfall would normally be addressed with a revolver or another committed liquidity facility.

![Debt paydown](assets/debt_paydown.png)

![Net leverage](assets/net_leverage.png)

## Sensitivities

The model re-runs operating cash flow, debt paydown and exit returns for each sensitivity cell. It includes:

- Entry Multiple × Exit Multiple sensitivity for IRR
- Exit Multiple × Exit EBITDA CAGR sensitivity for IRR
- Holding period sensitivity from three to seven years

The test suite also verifies directional behavior: a higher exit multiple increases IRR and a higher entry multiple decreases IRR, all else equal.

![IRR sensitivity heatmap](assets/irr_sensitivity_heatmap.png)

## Model Architecture

| Module | Responsibility |
|---|---|
| `model/assumptions.py` | Entry, operating, debt and scenario assumptions |
| `model/operating_model.py` | Revenue, EBITDA, D&A, EBIT, CapEx and NWC projection |
| `model/debt.py` | Sources & Uses, cash interest, PIK, amortization, liquidity protection and cash sweep |
| `model/returns.py` | Exit equity bridge, MOIC, IRR and value creation |
| `model/sensitivity.py` | Return sensitivities with full model recalculation |
| `model/excel_export.py` | Six-sheet professional Excel workbook |
| `model/charts.py` | README and presentation chart assets |
| `model/engine.py` | Model orchestration and independent financial consistency checks |

The Python model is the source of truth. The Excel workbook is generated from the same calculated schedules and contains `Summary`, `Assumptions`, `Operating Model`, `Debt Schedule`, `Returns` and `Sensitivities` sheets.

## How to Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python lbo_model.py
pytest
```

The command generates:

- `outputs/LBO_Investment_Model.xlsx`
- Six charts in `assets/`

## Model Checks

The model reports explicit checks for:

- Sources = Uses;
- entry EV reconciliation;
- EV-to-equity purchase price reconciliation;
- initial debt sizing;
- debt roll-forwards;
- non-negative debt balances;
- cash sweep capped by available debt;
- the FCF bridge;
- cash roll-forward;
- minimum liquidity;
- exit EV to equity value; and
- scenario consistency.

The automated test suite additionally challenges multi-year PIK compounding, weak-FCF liquidity failure, Bear/Base/Bull ordering and sensitivity directionality.

## Limitations

The transaction and company are entirely fictional. This project is an analytical and portfolio exercise and does not represent transaction experience, investment advice or a production underwriting model.

The model does not include a full three-statement balance sheet, purchase accounting, a fully modelled revolver, management incentive dilution or interim sponsor distributions. PIK interest is assumed tax-deductible for modelling purposes; interest-deduction limitations, NOL carryforwards and jurisdiction-specific tax rules are not modelled. Mandatory amortization occurs during the year and the cash sweep occurs at year-end. Cash interest uses average scheduled pre-sweep debt to avoid a circular reference. Any real underwriting case would require diligence-backed operating drivers, legal debt terms, detailed liquidity facilities and jurisdiction-specific tax analysis.

## Author

**Wilfried LAWSON HELLU**

Finance × Data × Software

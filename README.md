# LBO Model — Private Equity Analysis

> End-to-end Leveraged Buyout financial model with multi-scenario returns analysis

[![Python](https://img.shields.io/badge/Python-3.11-blue)](https://python.org)
[![Finance](https://img.shields.io/badge/Domain-Private%20Equity-purple)]()

## Deal Overview

| Parameter | Value |
|-----------|-------|
| Target | TechRetail SA |
| Entry EV | €450M |
| Entry Multiple | 7.5x EBITDA |
| Senior Debt | €247.5M @ 6% |
| Mezzanine (PIK) | €67.5M @ 10% |
| Equity | €135M (30%) |
| Holding Period | 5 years |

## Model Components

- **Income Statement** — Revenue CAGR 8%, margin expansion +1%/yr, D&A and EBIT projections
- **Debt Schedule** — Senior mandatory amortization (5%/yr) + Mezzanine PIK accrual
- **Cash Flow Model** — EBITDA → FCF with capex, working capital, and debt service
- **Exit Analysis** — Bear/Base/Bull scenarios with IRR, MOIC, and DPI calculation
- **Excel Output** — Professional 3-sheet Excel file with formatted tables

## Exit Scenarios

| Scenario | Multiple | IRR | MOIC |
|----------|----------|-----|------|
| Bear Case | 6.0x | ~15% | ~2.2x |
| Base Case | 7.5x | ~22% | ~3.1x |
| Bull Case | 9.0x | ~29% | ~4.2x |

## Tech Stack

`Python 3.11` `pandas` `numpy` `openpyxl` `tabulate`

## How to Run

```bash
pip install -r requirements.txt
python lbo_model.py
```

Output: Formatted tables in terminal + `lbo_output.xlsx`

## Key Concepts

- **MOIC** (Multiple on Invested Capital): Exit Equity / Entry Equity
- **IRR**: Annualized return solving for NPV = 0
- **PIK** (Payment-in-Kind): Mezzanine interest accrues to principal (no cash payment)
- **Debt waterfall**: Senior repaid first from FCF before mezz

## Author

**Wilfried LAWSON HELLU** | Finance Analyst  
📧 wilfriedlawpro@gmail.com | 🔗 [LinkedIn](https://linkedin.com/in/wilfried-lawsonhellu) | 🐙 [GitHub](https://github.com/Wxlly00)

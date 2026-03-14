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

## Model Inputs Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `ENTRY_EV` | €450M | Enterprise Value paid at acquisition |
| `ENTRY_EBITDA` | €60M | LTM EBITDA at entry (7.5× multiple) |
| `REVENUE_Y0` | €300M | Base year revenue |
| `EBITDA_MARGIN_Y0` | 20% | Base EBITDA margin |
| `REVENUE_CAGR` | 8% | Annual revenue growth assumption |
| `MARGIN_EXPANSION` | +1%/yr | EBITDA margin improvement per year |
| `DA_PCT` | 4% | D&A as % of revenue |
| `CAPEX_PCT` | 3% | CapEx as % of revenue |
| `WC_CHANGE_PCT` | 1% | NWC increase as % of revenue |
| `TAX_RATE` | 28% | Corporate tax rate |
| `HOLDING_YEARS` | 5 | Investment horizon |
| `SENIOR_DEBT` | €247.5M | Senior tranche (55% of EV @ 6%) |
| `SENIOR_AMORT_PCT` | 5%/yr | Mandatory annual principal repayment |
| `MEZZ_DEBT` | €67.5M | Mezzanine tranche (15% of EV @ 10% PIK) |
| `EQUITY` | €135M | Sponsor equity (30% of EV) |
| `EXIT_SCENARIOS` | 6×/7.5×/9× | Bear / Base / Bull exit multiples |

## How to Adapt to a Real Case

This model uses fictional data for **TechRetail SA**. Here's how to plug in a real deal:

### 1. Update Entry Assumptions
Edit the constants at the top of `lbo_model.py`:
```python
COMPANY      = "Your Target Name"
ENTRY_EV     = 600_000_000   # Actual negotiated EV
ENTRY_EBITDA = 80_000_000    # LTM or NTM EBITDA from data room
REVENUE_Y0   = 400_000_000   # Last fiscal year revenue
```

### 2. Calibrate Growth & Margins
Source your assumptions from:
- Management projections (data room)
- Comparable company CAGR (industry reports)
- Conservative "sponsor case" haircut (typically −1 to −2% vs mgmt)

```python
REVENUE_CAGR     = 0.06    # e.g. more conservative than mgmt's 9%
MARGIN_EXPANSION = 0.005   # e.g. +50bps/yr if operational improvements planned
```

### 3. Adjust Debt Structure
Match your actual financing package:
```python
SENIOR_DEBT      = 0.55 * ENTRY_EV   # Adjust leverage multiple
SENIOR_RATE      = 0.07              # Current market rate (SOFR + spread)
MEZZ_DEBT        = 0.10 * ENTRY_EV   # May be 0 if no mezz tranche
MEZZ_RATE        = 0.12              # PIK or cash-pay
EQUITY           = ENTRY_EV - SENIOR_DEBT - MEZZ_DEBT
```

### 4. Set Exit Scenarios
Use sector-specific EV/EBITDA comps for exit multiple assumptions:
```python
EXIT_SCENARIOS = {
    "Bear Case": 5.5,   # Sector compression / distressed market
    "Base Case": 7.0,   # In-line with entry / slight re-rating
    "Bull Case": 8.5,   # Strong growth + multiple expansion
}
```

### 5. Validate IRR vs Hurdle Rate
- Typical PE hurdle: **20%+ IRR**, **2.5× MOIC**
- If Base Case IRR < 15%, revisit entry price or structure

### 6. Add Real Taxes & Fees
For a full model also account for:
- Transaction fees (typically 2–3% of EV)
- Management fees (1–2% of equity/year)
- Exit fees and carry structure
- Tax shield on interest (already included via EBIT → net income bridge)

## Author

**Wilfried LAWSON HELLU** | Finance Analyst  
📧 wilfriedlawpro@gmail.com | 🔗 [LinkedIn](https://linkedin.com/in/wilfried-lawsonhellu) | 🐙 [GitHub](https://github.com/Wxlly00)

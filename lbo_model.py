"""Command-line entry point for the Northstar Components LBO model."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from model import DEFAULT_SCENARIOS, run_scenarios
from model.charts import generate_charts
from model.excel_export import export_workbook, validate_workbook
from model.sensitivity import default_sensitivities


def _format_eur(value: float) -> str:
    return f"€{value / 1e6:,.1f}M"


def _returns_table(results: dict) -> pd.DataFrame:
    rows = []
    for name, result in results.items():
        rows.append(
            {
                "Scenario": name,
                "Exit EBITDA": _format_eur(float(result.returns["Exit EBITDA"])),
                "Exit Equity": _format_eur(
                    float(result.returns["Sponsor Equity Value"])
                ),
                "Debt Paydown": _format_eur(
                    float(result.returns["Gross Debt Paydown"])
                ),
                "Net Leverage": f"{float(result.returns['Exit Net Debt / EBITDA']):.2f}x",
                "MOIC": f"{float(result.returns['MOIC']):.2f}x",
                "IRR": f"{float(result.returns['IRR']):.1%}",
            }
        )
    return pd.DataFrame(rows).set_index("Scenario")


def run(output_dir: str | Path = "outputs", assets_dir: str | Path = "assets") -> dict:
    """Run all cases and generate the Excel workbook and chart assets."""

    results = run_scenarios()
    sensitivities = default_sensitivities(results["Base"])
    output_path = Path(output_dir) / "LBO_Investment_Model.xlsx"
    workbook_path = export_workbook(
        results=results,
        scenarios=DEFAULT_SCENARIOS,
        sensitivities=sensitivities,
        output_path=output_path,
    )
    chart_paths = generate_charts(
        base_result=results["Base"],
        sensitivities=sensitivities,
        assets_dir=assets_dir,
    )
    workbook_validation = validate_workbook(workbook_path)
    return {
        "results": results,
        "sensitivities": sensitivities,
        "workbook_path": workbook_path,
        "chart_paths": chart_paths,
        "workbook_validation": workbook_validation,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the fictional Northstar Components LBO investment case."
    )
    parser.add_argument(
        "--output-dir",
        default="outputs",
        help="Directory for the Excel workbook (default: outputs).",
    )
    parser.add_argument(
        "--assets-dir",
        default="assets",
        help="Directory for generated charts (default: assets).",
    )
    args = parser.parse_args()

    artifacts = run(args.output_dir, args.assets_dir)
    results = artifacts["results"]
    base = results["Base"]
    print("\nLBO Investment Model — Northstar Components")
    print(f"Entry Enterprise Value: {_format_eur(base.entry.entry_enterprise_value)}")
    print(f"Sponsor Equity Invested: {_format_eur(float(base.returns['Entry Equity']))}")
    print("\nScenario Returns")
    print(_returns_table(results).to_string())
    print("\nModel Checks")
    print(base.checks[["Check", "Status"]].to_string(index=False))
    print(f"\nWorkbook: {artifacts['workbook_path']}")
    print(f"Charts: {len(artifacts['chart_paths'])} files in {args.assets_dir}")


if __name__ == "__main__":
    main()

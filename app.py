import io
from dataclasses import dataclass
from typing import Dict, List

import numpy as np
import pandas as pd
import streamlit as st

REQUIRED_COLUMNS = [
    "customer",
    "product",
    "geography",
    "base_annual_sales",
    "base_gross_margin_pct",
]

MONTHS = [
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
]


@dataclass
class PlanAssumptions:
    plan_year: int
    currency: str
    growth_pct: float
    price_increase_pct: float
    volume_growth_pct: float
    seasonality: Dict[str, float]


SAMPLE_DATA = pd.DataFrame(
    [
        ["Acme Retail", "Widget A", "North", 120_000, 32],
        ["Acme Retail", "Widget B", "North", 80_000, 28],
        ["Bravo Distributors", "Widget A", "West", 95_000, 30],
        ["Central Stores", "Widget C", "East", 140_000, 35],
        ["Delta Wholesale", "Widget B", "South", 110_000, 27],
    ],
    columns=REQUIRED_COLUMNS,
)


def validate_input(df: pd.DataFrame) -> List[str]:
    errors: List[str] = []
    missing_cols = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing_cols:
        errors.append(f"Missing required columns: {', '.join(missing_cols)}")

    if not missing_cols:
        for num_col in ["base_annual_sales", "base_gross_margin_pct"]:
            if not pd.api.types.is_numeric_dtype(df[num_col]):
                errors.append(f"Column '{num_col}' must be numeric")

        if (df["base_annual_sales"] < 0).any():
            errors.append("'base_annual_sales' cannot have negative values")

        if ((df["base_gross_margin_pct"] < 0) | (df["base_gross_margin_pct"] > 100)).any():
            errors.append("'base_gross_margin_pct' must be between 0 and 100")

    return errors


def normalize_seasonality(raw_weights: Dict[str, float]) -> Dict[str, float]:
    weights = np.array([max(0.0, raw_weights[m]) for m in MONTHS], dtype=float)
    if np.isclose(weights.sum(), 0):
        weights = np.array([1 / 12] * 12)
    else:
        weights = weights / weights.sum()
    return {m: float(w) for m, w in zip(MONTHS, weights)}


def build_plan(df: pd.DataFrame, assumptions: PlanAssumptions) -> pd.DataFrame:
    seasonality = assumptions.seasonality
    growth_factor = (1 + assumptions.growth_pct / 100) * (1 + assumptions.price_increase_pct / 100) * (
        1 + assumptions.volume_growth_pct / 100
    )

    rows = []
    for _, row in df.iterrows():
        planned_annual_sales = row["base_annual_sales"] * growth_factor
        for month in MONTHS:
            monthly_sales = planned_annual_sales * seasonality[month]
            margin_pct = row["base_gross_margin_pct"]
            gross_margin_value = monthly_sales * (margin_pct / 100)
            rows.append(
                {
                    "year": assumptions.plan_year,
                    "month": month,
                    "customer": row["customer"],
                    "product": row["product"],
                    "geography": row["geography"],
                    "planned_sales": round(monthly_sales, 2),
                    "gross_margin_pct": margin_pct,
                    "gross_margin_value": round(gross_margin_value, 2),
                }
            )

    return pd.DataFrame(rows)


def summarize(plan_df: pd.DataFrame, group_by: str) -> pd.DataFrame:
    return (
        plan_df.groupby(group_by, as_index=False)
        .agg(
            annual_sales=("planned_sales", "sum"),
            annual_gross_margin=("gross_margin_value", "sum"),
        )
        .sort_values("annual_sales", ascending=False)
    )


def to_excel_bytes(
    detail_df: pd.DataFrame,
    product_df: pd.DataFrame,
    geography_df: pd.DataFrame,
    customer_df: pd.DataFrame,
    assumptions: PlanAssumptions,
) -> bytes:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        detail_df.to_excel(writer, sheet_name="SalesPlan_Detail", index=False)
        product_df.to_excel(writer, sheet_name="Summary_Product", index=False)
        geography_df.to_excel(writer, sheet_name="Summary_Geography", index=False)
        customer_df.to_excel(writer, sheet_name="Summary_Customer", index=False)

        assumptions_df = pd.DataFrame(
            {
                "parameter": [
                    "plan_year",
                    "currency",
                    "growth_pct",
                    "price_increase_pct",
                    "volume_growth_pct",
                ],
                "value": [
                    assumptions.plan_year,
                    assumptions.currency,
                    assumptions.growth_pct,
                    assumptions.price_increase_pct,
                    assumptions.volume_growth_pct,
                ],
            }
        )
        assumptions_df.to_excel(writer, sheet_name="Assumptions", index=False)

    output.seek(0)
    return output.getvalue()


def main() -> None:
    st.set_page_config(page_title="AOP Sales Planner", layout="wide")
    st.title("Annual Operating Plan (AOP) Sales Planner")
    st.caption("Build a product-wise, geography-wise, and customer-wise annual sales plan and export it to Excel.")

    with st.sidebar:
        st.header("Plan assumptions")
        plan_year = st.number_input("Plan year", min_value=2020, max_value=2100, value=2026, step=1)
        currency = st.text_input("Currency", value="USD")
        growth_pct = st.number_input("General growth (%)", min_value=-100.0, max_value=500.0, value=8.0, step=0.5)
        price_increase_pct = st.number_input(
            "Price increase (%)", min_value=-100.0, max_value=500.0, value=2.0, step=0.5
        )
        volume_growth_pct = st.number_input(
            "Volume growth (%)", min_value=-100.0, max_value=500.0, value=4.0, step=0.5
        )

        st.subheader("Seasonality weights")
        st.caption("Set monthly demand weights. They are normalized automatically.")
        raw_weights = {m: st.number_input(m, min_value=0.0, value=1.0, step=0.1) for m in MONTHS}

    seasonality = normalize_seasonality(raw_weights)
    assumptions = PlanAssumptions(
        plan_year=int(plan_year),
        currency=currency.strip() or "USD",
        growth_pct=float(growth_pct),
        price_increase_pct=float(price_increase_pct),
        volume_growth_pct=float(volume_growth_pct),
        seasonality=seasonality,
    )

    st.subheader("Base sales input")
    uploaded = st.file_uploader("Upload CSV input", type=["csv"])

    if uploaded is not None:
        input_df = pd.read_csv(uploaded)
    else:
        st.info("No CSV uploaded. Using sample dataset.")
        input_df = SAMPLE_DATA.copy()

    st.dataframe(input_df, use_container_width=True)

    errors = validate_input(input_df)
    if errors:
        for err in errors:
            st.error(err)
        st.stop()

    detail_df = build_plan(input_df, assumptions)
    product_df = summarize(detail_df, "product")
    geography_df = summarize(detail_df, "geography")
    customer_df = summarize(detail_df, "customer")

    col1, col2, col3 = st.columns(3)
    col1.metric(f"Total plan sales ({assumptions.currency})", f"{detail_df['planned_sales'].sum():,.0f}")
    col2.metric(f"Total gross margin ({assumptions.currency})", f"{detail_df['gross_margin_value'].sum():,.0f}")
    col3.metric("Planned combinations", f"{input_df.shape[0]:,}")

    st.subheader("Product summary")
    st.dataframe(product_df, use_container_width=True)

    st.subheader("Geography summary")
    st.dataframe(geography_df, use_container_width=True)

    st.subheader("Customer summary")
    st.dataframe(customer_df, use_container_width=True)

    excel_data = to_excel_bytes(detail_df, product_df, geography_df, customer_df, assumptions)
    st.download_button(
        label="Download AOP Excel workbook",
        data=excel_data,
        file_name=f"AOP_Sales_Plan_{assumptions.plan_year}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


if __name__ == "__main__":
    main()

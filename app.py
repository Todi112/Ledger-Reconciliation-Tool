import io
from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import streamlit as st

REQUIRED_COLUMNS = [
    "customer",
    "product",
    "geography",
    "industry",
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

INDUSTRY_BENCHMARKS = {
    "FMCG": {
        "growth_hint_pct": 6.0,
        "price_hint_pct": 2.0,
        "margin_hint_pct": 24.0,
        "note": "Push distribution expansion and promo ROI tracking.",
    },
    "Pharma": {
        "growth_hint_pct": 8.0,
        "price_hint_pct": 3.0,
        "margin_hint_pct": 33.0,
        "note": "Focus on key account coverage and channel fill-rates.",
    },
    "Industrial": {
        "growth_hint_pct": 5.0,
        "price_hint_pct": 2.5,
        "margin_hint_pct": 28.0,
        "note": "Use deal-level pipeline confidence and contract renewal plans.",
    },
    "Retail": {
        "growth_hint_pct": 7.0,
        "price_hint_pct": 1.5,
        "margin_hint_pct": 22.0,
        "note": "Watch assortment productivity and regional sell-through.",
    },
    "Technology": {
        "growth_hint_pct": 10.0,
        "price_hint_pct": 1.0,
        "margin_hint_pct": 36.0,
        "note": "Prioritize upsell/cross-sell motions in existing customers.",
    },
}


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
        ["Acme Retail", "Widget A", "North", "Retail", 120_000, 32],
        ["Acme Retail", "Widget B", "North", "Retail", 80_000, 28],
        ["Bravo Distributors", "Widget A", "West", "FMCG", 95_000, 30],
        ["Central Stores", "Widget C", "East", "Industrial", 140_000, 35],
        ["Delta Wholesale", "Widget B", "South", "Pharma", 110_000, 27],
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

        for text_col in ["customer", "product", "geography", "industry"]:
            if df[text_col].astype(str).str.strip().eq("").any():
                errors.append(f"Column '{text_col}' cannot be blank")

    return errors


def normalize_seasonality(raw_weights: Dict[str, float]) -> Dict[str, float]:
    weights = np.array([max(0.0, raw_weights[m]) for m in MONTHS], dtype=float)
    if np.isclose(weights.sum(), 0):
        weights = np.array([1 / 12] * 12)
    else:
        weights = weights / weights.sum()
    return {m: float(w) for m, w in zip(MONTHS, weights)}


def normalize_team_split(team_split: pd.DataFrame) -> pd.DataFrame:
    clean = team_split.copy()
    clean["allocation_pct"] = clean["allocation_pct"].clip(lower=0)
    total = clean["allocation_pct"].sum()
    if np.isclose(total, 0):
        clean["allocation_pct"] = 100 / len(clean)
    else:
        clean["allocation_pct"] = (clean["allocation_pct"] / total) * 100
    return clean


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
                    "industry": row["industry"],
                    "planned_sales": round(monthly_sales, 2),
                    "gross_margin_pct": margin_pct,
                    "gross_margin_value": round(gross_margin_value, 2),
                }
            )

    return pd.DataFrame(rows)


def apply_sales_team_split(detail_df: pd.DataFrame, team_split: pd.DataFrame) -> pd.DataFrame:
    normalized_split = normalize_team_split(team_split)
    detail_df = detail_df.assign(_key=1)
    normalized_split = normalized_split.assign(_key=1)

    team_df = detail_df.merge(normalized_split, on="_key", how="inner").drop(columns=["_key"])
    team_df["planned_sales"] = (team_df["planned_sales"] * team_df["allocation_pct"] / 100).round(2)
    team_df["gross_margin_value"] = (team_df["gross_margin_value"] * team_df["allocation_pct"] / 100).round(2)
    return team_df


def summarize(plan_df: pd.DataFrame, group_by: str) -> pd.DataFrame:
    return (
        plan_df.groupby(group_by, as_index=False)
        .agg(
            annual_sales=("planned_sales", "sum"),
            annual_gross_margin=("gross_margin_value", "sum"),
        )
        .sort_values("annual_sales", ascending=False)
    )


def get_industry_insights(input_df: pd.DataFrame, assumptions: PlanAssumptions) -> pd.DataFrame:
    insights = []
    for industry in sorted(input_df["industry"].dropna().astype(str).str.strip().unique()):
        benchmark = INDUSTRY_BENCHMARKS.get(industry)
        if benchmark:
            benchmark_growth = benchmark["growth_hint_pct"]
            gap = assumptions.growth_pct - benchmark_growth
            advice = (
                "Planned growth is above benchmark; validate pipeline coverage and capacity."
                if gap > 1
                else "Planned growth is below benchmark; consider additional demand generation."
                if gap < -1
                else "Planned growth is aligned with benchmark."
            )
            insights.append(
                {
                    "industry": industry,
                    "benchmark_growth_pct": benchmark_growth,
                    "benchmark_margin_pct": benchmark["margin_hint_pct"],
                    "planning_note": f"{advice} {benchmark['note']}",
                }
            )
        else:
            insights.append(
                {
                    "industry": industry,
                    "benchmark_growth_pct": np.nan,
                    "benchmark_margin_pct": np.nan,
                    "planning_note": "No benchmark configured. Use recent trend + sales team judgment.",
                }
            )

    return pd.DataFrame(insights)


def to_excel_bytes(
    detail_df: pd.DataFrame,
    team_df: pd.DataFrame,
    product_df: pd.DataFrame,
    geography_df: pd.DataFrame,
    customer_df: pd.DataFrame,
    industry_df: pd.DataFrame,
    team_summary_df: pd.DataFrame,
    insights_df: pd.DataFrame,
    assumptions: PlanAssumptions,
) -> bytes:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        detail_df.to_excel(writer, sheet_name="SalesPlan_Detail", index=False)
        team_df.to_excel(writer, sheet_name="SalesPlan_ByTeam", index=False)
        product_df.to_excel(writer, sheet_name="Summary_Product", index=False)
        geography_df.to_excel(writer, sheet_name="Summary_Geography", index=False)
        customer_df.to_excel(writer, sheet_name="Summary_Customer", index=False)
        industry_df.to_excel(writer, sheet_name="Summary_Industry", index=False)
        team_summary_df.to_excel(writer, sheet_name="Summary_SalesTeam", index=False)
        insights_df.to_excel(writer, sheet_name="Industry_Insights", index=False)

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


def capture_team_split() -> pd.DataFrame:
    st.subheader("Sales team split")
    st.caption("Allocate the total plan across sales teams. Percentages are normalized automatically.")

    team_count = st.number_input("Number of sales teams", min_value=1, max_value=10, value=3, step=1)
    default_teams = ["National Key Accounts", "Regional Field", "Inside Sales", "Distributor Team"]

    rows: List[Tuple[str, float]] = []
    for i in range(int(team_count)):
        c1, c2 = st.columns([3, 1])
        team_name = c1.text_input(f"Team {i + 1} name", value=default_teams[i] if i < len(default_teams) else f"Team {i + 1}")
        team_alloc = c2.number_input(f"Team {i + 1} %", min_value=0.0, max_value=100.0, value=round(100 / team_count, 2), step=0.5)
        rows.append((team_name.strip() or f"Team {i + 1}", float(team_alloc)))

    split_df = pd.DataFrame(rows, columns=["sales_team", "allocation_pct"])
    split_df = normalize_team_split(split_df)
    st.dataframe(split_df, use_container_width=True)
    return split_df


def main() -> None:
    st.set_page_config(page_title="AOP Sales Planner", layout="wide")
    st.title("Annual Operating Plan (AOP) Sales Planner")
    st.caption(
        "Build product-wise, geography-wise, customer-wise and sales-team-wise plans with industry insights, then export to Excel."
    )

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

    team_split_df = capture_team_split()

    detail_df = build_plan(input_df, assumptions)
    team_df = apply_sales_team_split(detail_df, team_split_df)

    product_df = summarize(detail_df, "product")
    geography_df = summarize(detail_df, "geography")
    customer_df = summarize(detail_df, "customer")
    industry_df = summarize(detail_df, "industry")
    team_summary_df = summarize(team_df, "sales_team")
    insights_df = get_industry_insights(input_df, assumptions)

    col1, col2, col3 = st.columns(3)
    col1.metric(f"Total plan sales ({assumptions.currency})", f"{detail_df['planned_sales'].sum():,.0f}")
    col2.metric(f"Total gross margin ({assumptions.currency})", f"{detail_df['gross_margin_value'].sum():,.0f}")
    col3.metric("Planned combinations", f"{input_df.shape[0]:,}")

    st.subheader("Industry insights for plan tailoring")
    st.dataframe(insights_df, use_container_width=True)

    st.subheader("Sales team annual split")
    st.dataframe(team_summary_df, use_container_width=True)

    st.subheader("Product summary")
    st.dataframe(product_df, use_container_width=True)

    st.subheader("Geography summary")
    st.dataframe(geography_df, use_container_width=True)

    st.subheader("Customer summary")
    st.dataframe(customer_df, use_container_width=True)

    st.subheader("Industry summary")
    st.dataframe(industry_df, use_container_width=True)

    excel_data = to_excel_bytes(
        detail_df,
        team_df,
        product_df,
        geography_df,
        customer_df,
        industry_df,
        team_summary_df,
        insights_df,
        assumptions,
    )
    st.download_button(
        label="Download AOP Excel workbook",
        data=excel_data,
        file_name=f"AOP_Sales_Plan_{assumptions.plan_year}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


if __name__ == "__main__":
    main()

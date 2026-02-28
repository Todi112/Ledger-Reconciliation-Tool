# Annual Operating Plan (AOP) Sales Planner

This repository contains a lightweight app to build an **Excel-based Annual Operating Plan (AOP)** sales plan across:

- Product
- Geography
- Customer
- Industry
- Sales team

## What the app does

- Captures plan assumptions (year, currency, growth rates, seasonality).
- Lets you upload a base sales dataset (or use sample data).
- Uses **industry benchmark insights** to suggest planning actions by industry.
- Builds a monthly AOP plan with baseline + growth adjustment.
- Splits plan values between multiple sales teams based on allocation percentages.
- Exports a multi-sheet Excel workbook with detailed and summary tabs.

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Input template

Upload a CSV with the following columns:

- `customer`
- `product`
- `geography`
- `industry`
- `base_annual_sales`
- `base_gross_margin_pct`

Example:

```csv
customer,product,geography,industry,base_annual_sales,base_gross_margin_pct
Acme Retail,Widget A,North,Retail,120000,32
Acme Retail,Widget B,North,Retail,80000,28
Bravo Distributors,Widget A,West,FMCG,95000,30
```

## Output workbook

The exported workbook includes:

- `SalesPlan_Detail`: monthly plan rows by customer-product-geography-industry.
- `SalesPlan_ByTeam`: monthly plan with sales team allocation applied.
- `Summary_Product`: annual totals by product.
- `Summary_Geography`: annual totals by geography.
- `Summary_Customer`: annual totals by customer.
- `Summary_Industry`: annual totals by industry.
- `Summary_SalesTeam`: annual totals by sales team.
- `Industry_Insights`: benchmark-based guidance to tailor plan assumptions by industry.
- `Assumptions`: key AOP input assumptions used for generation.

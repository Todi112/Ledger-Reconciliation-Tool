# Annual Operating Plan (AOP) Sales Planner

This repository contains a lightweight app to build an **Excel-based Annual Operating Plan (AOP)** sales plan across:

- Product
- Geography
- Customer

## What the app does

- Captures plan assumptions (year, currency, growth rates, optional seasonality).
- Lets you upload a base sales dataset (or use sample data).
- Generates a monthly AOP plan with baseline + growth adjustment.
- Exports a multi-sheet Excel workbook with:
  - Detailed monthly plan
  - Product-wise summary
  - Geography-wise summary
  - Customer-wise summary

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
- `base_annual_sales`
- `base_gross_margin_pct`

Example:

```csv
customer,product,geography,base_annual_sales,base_gross_margin_pct
Acme Retail,Widget A,North,120000,32
Acme Retail,Widget B,North,80000,28
Bravo Distributors,Widget A,West,95000,30
```

## Output workbook

The exported workbook includes:

- `SalesPlan_Detail`: monthly plan rows for every customer-product-geography combination.
- `Summary_Product`: annual totals by product.
- `Summary_Geography`: annual totals by geography.
- `Summary_Customer`: annual totals by customer.
- `Assumptions`: key AOP input assumptions used for generation.

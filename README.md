# Financial Data Analysis Pipeline

A Python pipeline that extracts financial metrics from **PDF, Excel, and CSV financial files**, cleans and stores the data in **SQLite**, calculates financial KPIs with **pandas and SQL**, and exports **Power BI-ready reports and charts**.

---

## 1. Project Overview

This project takes messy financial files from an input folder and turns them into a clean dataset for analysis.

```text
PDF / Excel / CSV files
        ↓
Python extraction and cleaning
        ↓
SQLite database
        ↓
KPI calculations with pandas and SQL
        ↓
CSV outputs and charts
        ↓
Power BI dashboard
```

The pipeline:

1. Reads PDF, Excel, or CSV financial files
2. Extracts key financial values
3. Organizes the data into a structured table
4. Stores the cleaned data in a SQLite database
5. Calculates financial KPIs using pandas and SQL
6. Exports CSV files for Power BI
7. Creates basic charts for quick checking

---

## 2. Input Files and Formatting

### 2.1 Supported Input Files

Place all files inside the `input_files/` folder.

| File Type | Extension | How the Pipeline Reads It |
|---|---|---|
| PDF | `.pdf` | Extracts text and searches for financial labels |
| Excel | `.xlsx`, `.xls` | Reads all sheets in the workbook and searches for financial labels |
| CSV | `.csv` | Reads structured columns directly |

Note: For best results, each PDF or Excel file should represent one company/entity and one reporting period. Excel workbooks can contain multiple sheets, but those sheets should belong to the same company and period. If one workbook contains different companies or periods across sheets, the parser may need additional logic to separate them correctly.

---

### 2.2 File Naming Format

Use this format when possible:

```text
company_year_month.filetype
```

Examples:

```text
company_a_2024_01.csv
company_b_2024_02.xlsx
company_c_april_2024.pdf
```

The pipeline uses file names to identify company, year, month, period, source file, and source type.

Example:

```text
company_a_2024_01.csv
```

is read as:

| Field | Value |
|---|---|
| company | `company_a` |
| year | `2024` |
| month | `01` |
| period | `2024-01` |
| source_type | `csv` |

---

### 2.3 CSV Input Format

CSV files should already be organized in columns.

Recommended columns:

```text
company,year,month,service_revenue,sales_revenue,net_income,operating_expenses,total_assets,current_assets,liabilities,retained_earnings
```

Example:

```csv
company,year,month,service_revenue,sales_revenue,net_income,operating_expenses,total_assets,current_assets,liabilities,retained_earnings
company_a,2024,01,500000,300000,120000,450000,900000,300000,200000,150000
company_b,2024,01,400000,300000,80000,500000,750000,250000,180000,100000
company_c,2024,01,600000,200000,150000,420000,1000000,350000,220000,180000
```

The pipeline uses file names to identify company, year, month, period, and source type for PDF, Excel, and CSV files. If a CSV already includes these columns, the file values are used; otherwise, missing metadata is filled from the file name.

---

### 2.4 PDF and Excel Input Format

PDF and Excel files should include recognizable financial labels, such as:

```text
Service revenue
Sales revenue
Net income
Total operating expenses
Total assets
Total current assets
Total current liabilities
Retained earnings
```

The parser searches for these labels and extracts the matching values.

Note: The parser currently uses regex patterns for common financial labels. If a PDF or Excel file uses different wording, abbreviations, or unusual formatting, the patterns in `financial_pipeline.py` may need to be updated.

---

## 3. Setup, Run, and Outputs

### 3.1 Setup Instructions

Install the required packages:

```bash
pip install pandas matplotlib pdfplumber openpyxl
```

If `pip` does not work, try:

```bash
python3 -m pip install pandas matplotlib pdfplumber openpyxl
```

---

### 3.2 How to Run

1. Add your files to the `input_files/` folder.

Example:

```text
input_files/
├── company_a_2024_01.csv
├── company_b_2024_01.xlsx
└── company_c_2024_01.pdf
```

2. Run the pipeline:

```bash
python3 financial_pipeline.py
```

If your computer uses `python` instead of `python3`, run:

```bash
python financial_pipeline.py
```

---

### 3.3 Output Files

The pipeline creates an `output/` folder.

Main outputs:

```text
output/
├── financial_data_with_kpis.csv
├── financial_analysis.db
├── all_records.csv
├── sql_calculated_kpis.csv
├── highest_profit_margin.csv
├── strongest_liquidity.csv
├── largest_total_assets.csv
├── revenue_by_company.csv
├── revenue_by_period.csv
├── average_profit_margin_by_company.csv
├── total_revenue_by_company.png
├── profit_margin_by_company.png
└── total_revenue_by_period.png
```

---

## 4. Analytics and Reporting

### 4.1 KPIs Calculated

The pipeline calculates the following financial KPIs:

| KPI | Formula |
|---|---|
| Total revenue | `service_revenue + sales_revenue` |
| Profit margin | `net_income / total_revenue` |
| Operating expense ratio | `operating_expenses / total_revenue` |
| Current ratio | `current_assets / liabilities` |
| Asset-to-liability ratio | `total_assets / liabilities` |

---

### 4.2 SQL Analysis

After the financial data is extracted and cleaned with Python/pandas, the pipeline saves the structured dataset into a SQLite database:

```text
output/financial_analysis.db
```

The SQLite table includes the cleaned financial records and the main KPI columns calculated with pandas, such as:

```text
total_revenue
profit_margin
operating_expense_ratio
current_ratio
asset_to_liability_ratio
```

Once the data is stored in SQLite, the script automatically runs SQL queries to retrieve, filter, rank, compare, and create database-based analysis outputs.

SQL query outputs are exported as CSV files, including:

```text
all_records.csv
sql_calculated_kpis.csv
highest_profit_margin.csv
strongest_liquidity.csv
largest_total_assets.csv
revenue_by_company.csv
revenue_by_period.csv
average_profit_margin_by_company.csv
```

The `sql_calculated_kpis` query also calculates KPI values directly from the raw financial columns in SQLite. This helps check the pandas-calculated KPI results and shows how the same metrics can be calculated directly with SQL.

---

### 4.3 Power BI Reporting

The main file to import into Power BI is:

```text
output/financial_data_with_kpis.csv
```

This file can be used to create dashboard visuals.

Suggested dashboard elements:

| Dashboard Element | Fields |
|---|---|
| KPI cards | `total_revenue`, `net_income`, `profit_margin`, `current_ratio` |
| Revenue chart | `company`, `total_revenue` |
| Profitability chart | `company`, `profit_margin` |
| Time trend | `period`, `total_revenue` |
| Slicers | `company`, `year`, `month`, `source_type` |

---
### 5. Current Status & Future Improvements

The main pipeline code is included and runs with compatible financial PDF, CSV, or Excel inputs. Example input files and sample output reports are not included yet, but will be added as demo materials.

The repository also includes a complementary LLM API-based prototype for summarizing extracted financial data and generating plain-language explanations.

Possible future upgrades:

- Add more flexible financial label matching with document parsing tools such as LlamaParse
- Add support for scanned PDFs or OCR
- Add AI-generated summaries from already-computed KPI results to the main pipeline code
- Add a Streamlit app for uploading files...

---

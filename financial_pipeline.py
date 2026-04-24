import re
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional

import pdfplumber
import pandas as pd
import matplotlib.pyplot as plt


# =========================
# Configuration
# =========================
INPUT_DIR = "input_files"          # Put PDF, Excel, or CSV files here
OUTPUT_DIR = "output"              # CSVs, plots, and database go here
DB_NAME = "financial_analysis.db"  # SQLite database file name


# =========================
# Metadata Extraction
# =========================
def extract_metadata_from_filename(file_path: Path) -> Dict[str, Optional[str]]:
    """
    Extract company/entity, year, month, period, source file, and source type
    from the file name.

    Recommended file names:
        company_a_2024_04.csv
        company_a_april_2024.xlsx
        company_b_2025_01.pdf

    period will be:
        2024-04 if year and month exist
        2024 if only year exists
        None if no year exists
    """
    month_map = {
        "jan": "01", "january": "01",
        "feb": "02", "february": "02",
        "mar": "03", "march": "03",
        "apr": "04", "april": "04",
        "may": "05",
        "jun": "06", "june": "06",
        "jul": "07", "july": "07",
        "aug": "08", "august": "08",
        "sep": "09", "sept": "09", "september": "09",
        "oct": "10", "october": "10",
        "nov": "11", "november": "11",
        "dec": "12", "december": "12",
    }

    stem = file_path.stem.lower()
    source_type = file_path.suffix.replace(".", "").lower()

    # Split on underscores, hyphens, and spaces
    parts = re.split(r"[_\-\s]+", stem)

    year = None
    month = None

    # Find year and month
    for part in parts:
        if re.fullmatch(r"20\d{2}|19\d{2}", part):
            year = part

        elif re.fullmatch(r"0?[1-9]|1[0-2]", part):
            # Numeric month, like 4 or 04
            month = part.zfill(2)

        elif part in month_map:
            # Month name, like april
            month = month_map[part]

    # Build company name by removing year/month parts
    company_parts = []
    for part in parts:
        is_year = re.fullmatch(r"20\d{2}|19\d{2}", part)
        is_numeric_month = re.fullmatch(r"0?[1-9]|1[0-2]", part)
        is_month_name = part in month_map

        if not is_year and not is_numeric_month and not is_month_name:
            company_parts.append(part)

    company = "_".join(company_parts) if company_parts else stem

    if year and month:
        period = f"{year}-{month}"
    elif year:
        period = year
    else:
        period = None

    return {
        "company": company,
        "year": year,
        "month": month,
        "period": period,
        "source_file": file_path.name,
        "source_type": source_type,
    }


# =========================
# PDF Extraction
# =========================
def extract_text_from_pdf(pdf_path: Path) -> str:
    """
    Extract all text from a PDF file.
    """
    try:
        text_parts: List[str] = []

        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)

        return "\n".join(text_parts)

    except Exception as e:
        raise RuntimeError(f"Failed to extract text from PDF {pdf_path.name}: {e}")


# =========================
# Excel Extraction
# =========================
def extract_text_from_excel(excel_path: Path) -> str:
    """
    Extract text from all sheets in an Excel file.
    """
    try:
        sheets = pd.read_excel(excel_path, sheet_name=None)
        text_parts: List[str] = []

        for sheet_name, sheet_df in sheets.items():
            text_parts.append(f"\n--- Sheet: {sheet_name} ---\n")
            text_parts.append(sheet_df.to_string(index=False))

        return "\n".join(text_parts)

    except Exception as e:
        raise RuntimeError(f"Failed to extract text from Excel {excel_path.name}: {e}")


# =========================
# Data Parsing
# =========================
def parse_money(text: str, pattern: str) -> Optional[float]:
    """
    Extract a money value using a regex pattern.
    Returns None if the value is not found.
    """
    match = re.search(pattern, text, flags=re.IGNORECASE)

    if not match:
        return None

    raw_value = match.group(1).replace(",", "").replace("$", "").strip()

    try:
        return float(raw_value)
    except ValueError:
        return None


def extract_financial_data(text: str, source_file: str) -> Dict[str, Optional[float]]:
    """
    Extract selected financial values from PDF/Excel text using regex patterns.
    """
    patterns = {
        "service_revenue": r"Service\s+revenue\s*\$?([\d,]+(?:\.\d{2})?)",
        "sales_revenue": r"Sales\s+revenue\s*\$?([\d,]+(?:\.\d{2})?)",
        "net_income": r"Net\s+income\s*\$?([\d,]+(?:\.\d{2})?)",
        "operating_expenses": r"Total\s+operating\s+expenses\s*\$?([\d,]+(?:\.\d{2})?)",
        "total_assets": r"Total\s+assets\s*\$?([\d,]+(?:\.\d{2})?)",
        "current_assets": r"Total\s+current\s+assets\s*\$?([\d,]+(?:\.\d{2})?)",
        "liabilities": r"Total\s+current\s+liabilities\s*\$?([\d,]+(?:\.\d{2})?)",
        "retained_earnings": r"Retained\s+earnings\s*\$?([\d,]+(?:\.\d{2})?)",
    }

    record = {"source_file": source_file}

    for field, pattern in patterns.items():
        record[field] = parse_money(text, pattern)

    return record


# =========================
# CSV Cleaning
# =========================
def clean_csv_dataframe(csv_df: pd.DataFrame, source_file: str) -> pd.DataFrame:
    """
    Clean CSV data so it matches the same structure as extracted PDF/Excel data.
    """
    df = csv_df.copy()

    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(" ", "_")
        .str.replace("-", "_")
    )

    required_columns = [
        "company",
        "year",
        "month",
        "period",
        "source_file",
        "source_type",
        "service_revenue",
        "sales_revenue",
        "net_income",
        "operating_expenses",
        "total_assets",
        "current_assets",
        "liabilities",
        "retained_earnings",
    ]

    for col in required_columns:
        if col not in df.columns:
            df[col] = None

    money_columns = [
        "service_revenue",
        "sales_revenue",
        "net_income",
        "operating_expenses",
        "total_assets",
        "current_assets",
        "liabilities",
        "retained_earnings",
    ]

    for col in money_columns:
        df[col] = (
            df[col]
            .astype(str)
            .str.replace("$", "", regex=False)
            .str.replace(",", "", regex=False)
            .str.strip()
        )
        df[col] = pd.to_numeric(df[col], errors="coerce")

    return df[required_columns]


# =========================
# KPI Computation with Pandas
# =========================
def compute_kpis_with_pandas(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute financial KPIs using pandas.
    """
    df = df.copy()

    money_columns = [
        "service_revenue",
        "sales_revenue",
        "net_income",
        "operating_expenses",
        "total_assets",
        "current_assets",
        "liabilities",
        "retained_earnings",
    ]

    for col in money_columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["total_revenue"] = df[["service_revenue", "sales_revenue"]].sum(axis=1, skipna=True)

    df["profit_margin"] = df.apply(
        lambda row: row["net_income"] / row["total_revenue"]
        if pd.notna(row["net_income"])
        and pd.notna(row["total_revenue"])
        and row["total_revenue"] != 0
        else None,
        axis=1,
    )

    df["operating_expense_ratio"] = df.apply(
        lambda row: row["operating_expenses"] / row["total_revenue"]
        if pd.notna(row["operating_expenses"])
        and pd.notna(row["total_revenue"])
        and row["total_revenue"] != 0
        else None,
        axis=1,
    )

    df["current_ratio"] = df.apply(
        lambda row: row["current_assets"] / row["liabilities"]
        if pd.notna(row["current_assets"])
        and pd.notna(row["liabilities"])
        and row["liabilities"] != 0
        else None,
        axis=1,
    )

    df["asset_to_liability_ratio"] = df.apply(
        lambda row: row["total_assets"] / row["liabilities"]
        if pd.notna(row["total_assets"])
        and pd.notna(row["liabilities"])
        and row["liabilities"] != 0
        else None,
        axis=1,
    )

    return df


# =========================
# Database
# =========================
def initialize_database(db_path: Path) -> None:
    """
    Create the SQLite table if it does not exist.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS financial_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company TEXT,
            year TEXT,
            month TEXT,
            period TEXT,
            source_file TEXT,
            source_type TEXT,
            service_revenue REAL,
            sales_revenue REAL,
            net_income REAL,
            operating_expenses REAL,
            total_assets REAL,
            current_assets REAL,
            liabilities REAL,
            retained_earnings REAL,
            total_revenue REAL,
            profit_margin REAL,
            operating_expense_ratio REAL,
            current_ratio REAL,
            asset_to_liability_ratio REAL
        )
        """
    )

    conn.commit()
    conn.close()


def save_to_database(df: pd.DataFrame, db_path: Path) -> None:
    """
    Save cleaned financial data into SQLite.
    Clears old records before inserting the fresh run.
    """
    conn = sqlite3.connect(db_path)

    conn.execute("DELETE FROM financial_data")
    conn.commit()

    df.to_sql("financial_data", conn, if_exists="append", index=False)

    conn.close()


# =========================
# SQL Queries
# =========================
def run_sql_queries(db_path: Path) -> Dict[str, pd.DataFrame]:
    """
    Run SQL queries for analysis.
    Includes SQL-calculated KPIs.
    """
    conn = sqlite3.connect(db_path)

    queries = {
        "all_records": """
            SELECT
                company,
                year,
                month,
                period,
                source_file,
                source_type,
                service_revenue,
                sales_revenue,
                total_revenue,
                net_income,
                operating_expenses,
                total_assets,
                current_assets,
                liabilities,
                retained_earnings,
                profit_margin,
                operating_expense_ratio,
                current_ratio,
                asset_to_liability_ratio
            FROM financial_data
            ORDER BY company, period, source_file;
        """,

        "sql_calculated_kpis": """
            SELECT
                company,
                year,
                month,
                period,
                source_file,
                source_type,
                service_revenue,
                sales_revenue,
                net_income,
                operating_expenses,
                total_assets,
                current_assets,
                liabilities,
                retained_earnings,

                COALESCE(service_revenue, 0) + COALESCE(sales_revenue, 0)
                    AS sql_total_revenue,

                ROUND(
                    net_income * 1.0 /
                    NULLIF(COALESCE(service_revenue, 0) + COALESCE(sales_revenue, 0), 0),
                    4
                ) AS sql_profit_margin,

                ROUND(
                    operating_expenses * 1.0 /
                    NULLIF(COALESCE(service_revenue, 0) + COALESCE(sales_revenue, 0), 0),
                    4
                ) AS sql_operating_expense_ratio,

                ROUND(
                    current_assets * 1.0 / NULLIF(liabilities, 0),
                    4
                ) AS sql_current_ratio,

                ROUND(
                    total_assets * 1.0 / NULLIF(liabilities, 0),
                    4
                ) AS sql_asset_to_liability_ratio

            FROM financial_data
            ORDER BY company, period, source_file;
        """,

        "highest_profit_margin": """
            SELECT
                company,
                period,
                source_file,
                profit_margin
            FROM financial_data
            WHERE profit_margin IS NOT NULL
            ORDER BY profit_margin DESC;
        """,

        "strongest_liquidity": """
            SELECT
                company,
                period,
                source_file,
                current_ratio
            FROM financial_data
            WHERE current_ratio IS NOT NULL
            ORDER BY current_ratio DESC;
        """,

        "largest_total_assets": """
            SELECT
                company,
                period,
                source_file,
                total_assets
            FROM financial_data
            WHERE total_assets IS NOT NULL
            ORDER BY total_assets DESC;
        """,

        "revenue_by_company": """
            SELECT
                company,
                SUM(total_revenue) AS total_revenue
            FROM financial_data
            GROUP BY company
            ORDER BY total_revenue DESC;
        """,

        "revenue_by_period": """
            SELECT
                period,
                SUM(total_revenue) AS total_revenue
            FROM financial_data
            WHERE period IS NOT NULL
            GROUP BY period
            ORDER BY period;
        """,

        "average_profit_margin_by_company": """
            SELECT
                company,
                ROUND(AVG(profit_margin), 4) AS average_profit_margin
            FROM financial_data
            WHERE profit_margin IS NOT NULL
            GROUP BY company
            ORDER BY average_profit_margin DESC;
        """
    }

    results = {}

    for name, query in queries.items():
        results[name] = pd.read_sql_query(query, conn)

    conn.close()
    return results


# =========================
# Reporting Outputs
# =========================
def save_csv_outputs(
    df: pd.DataFrame,
    query_results: Dict[str, pd.DataFrame],
    output_dir: Path
) -> None:
    """
    Save main dataset and SQL query outputs as CSV files.

    financial_data_with_kpis.csv is the main file to import into Power BI.
    """
    df.to_csv(output_dir / "financial_data_with_kpis.csv", index=False)

    for name, result_df in query_results.items():
        result_df.to_csv(output_dir / f"{name}.csv", index=False)


def plot_total_revenue_by_company(df: pd.DataFrame, output_dir: Path) -> None:
    """
    Create a bar chart of total revenue by company.
    """
    plot_df = (
        df.groupby("company", as_index=False)["total_revenue"]
        .sum()
        .dropna()
    )

    if plot_df.empty:
        print("Skipping company revenue plot: no revenue data available.")
        return

    plt.figure(figsize=(10, 6))
    bars = plt.bar(plot_df["company"], plot_df["total_revenue"])

    for bar in bars:
        y = bar.get_height()
        plt.text(
            bar.get_x() + bar.get_width() / 2,
            y,
            f"{y:,.0f}",
            ha="center",
            va="bottom",
        )

    plt.title("Total Revenue by Company")
    plt.ylabel("Revenue")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(output_dir / "total_revenue_by_company.png")
    plt.close()


def plot_profit_margin_by_company(df: pd.DataFrame, output_dir: Path) -> None:
    """
    Create a bar chart of average profit margin by company.
    """
    plot_df = (
        df.groupby("company", as_index=False)["profit_margin"]
        .mean()
        .dropna()
    )

    if plot_df.empty:
        print("Skipping company profit margin plot: no profit margin data available.")
        return

    plt.figure(figsize=(10, 6))
    bars = plt.bar(plot_df["company"], plot_df["profit_margin"])

    for bar in bars:
        y = bar.get_height()
        plt.text(
            bar.get_x() + bar.get_width() / 2,
            y,
            f"{y:.2%}",
            ha="center",
            va="bottom",
        )

    plt.title("Average Profit Margin by Company")
    plt.ylabel("Profit Margin")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(output_dir / "profit_margin_by_company.png")
    plt.close()


def plot_total_revenue_by_period(df: pd.DataFrame, output_dir: Path) -> None:
    """
    Create a bar chart of total revenue by period.
    """
    plot_df = (
        df.dropna(subset=["period"])
        .groupby("period", as_index=False)["total_revenue"]
        .sum()
    )

    if plot_df.empty:
        print("Skipping period revenue plot: no period data available.")
        return

    plt.figure(figsize=(10, 6))
    bars = plt.bar(plot_df["period"], plot_df["total_revenue"])

    for bar in bars:
        y = bar.get_height()
        plt.text(
            bar.get_x() + bar.get_width() / 2,
            y,
            f"{y:,.0f}",
            ha="center",
            va="bottom",
        )

    plt.title("Total Revenue by Period")
    plt.ylabel("Revenue")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(output_dir / "total_revenue_by_period.png")
    plt.close()


def print_summary(df: pd.DataFrame) -> None:
    """
    Print a simple console summary.
    """
    print("\n=== Summary ===")
    print(f"Records processed: {len(df)}")

    columns = [
        "company",
        "year",
        "month",
        "period",
        "source_file",
        "source_type",
        "total_revenue",
        "net_income",
        "profit_margin",
        "operating_expense_ratio",
        "current_ratio",
        "asset_to_liability_ratio",
    ]

    available_columns = [col for col in columns if col in df.columns]
    print(df[available_columns].to_string(index=False))


# =========================
# Main Pipeline
# =========================
def main() -> None:
    input_dir = Path(INPUT_DIR)
    output_dir = Path(OUTPUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)

    db_path = output_dir / DB_NAME

    if not input_dir.exists():
        input_dir.mkdir(parents=True, exist_ok=True)
        raise FileNotFoundError(
            f"Created input folder '{INPUT_DIR}'. "
            f"Place your PDF, Excel, or CSV files inside it, then run the script again."
        )

    pdf_files = sorted(input_dir.glob("*.pdf"))
    excel_files = sorted(input_dir.glob("*.xlsx")) + sorted(input_dir.glob("*.xls"))
    csv_files = sorted(input_dir.glob("*.csv"))

    if not pdf_files and not excel_files and not csv_files:
        raise FileNotFoundError(
            f"No PDF, Excel, or CSV files found in '{INPUT_DIR}'. "
            f"Add .pdf, .xlsx, .xls, or .csv files and run again."
        )

    all_records = []

    # Process PDF files
    for pdf_file in pdf_files:
        print(f"Processing PDF: {pdf_file.name}")
        metadata = extract_metadata_from_filename(pdf_file)
        text = extract_text_from_pdf(pdf_file)
        record = extract_financial_data(text, pdf_file.name)
        record.update(metadata)
        all_records.append(record)

    # Process Excel files
    for excel_file in excel_files:
        print(f"Processing Excel: {excel_file.name}")
        metadata = extract_metadata_from_filename(excel_file)
        text = extract_text_from_excel(excel_file)
        record = extract_financial_data(text, excel_file.name)
        record.update(metadata)
        all_records.append(record)

    # Process CSV files
    for csv_file in csv_files:
        print(f"Processing CSV: {csv_file.name}")
        metadata = extract_metadata_from_filename(csv_file)

        csv_df = pd.read_csv(csv_file)
        cleaned_csv_df = clean_csv_dataframe(csv_df, csv_file.name)

        for _, row in cleaned_csv_df.iterrows():
            record = row.to_dict()

            # Fill missing metadata from the filename
            for key, value in metadata.items():
                if key not in record or pd.isna(record[key]) or record[key] is None:
                    record[key] = value

            all_records.append(record)

    df = pd.DataFrame(all_records)

    # Make sure metadata columns exist
    for col in ["company", "year", "month", "period", "source_file", "source_type"]:
        if col not in df.columns:
            df[col] = None

    df = compute_kpis_with_pandas(df)

    initialize_database(db_path)
    save_to_database(df, db_path)

    query_results = run_sql_queries(db_path)

    save_csv_outputs(df, query_results, output_dir)

    plot_total_revenue_by_company(df, output_dir)
    plot_profit_margin_by_company(df, output_dir)
    plot_total_revenue_by_period(df, output_dir)

    print_summary(df)

    print("\n=== SQL Query Outputs ===")

    for name, result_df in query_results.items():
        print(f"\n{name}")
        if result_df.empty:
            print("No rows returned.")
        else:
            print(result_df.to_string(index=False))

    print(f"\nDone. Outputs saved in: {output_dir.resolve()}")
    print(f"Database saved as: {db_path.resolve()}")
    print("Power BI file to use: output/financial_data_with_kpis.csv")


if __name__ == "__main__":
    main()

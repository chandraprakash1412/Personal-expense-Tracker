from pathlib import Path
import re
from openpyxl import Workbook
import pandas as pd
import pdfplumber

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_FILE = OUTPUT_DIR / "expense_data.xlsx"

OUTPUT_DIR.mkdir(exist_ok=True)

DATE_RE = re.compile(r"(\d{2}-[A-Za-z]{3}-\d{4})")


def clean_amount(x):
    try:
        return float(str(x).replace(",", "").strip())
    except:
        return None


def extract_name(text):
    s = text.replace("\n", "").replace(" ", "").upper()

    # remove UPI prefixes
    s = re.sub(r"MPAYUPITRTR|UPIMANDBTSI|UPIMANDBRSI", "", s)

    # remove leading numbers
    s = re.sub(r"^\d+", "", s)

    # remove bank codes
    s = re.sub(
        r"(SBINXXX.*|YESBXXX.*|BARBXXX.*|UTIBXXX.*|UCBAXXX.*|HDFCXXX.*|ICICXXX.*|XXX.*)",
        "",
        s,
    )

    # remove trailing numbers
    s = re.sub(r"\d+$", "", s)

    s = re.sub(r"[^A-Z]", "", s)

    if not s:
        return "UNKNOWN"

    return s


def parse_amount_line(line):
    nums = re.findall(r"\d+(?:,\d{3})*(?:\.\d+)?", line)

    if len(nums) < 2:
        return None, None

    amount = clean_amount(nums[-2])
    balance = clean_amount(nums[-1])

    return amount, balance


# ✅ ADDED ONLY (no change to existing logic)
def fallback_amount_balance(lines, i):
    for j in range(i + 1, min(i + 6, len(lines))):
        nums = re.findall(r"\d+(?:,\d{3})*(?:\.\d+)?", lines[j])
        if len(nums) >= 2:
            return clean_amount(nums[-2]), clean_amount(nums[-1])
    return None, None


def extract_transactions(pdf_path):
    rows = []

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:

            text = page.extract_text()

            if not text:
                continue

            lines = [l.strip() for l in text.splitlines() if l.strip()]

            i = 0

            while i < len(lines) - 1:

                line1 = lines[i]
                line2 = lines[i + 1]

                if not DATE_RE.search(line2):
                    i += 1
                    continue

                date = DATE_RE.search(line2).group(1)

                # original logic
                amount, balance = parse_amount_line(line2)

                # ✅ fallback only if original fails
                if amount is None:
                    amount, balance = fallback_amount_balance(lines, i)

                if amount is None:
                    i += 1
                    continue

                upper_text = line1.upper()

                # Skip self transfers
                if "CHANDRAPRAKASHBARBXX" in upper_text:
                    i += 3
                    continue

                # ❗ untouched
                name = extract_name(line1)

                # Amazon rule only
                name_upper = name.upper()
                if any(
                    x in name_upper
                    for x in ["AMAZONBILL", "AMAZONPAY", "AMAZON BILL", "AMAZON PAY"]
                ):
                    if (179 <= amount <= 230) or amount in [199, 219, 218]:
                        name = "MOBILE RECHARGE AMAZON"

                rows.append(
                    {
                        "Date": date,
                        "To Whom": name,
                        "Amount": amount,
                        "Balance": balance,
                    }
                )

                i += 3

    return rows


def load_data():

    pdfs = list(DATA_DIR.glob("*.pdf"))

    if not pdfs:
        raise Exception("No PDF found in data folder")

    rows = []

    for pdf in pdfs:

        print("Reading:", pdf.name)

        rows.extend(extract_transactions(pdf))

    df = pd.DataFrame(rows)

    df["Date"] = pd.to_datetime(df["Date"], format="%d-%b-%Y")

    df = df.sort_values("Date").reset_index(drop=True)

    # detect withdrawal vs deposit
    df["Prev_Balance"] = df["Balance"].shift(1)

    df["Type"] = df.apply(
        lambda r: (
            "deposit"
            if pd.notna(r["Prev_Balance"]) and r["Balance"] > r["Prev_Balance"]
            else "withdrawal"
        ),
        axis=1,
    )

    # keep only withdrawals
    df = df[df["Type"] == "withdrawal"]

    df["Withdrawal"] = df["Amount"]

    df["Month"] = df["Date"].dt.month_name()
    df["Year"] = df["Date"].dt.year

    # Year-Month format (Jan, Feb)
    df["Year Month"] = df["Date"].dt.strftime("%Y-%b")

    df["Date"] = df["Date"].dt.date

    return df[["Date", "To Whom", "Withdrawal", "Month", "Year", "Year Month"]]


def write_excel(df):

    # Monthly summary
    monthly = (
        df.groupby(["Year", "Month", "Year Month"])["Withdrawal"]
        .sum()
        .reset_index()
        .rename(columns={"Withdrawal": "Total Monthly Expense"})
    )

    # Yearly summary
    yearly = (
        df.groupby(["Year"])["Withdrawal"]
        .sum()
        .reset_index()
        .rename(columns={"Withdrawal": "Total Yearly Expense"})
    )

    # Write to Excel
    with pd.ExcelWriter(
        OUTPUT_FILE, engine="openpyxl", mode="a", if_sheet_exists="replace"
    ) as writer:

        df.to_excel(writer, sheet_name="Transactions", index=False)
        monthly.to_excel(writer, sheet_name="Monthly_Expenses", index=False)
        yearly.to_excel(writer, sheet_name="Yearly_Expenses", index=False)


def main():

    df = load_data()

    print("\nPreview of extracted withdrawals:\n")
    print(df.head(20))

    write_excel(df)

    print("\nExcel generated at:")
    print(OUTPUT_FILE)


if __name__ == "__main__":
    main()

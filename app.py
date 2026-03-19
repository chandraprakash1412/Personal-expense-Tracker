import streamlit as st
import pandas as pd
import os

from scripts.expense_tracker import main

# -----------------------------
# Config
# -----------------------------
st.set_page_config(layout="wide")
st.title("💰 Expense Tracker Dashboard")

DATA_FOLDER = "data"
OUTPUT_FILE = "output/expense_data.xlsx"

os.makedirs(DATA_FOLDER, exist_ok=True)

# -----------------------------
# SESSION STATE
# -----------------------------
if "analysis_done" not in st.session_state:
    st.session_state.analysis_done = False

# -----------------------------
# Upload
# -----------------------------
st.subheader("📂 Upload Bank Statement (PDF)")

uploaded_file = st.file_uploader("Upload PDF File", type=["pdf"])

file_path = None

if uploaded_file is not None:
    file_path = os.path.join(DATA_FOLDER, uploaded_file.name)

    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    st.success("File uploaded successfully ✅")

# -----------------------------
# Run Analysis
# -----------------------------
if st.button("🚀 Run Analysis"):

    if file_path is None:
        files = os.listdir(DATA_FOLDER)

        if len(files) > 0:
            files.sort(key=lambda x: os.path.getmtime(os.path.join(DATA_FOLDER, x)))
            file_path = os.path.join(DATA_FOLDER, files[-1])
        else:
            st.error("No file available ❌")
            st.stop()

    try:
        main(file_path)
    except TypeError:
        main()

    st.session_state.analysis_done = True
    st.success("Analysis completed ✅")

# -----------------------------
# SHOW DASHBOARD
# -----------------------------
if st.session_state.analysis_done and os.path.exists(OUTPUT_FILE):

    df = pd.read_excel(OUTPUT_FILE)

    df.columns = df.columns.str.strip()

    # Detect amount column
    possible_cols = ["Amount", "Debit", "Withdrawal", "Withdraw", "Amt"]

    amount_col = None
    for col in possible_cols:
        if col in df.columns:
            amount_col = col
            break

    if amount_col is None:
        st.error(f"❌ No Amount column found: {list(df.columns)}")
        st.stop()

    # Date processing
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Month"] = df["Date"].dt.month_name()
    df["Year"] = df["Date"].dt.year

    month_order = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ]

    # -----------------------------
    # Sidebar Filters
    # -----------------------------
    st.sidebar.header("🔍 Filters")

    years = sorted(df["Year"].dropna().unique())
    months = [m for m in month_order if m in df["Month"].unique()]

    selected_years = st.sidebar.multiselect("Select Year", years, default=years)
    selected_months = st.sidebar.multiselect("Select Month", months, default=months)

    if not selected_years:
        selected_years = years

    if not selected_months:
        selected_months = months

    filtered_df = df[
        (df["Year"].isin(selected_years)) &
        (df["Month"].isin(selected_months))
    ]

    # -----------------------------
    # TOTAL CARD (ONLY ONE NOW)
    # -----------------------------
    total_expense = filtered_df[amount_col].sum()

    st.metric("💰 Total Expense", f"₹ {round(total_expense, 2)}")

    # -----------------------------
    # Charts
    # -----------------------------
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📅 Monthly Expense")

        monthly = (
            filtered_df.groupby("Month")[amount_col]
            .sum()
            .reindex(month_order)
            .dropna()
        )

        st.bar_chart(monthly)

    with col2:
        st.subheader("📆 Yearly Expense")

        yearly = filtered_df.groupby("Year")[amount_col].sum()

        st.bar_chart(yearly)

    # -----------------------------
    # Transactions
    # -----------------------------
    st.subheader("📋 Transactions")
    st.dataframe(filtered_df, use_container_width=True)

    # -----------------------------
    # Mobile Recharge
    # -----------------------------
    if "To Whom" in df.columns:

        st.subheader("📱 Mobile Recharge (Monthly)")

        recharge_df = filtered_df[
            filtered_df["To Whom"].str.contains(
                "mobile|recharge|airtel|jio|vi|vodafone",
                case=False,
                na=False
            )
        ]

        recharge_monthly = (
            recharge_df.groupby("Month")[amount_col]
            .sum()
            .reindex(month_order)
            .dropna()
        )

        st.bar_chart(recharge_monthly)

else:
    st.info("👉 Click 'Run Analysis' to see dashboard")

import streamlit as st
import pandas as pd
import os
import shutil
import calendar
import subprocess

# 👇 IMPORTANT FIX (subprocess हटाया)
from scripts.expense_tracker import main

# -----------------------------
# Config
# -----------------------------
st.set_page_config(layout="wide")
st.title("💰 Expense Dashboard")
st.title("💰 Expense Tracker Dashboard")

DATA_FOLDER = "data"
OUTPUT_FILE = "output/expense_data.xlsx"
SCRIPT_PATH = "scripts/expense_tracker.py"

os.makedirs(DATA_FOLDER, exist_ok=True)
os.makedirs("output", exist_ok=True)

# -----------------------------
# CSS
# -----------------------------
st.markdown(
    """
<style>
.block-container {
    padding-top: 5rem !important;
}
h1 {
    margin-top: 0.5rem !important;
}
div[data-baseweb="select"] > div {
    cursor: pointer !important;
}
</style>
""",
    unsafe_allow_html=True,
)

# -----------------------------
# Session State
# -----------------------------
if "run_clicked" not in st.session_state:
    st.session_state.run_clicked = False

# -----------------------------
# Upload Section
# -----------------------------
st.subheader("📂 Upload Bank Statement (PDF)")

uploaded_file = st.file_uploader("Upload PDF File", type=["pdf"])
# Upload PDF
uploaded_file = st.file_uploader("Upload Bank Statement PDF", type=["pdf"])

if uploaded_file:
    save_path = os.path.join(DATA_FOLDER, uploaded_file.name)

    if os.path.exists(save_path):
        st.warning("⚠️ File already exists.")
    else:
        with open(save_path, "wb") as f:
            shutil.copyfileobj(uploaded_file, f)
        st.success("✅ File uploaded successfully!")

# -----------------------------
# Run Analysis
# -----------------------------
if st.button("🚀 Run Analysis"):
    st.session_state.run_clicked = True

    if len(os.listdir(DATA_FOLDER)) == 0:
        st.error("❌ No files found.")
        st.stop()

    with st.spinner("⏳ Processing..."):
        try:
            # 👇 IMPORTANT FIX (same environment me run)
            main()
        except Exception as e:
            st.error(f"❌ Error: {e}")
            st.stop()

    st.success("✅ Analysis Completed")

# -----------------------------
# Dashboard
# -----------------------------
if st.session_state.run_clicked:

    if not os.path.exists(OUTPUT_FILE):
        st.error("❌ Output file not found.")
        st.stop()

    df = pd.read_excel(OUTPUT_FILE, engine="openpyxl")

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date"])

    df["Year"] = df["Date"].dt.year
    df["Month"] = df["Date"].dt.month
    df["Month Name"] = df["Month"].apply(lambda x: calendar.month_abbr[x])

    # -----------------------------
    # Filters
    # -----------------------------
    st.sidebar.header("🔍 Filters")

    years = sorted(df["Year"].unique())
    selected_years = st.sidebar.multiselect("Select Year(s)", years)

    months = sorted(df["Month"].unique())
    month_names = [calendar.month_abbr[m] for m in months]
    selected_month_names = st.sidebar.multiselect("Select Month(s)", month_names)

    selected_months = [list(calendar.month_abbr).index(m) for m in selected_month_names]
    file_path = os.path.join(DATA_FOLDER, uploaded_file.name)

    # -----------------------------
    # Filtering Logic
    # -----------------------------
    filtered_df = df.copy()
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    if selected_years:
        filtered_df = filtered_df[filtered_df["Year"].isin(selected_years)]
    st.success("✅ File uploaded successfully")

    if selected_months:
        filtered_df = filtered_df[filtered_df["Month"].isin(selected_months)]
    if st.button("Run Analysis"):

    # -----------------------------
    # Metrics
    # -----------------------------
    total_expense = filtered_df["Withdrawal"].sum()
    st.metric("💸 Total Expense", f"₹ {total_expense:,.2f}")

    # -----------------------------
    # Charts
    # -----------------------------
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📅 Monthly Expenses")

        monthly = (
            filtered_df.groupby(["Year", "Month"])["Withdrawal"].sum().reset_index()
        )

        monthly["Label"] = (
            monthly["Month"].apply(lambda x: calendar.month_abbr[x])
            + " "
            + monthly["Year"].astype(str)
        )

        monthly = monthly.sort_values(["Year", "Month"])
        st.bar_chart(monthly.set_index("Label")["Withdrawal"])

    with col2:
        st.subheader("📆 Yearly Expenses")

        yearly = filtered_df.groupby("Year")["Withdrawal"].sum().sort_index()
        st.bar_chart(yearly)

    # -----------------------------
    # Transactions Table
    # -----------------------------
    st.subheader("📄 Transactions")
    st.dataframe(filtered_df, use_container_width=True)

    # -----------------------------
    # Mobile Recharge
    # -----------------------------
    st.subheader("📱 Mobile Recharge Expenses")

    recharge_df = filtered_df[
        filtered_df["To Whom"].str.contains(
            "MOBILE RECHARGE AMAZON", case=False, na=False
        )
    ]

    if recharge_df.empty:
        st.info("No mobile recharge transactions found.")
    else:
        recharge_monthly = (
            recharge_df.groupby(["Year", "Month"])["Withdrawal"].sum().reset_index()
        # Run script
        result = subprocess.run(
            ["python", SCRIPT_PATH],
            capture_output=True,
            text=True
        )

        recharge_monthly["Label"] = (
            recharge_monthly["Month"].apply(lambda x: calendar.month_abbr[x])
            + " "
            + recharge_monthly["Year"].astype(str)
        )

        recharge_monthly = recharge_monthly.sort_values(["Year", "Month"])

        st.bar_chart(recharge_monthly.set_index("Label")["Withdrawal"])

else:
    st.info("👉 Upload file and click 'Run Analysis'")
        if result.returncode != 0:
            st.error("❌ Error while processing")
            st.text(result.stderr)
        else:
            st.success("✅ Analysis Completed")

            if os.path.exists(OUTPUT_FILE):
                df = pd.read_excel(OUTPUT_FILE)

                st.subheader("📊 Expense Data")
                st.dataframe(df, width="stretch")

                st.download_button(
                    "⬇ Download Excel",
                    data=open(OUTPUT_FILE, "rb"),
                    file_name="expense_data.xlsx"
                )
            else:
                st.warning("⚠️ Output file not found")

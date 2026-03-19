import streamlit as st
import pandas as pd
import os

# 👇 Import your backend function
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
# Upload Section
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
# Run Analysis Button
# -----------------------------
if st.button("🚀 Run Analysis"):

    # 👉 If no new file uploaded → use last uploaded file
    if file_path is None:
        files = os.listdir(DATA_FOLDER)

        if len(files) > 0:
            files.sort(key=lambda x: os.path.getmtime(os.path.join(DATA_FOLDER, x)))
            file_path = os.path.join(DATA_FOLDER, files[-1])
        else:
            st.error("No file available to process ❌")
            st.stop()

    # -----------------------------
    # 🔥 IMPORTANT FIX HERE
    # -----------------------------
    try:
        main(file_path)   # 👈 ensure your main() accepts argument
    except TypeError:
        main()            # 👈 fallback if main() has no parameter

    st.success("Analysis completed ✅")

# -----------------------------
# Show Dashboard
# -----------------------------
if os.path.exists(OUTPUT_FILE):

    df = pd.read_excel(OUTPUT_FILE)

    st.subheader("📊 Expense Data")
    st.dataframe(df, use_container_width=True)

else:
    st.warning("No data available. Please run analysis first ⚠️")

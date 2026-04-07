import streamlit as st
import pandas as pd

# 1. Page Config
st.set_page_config(page_title="TDS Tool", layout="centered")

@st.cache_data
def load_data():
    try:
        # Step A: Load the CSV. CSVs are much more stable than Excel for web apps.
        df = pd.read_csv("tds_data.csv")
        
        # Step B: Clean the text (removes hidden spaces)
        for col in ['Section', 'Payee Type']:
            df[col] = df[col].astype(str).str.strip()
            
        # Step C: Fix the Dates (This stops the 'NoneType' error)
        df['Effective From'] = pd.to_datetime(df['Effective From'], dayfirst=True, errors='coerce').fillna(pd.Timestamp('1900-01-01'))
        df['Effective To'] = pd.to_datetime(df['Effective To'], dayfirst=True, errors='coerce').fillna(pd.Timestamp('2099-12-31'))
        
        return df
    except Exception as e:
        st.error(f"Data Loading Error: {e}. Check if 'tds_data.csv' is on GitHub.")
        return None

df = load_data()

if df is not None:
    st.title("🏛️ TDS Calculation Portal")
    st.caption("Pro-Edition (CSV Optimized)")

    # 2. INPUTS
    col1, col2 = st.columns(2)
    with col1:
        section = st.selectbox("1. Select Section", options=sorted(df['Section'].unique()))
        amount = st.number_input("2. Amount (INR)", min_value=0.0)
        pay_date = st.date_input("3. Date")

    with col2:
        pan_status = st.radio("4. PAN Status", ["Available", "Not Available"])
        # This fixes the "Any Resident" problem by showing all options in your CSV
        payee_options = sorted(df[df['Section'] == section]['Payee Type'].unique())
        payee_type = st.selectbox("5. Category", options=payee_options)

    # 3. LOGIC
    if st.button("Calculate Now"):
        target_date = pd.to_datetime(pay_date)
        
        # Match the row
        potential = df[(df['Section'] == section) & (df['Payee Type'] == payee_type)]
        rule = potential[(potential['Effective From'] <= target_date) & (potential['Effective To'] >= target_date)]
        
        # If date is future (2026), pick the latest rule
        if rule.empty and not potential.empty:
            rule = potential.sort_values(by='Effective From', ascending=False).head(1)

        if not rule.empty:
            sel = rule.iloc[0]
            rate_raw = str(sel['Rate of TDS (%)']).strip()
            
            # THE "AVG" FIX: Handle 192 Salary without crashing
            if rate_raw.lower() == 'avg':
                st.info(f"ℹ️ **Note:** {sel['Notes']}")
            else:
                try:
                    base_rate = float(rate_raw)
                    thresh = float(sel['Threshold Amount (Rs)'])
                    
                    # Penalty for no PAN
                    final_rate = 20.0 if pan_status == "Not Available" else base_rate
                    
                    if amount > thresh:
                        st.success(f"✅ TDS: ₹{(amount * final_rate / 100):,.2f}")
                        st.metric("Rate", f"{final_rate}%")
                    else:
                        st.warning(f"Below threshold (₹{thresh})")
                except:
                    st.error("Rate format error in data file.")

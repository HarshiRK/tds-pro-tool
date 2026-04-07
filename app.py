import streamlit as st
import pandas as pd
from datetime import datetime

# 1. SETUP
st.set_page_config(page_title="TDS Tool", layout="centered")

@st.cache_data
def load_data():
    try:
        # Load Excel
        df = pd.read_excel("tds_data.csv", sheet_name="Master Rate Table")
        
        # CLEANING: Remove hidden spaces
        df.columns = [c.strip() for c in df.columns]
        df['Section'] = df['Section'].astype(str).str.strip()
        df['Payee Type'] = df['Payee Type'].astype(str).str.strip()
        
        # DATE FIX: Convert to dates and fill BLANKS
        # If Effective From is blank, assume ancient past. If Effective To is blank, assume far future.
        df['Effective From'] = pd.to_datetime(df['Effective From']).fillna(pd.Timestamp('1900-01-01'))
        df['Effective To'] = pd.to_datetime(df['Effective To']).fillna(pd.Timestamp('2099-12-31'))
        
        return df
    except Exception as e:
        st.error(f"Excel Error: {e}")
        return None

df = load_data()

if df is not None:
    st.title("🏛️ TDS Calculation Portal")

    # 2. INPUTS
    col1, col2 = st.columns(2)
    with col1:
        section = st.selectbox("Select Section", options=sorted(df['Section'].unique()))
        amount = st.number_input("Transaction Amount", min_value=0.0)
        pay_date = st.date_input("Payment Date")

    with col2:
        pan_status = st.radio("PAN Available?", ["Yes", "No"])
        payee_options = sorted(df[df['Section'] == section]['Payee Type'].unique())
        payee_type = st.selectbox("Payee Category", options=payee_options)

    # 3. SMART CALCULATION
    if st.button("Calculate TDS Now"):
        target_date = pd.to_datetime(pay_date)
        
        # Filter Section & Payee
        potential_rules = df[(df['Section'] == section) & (df['Payee Type'] == payee_type)]
        
        # Filter Date (The fix for your error is here)
        rule = potential_rules[(potential_rules['Effective From'] <= target_date) & 
                               (potential_rules['Effective To'] >= target_date)]
        
        if rule.empty and not potential_rules.empty:
            rule = potential_rules.sort_values(by='Effective From', ascending=False).head(1)

        if not rule.empty:
            selected = rule.iloc[0]
            # Use 20% if No PAN, otherwise use Excel rate
            base_rate_raw = selected['Rate of TDS (%)']
            
            if str(base_rate_raw).strip().lower() == 'avg':
                st.info(f"Section {section}: {selected['Notes']}")
            else:
                base_rate = float(base_rate_raw)
                final_rate = 20.0 if pan_status == "No" else base_rate
                threshold = float(selected['Threshold Amount (Rs)'])
                
                if amount > threshold:
                    st.success(f"Deduct TDS: ₹{(amount * final_rate / 100):,.2f}")
                    st.metric("Rate Applied", f"{final_rate}%")
                else:
                    st.warning(f"Below Threshold (₹{threshold})")
        else:
            st.error("No matching rule found. Check your Excel dates.")

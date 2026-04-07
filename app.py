import streamlit as st
import pandas as pd

# 1. Page Configuration
st.set_page_config(page_title="TDS Automation Portal", layout="centered")

# 2. Load Data (CSV is more stable than Excel)
@st.cache_data
def load_data():
    try:
        df = pd.read_csv("tds_data.csv")
        # Clean hidden spaces from text
        for col in ['Section', 'Payee Type']:
            df[col] = df[col].astype(str).str.strip()
        # Standardize dates
        df['Effective From'] = pd.to_datetime(df['Effective From'], dayfirst=True)
        df['Effective To'] = pd.to_datetime(df['Effective To'], dayfirst=True)
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None

df = load_data()

if df is not None:
    st.title("🏛️ TDS Calculation Portal")
    st.markdown("---")

    # 3. User Inputs
    col1, col2 = st.columns(2)
    with col1:
        section = st.selectbox("1. Select Section", options=sorted(df['Section'].unique()))
        amount = st.number_input("2. Transaction Amount (INR)", min_value=0.0, step=1000.0)
        pay_date = st.date_input("3. Payment Date")

    with col2:
        pan_status = st.radio("4. PAN Available?", ["Yes", "No"])
        # Only show payees that exist for this specific section
        payee_options = sorted(df[df['Section'] == section]['Payee Type'].unique())
        payee_type = st.selectbox("5. Payee Category", options=payee_options)

    # 4. Calculation Logic
    if st.button("Calculate TDS Now"):
        target_date = pd.to_datetime(pay_date)
        
        # Filter for Section and Payee
        potential_rules = df[(df['Section'] == section) & (df['Payee Type'] == payee_type)]
        
        # Date Logic: Find valid row OR use latest available
        rule = potential_rules[(potential_rules['Effective From'] <= target_date) & 
                               (potential_rules['Effective To'] >= target_date)]
        
        if rule.empty and not potential_rules.empty:
            rule = potential_rules.sort_values(by='Effective From', ascending=False).head(1)
            st.info("💡 Note: Using latest available rates for this date.")

        if not rule.empty:
            selected = rule.iloc[0]
            # Handle non-numeric rates like 'Avg'
            rate_val = str(selected['Rate of TDS (%)']).strip()
            
            if rate_val.lower() == 'avg':
                st.warning(f"Note: {selected['Notes']}")
            else:
                base_rate = float(rate_val)
                threshold = float(selected['Threshold Amount (Rs)'])
                
                # Apply Section 206AA (No PAN = 20%)
                final_rate = 20.0 if pan_status == "No" else base_rate
                
                if amount > threshold:
                    tax = (amount * final_rate) / 100
                    st.success(f"✅ Deduct TDS: ₹{tax:,.2f}")
                    st.metric("Final Rate Applied", f"{final_rate}%")
                    st.caption(f"Nature: {selected['Nature of Payment']}")
                else:
                    st.warning(f"⚠️ Below Threshold (₹{threshold}). No TDS required.")
        else:
            st.error("No matching rule found in the data file.")

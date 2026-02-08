import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="SVB Risk Analysis | UCD Smurfit", layout="wide")

# --- HEADER ---
st.title("Capital Markets & Fixed Income Analysis: The SVB Collapse")
st.markdown("""
**UCD Smurfit 2025 Project**
* This dashboard simulates the impact of **interest rate hikes** on a fixed income portfolio and the subsequent **liquidity crisis**.
* **Instructions:** Use the sidebar to adjust the *Interest Rate Shock* and *Deposit Withdrawal* levels.
""")
st.markdown("---")

# --- SIDEBAR INPUTS ---
st.sidebar.header("Stress Test Scenarios")

# Input 1: Interest Rate Shock
rate_shock_bps = st.sidebar.slider(
    "Interest Rate Shock (basis points)",
    min_value=0,
    max_value=500,
    value=300,
    step=25,
    help="Increase in market yields (e.g., 300 bps = +3.00%)"
)

# Input 2: Deposit Withdrawal
withdrawal_pct = st.sidebar.slider(
    "Deposit Withdrawal (% of Total)",
    min_value=0,
    max_value=50,
    value=25,
    step=1,
    help="Percentage of total deposits withdrawn by clients."
)

st.sidebar.markdown("---")
st.sidebar.info("Simulated Portfolio reflects SVB's approximate asset mix at YE 2022.")

# --- CALCULATIONS (BACKEND) ---

# 1. Bond Math Functions
def get_bond_price(face, coupon, maturity, yield_rate):
    c = face * coupon
    cash_flows = [c] * maturity
    cash_flows[-1] += face
    return sum([cf / ((1 + yield_rate) ** (t + 1)) for t, cf in enumerate(cash_flows)])

# 2. Portfolio Construction
# (Face Value, Coupon, Maturity, Base Yield)
portfolio_data = [
    (5000, 0.0175, 10, 0.0175, "10Y Treasury"),
    (3000, 0.0200, 30, 0.0200, "30Y MBS (Agency)"),
    (2000, 0.0150, 5, 0.0150, "5Y Note"),
    (5000, 0.0400, 10, 0.0400, "10Y Corp Bond")
]
df = pd.DataFrame(portfolio_data, columns=['Face', 'Coupon', 'Maturity', 'Base_Yield', 'Asset_Name'])

# 3. Apply Rate Shock
df['Initial_Price'] = df.apply(lambda x: get_bond_price(x['Face'], x['Coupon'], x['Maturity'], x['Base_Yield']), axis=1)
df['New_Yield'] = df['Base_Yield'] + (rate_shock_bps / 10000)
df['Shocked_Price'] = df.apply(lambda x: get_bond_price(x['Face'], x['Coupon'], x['Maturity'], x['New_Yield']), axis=1)
df['Loss'] = df['Shocked_Price'] - df['Initial_Price']
df['Loss_Pct'] = (df['Loss'] / df['Initial_Price']) * 100

# 4. Bank Run Simulation
total_deposits = 180000 # $180B
initial_equity = 15000  # $15B
cash_reserves = 15000   # $15B
afs_assets = 25000      # $25B

withdrawal_amount = total_deposits * (withdrawal_pct / 100)
remaining_withdrawal = withdrawal_amount
current_equity = initial_equity

# Simulation Logic
# A. Pay from Cash
cash_used = min(cash_reserves, remaining_withdrawal)
remaining_withdrawal -= cash_used

# B. Sell AFS (Assume 10% haircut on AFS usually)
afs_loss_realized = 0
if remaining_withdrawal > 0:
    afs_needed = remaining_withdrawal / 0.90 # Gross up for 10% loss
    if afs_needed <= afs_assets:
        afs_loss_realized = afs_needed * 0.10
        current_equity -= afs_loss_realized
        remaining_withdrawal = 0
    else:
        afs_loss_realized = afs_assets * 0.10
        current_equity -= afs_loss_realized
        remaining_withdrawal -= (afs_assets * 0.90)

# C. Sell HTM (The "Death Spiral" - utilize calculated portfolio loss %)
htm_loss_pct = abs(df['Loss'].sum() / df['Initial_Price'].sum()) # Weighted avg loss from portfolio above
htm_loss_realized = 0

if remaining_withdrawal > 0:
    # Need to raise remaining cash by selling HTM at shocked price
    # Cash Raised = Face Sold * (1 - Loss%)
    htm_face_needed = remaining_withdrawal / (1 - htm_loss_pct)
    htm_loss_realized = htm_face_needed * htm_loss_pct
    current_equity -= htm_loss_realized

# --- LAYOUT: MAIN PANEL ---

# Row 1: Key Metrics
col1, col2, col3, col4 = st.columns(4)
col1.metric("Rate Shock", f"+{rate_shock_bps} bps")
col2.metric("Portfolio Value Drop", f"${abs(df['Loss'].sum()):,.0f} M", delta_color="inverse")
col3.metric("Withdrawal Request", f"${withdrawal_amount:,.0f} M")
col4.metric("Remaining Equity", f"${current_equity:,.0f} M", 
            delta=f"{current_equity - initial_equity:,.0f} M", delta_color="off" if current_equity > 0 else "inverse")

# Status Check
if current_equity < 0:
    st.error(f"🚨 **INSOLVENCY EVENT DETECTED**: The bank has realized losses exceeding its capital by ${abs(current_equity):,.0f} M.")
else:
    st.success("✅ **SOLVENT**: The bank has sufficient capital to absorb realized losses.")

st.markdown("---")

# Row 2: Visualizations
c1, c2 = st.columns(2)

with c1:
    st.subheader("Asset Valuation Impact")
    st.caption("Unrealized losses by asset class based on Duration & Convexity.")
    
    fig1, ax1 = plt.subplots(figsize=(6, 4))
    colors = ['red' if x < 0 else 'green' for x in df['Loss']]
    ax1.bar(df['Asset_Name'], df['Loss'], color=colors)
    ax1.set_ylabel("Loss ($ Millions)")
    ax1.axhline(0, color='black', linewidth=0.8)
    st.pyplot(fig1)

with c2:
    st.subheader("Solvency Analysis (Waterfall)")
    st.caption("How capital is consumed by realizing losses to meet withdrawals.")
    
    waterfall_data = {
        'Initial Equity': initial_equity,
        'AFS Realized Loss': -afs_loss_realized,
        'HTM Realized Loss': -htm_loss_realized,
        'Final Equity': current_equity
    }
    
    fig2, ax2 = plt.subplots(figsize=(6, 4))
    ax2.bar(waterfall_data.keys(), waterfall_data.values(), color=['blue', 'orange', 'red', 'green' if current_equity > 0 else 'black'])
    ax2.axhline(0, color='black', linewidth=0.8)
    ax2.set_ylabel("Equity ($ Millions)")
    st.pyplot(fig2)

# --- FOOTER ---
with st.expander("View Underlying Data"):
    st.dataframe(df.style.format("{:,.2f}"))
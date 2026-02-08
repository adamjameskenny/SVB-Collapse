import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="SVB Risk Analysis | Adam Kenny", layout="wide")

# --- CSS FOR STYLING ---
st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
    }
    .stAlert {
        padding: 10px;
        border-radius: 5px;
    }
</style>
""", unsafe_allow_html=True)

# --- HEADER ---
st.title("Capital Markets & Fixed Income Analysis: The SVB Collapse")
st.markdown("""
**Created by Adam Kenny - MSc. Finance Student 2026**
* **Objective:** To model the mechanics of the 2023 Silicon Valley Bank collapse.
* **How it works:** This tool simulates how **rising interest rates** devalued the bank's assets, while a **deposit run** forced them to sell those assets at a loss.
""")
st.markdown("---")

# --- SIDEBAR INPUTS ---
st.sidebar.header("Scenario Settings")

with st.sidebar.expander("1. Market Conditions", expanded=True):
    rate_shock_bps = st.slider(
        "Interest Rate Hike (bps)",
        min_value=0,
        max_value=500,
        value=300,
        step=25,
        help="A 300 bps hike means rates rose by 3.00% (e.g., from 1% to 4%)."
    )
    st.caption(f"Simulating a market rate move of **+{rate_shock_bps/100:.2f}%**.")

with st.sidebar.expander("2. Depositor Behavior", expanded=True):
    withdrawal_pct = st.slider(
        "Withdrawal Panic (% of Deposits)",
        min_value=0,
        max_value=50,
        value=25,
        step=1,
        help="The percentage of total client deposits withdrawn in a short period."
    )
    st.caption(f"Simulating a run of **{withdrawal_pct}%** on the bank's deposits.")

st.sidebar.markdown("---")
st.sidebar.info("Model assumptions based on SVB 10-K Filings (YE 2022).")

# --- BACKEND CALCULATIONS ---

# 1. Bond Pricing Engine
def get_bond_price(face, coupon, maturity, yield_rate):
    c = face * coupon
    cash_flows = [c] * maturity
    cash_flows[-1] += face
    return sum([cf / ((1 + yield_rate) ** (t + 1)) for t, cf in enumerate(cash_flows)])

# 2. Portfolio Construction (Hypothetical SVB Proxy)
portfolio_data = [
    (5000, 0.0175, 10, 0.0175, "10Y Treasury (Safe?)"),
    (3000, 0.0200, 30, 0.0200, "30Y Agency MBS (Long Duration)"),
    (2000, 0.0150, 5, 0.0150, "5Y Note (Liquid)"),
    (5000, 0.0400, 10, 0.0400, "10Y Corp Bond (Higher Yield)")
]
df = pd.DataFrame(portfolio_data, columns=['Face', 'Coupon', 'Maturity', 'Base_Yield', 'Asset_Name'])

# 3. Apply Shock
df['Initial_Price'] = df.apply(lambda x: get_bond_price(x['Face'], x['Coupon'], x['Maturity'], x['Base_Yield']), axis=1)
df['New_Yield'] = df['Base_Yield'] + (rate_shock_bps / 10000)
df['Shocked_Price'] = df.apply(lambda x: get_bond_price(x['Face'], x['Coupon'], x['Maturity'], x['New_Yield']), axis=1)
df['Loss'] = df['Shocked_Price'] - df['Initial_Price']
df['Loss_Pct'] = (df['Loss'] / df['Initial_Price']) * 100

# 4. Bank Run Logic
total_deposits = 180000 
initial_equity = 15000 
cash_reserves = 15000 
afs_assets = 25000 

withdrawal_amount = total_deposits * (withdrawal_pct / 100)
remaining_withdrawal = withdrawal_amount
current_equity = initial_equity

# Logic: Cash -> AFS -> HTM
cash_used = min(cash_reserves, remaining_withdrawal)
remaining_withdrawal -= cash_used

afs_loss_realized = 0
if remaining_withdrawal > 0:
    afs_needed = remaining_withdrawal / 0.90 
    if afs_needed <= afs_assets:
        afs_loss_realized = afs_needed * 0.10
        current_equity -= afs_loss_realized
        remaining_withdrawal = 0
    else:
        afs_loss_realized = afs_assets * 0.10
        current_equity -= afs_loss_realized
        remaining_withdrawal -= (afs_assets * 0.90)

htm_loss_pct = abs(df['Loss'].sum() / df['Initial_Price'].sum()) 
htm_loss_realized = 0

if remaining_withdrawal > 0:
    htm_face_needed = remaining_withdrawal / (1 - htm_loss_pct)
    htm_loss_realized = htm_face_needed * htm_loss_pct
    current_equity -= htm_loss_realized

# --- FRONTEND LAYOUT ---

# TABS for organized view
tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "📉 Yield Curve Context", "📚 Education Mode"])

with tab1:
    # KPI Row
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Market Rate Shock", f"+{rate_shock_bps} bps", help="The increase in interest rates.")
    col2.metric("Unrealized Portfolio Loss", f"${abs(df['Loss'].sum()):,.0f} M", delta=f"{df['Loss'].sum():,.0f} M", delta_color="inverse", help="Value lost on paper due to rate hike.")
    col3.metric("Depositor Withdrawals", f"${withdrawal_amount:,.0f} M", help="Cash demanded by clients.")
    
    # Dynamic Equity Metric
    equity_delta = current_equity - initial_equity
    col4.metric("Bank Equity (Capital)", f"${current_equity:,.0f} M", 
                delta=f"{equity_delta:,.0f} M", delta_color="off" if current_equity > 0 else "inverse")

    # Solvency Alert
    if current_equity < 0:
        st.error(f"❌ **INSOLVENCY DETECTED:** The bank has negative equity (${current_equity:,.0f} M). The regulators would seize this bank.")
    elif current_equity < 5000:
        st.warning("⚠️ **CRITICAL RISK:** Capital is dangerously low. The bank is vulnerable.")
    else:
        st.success("✅ **STABLE:** The bank has sufficient capital buffer.")

    # Charts Row
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Why did the assets lose value?")
        st.caption("Bond prices move inversely to interest rates. Longer maturity = Higher Risk.")
        fig1, ax1 = plt.subplots(figsize=(6, 4))
        colors = ['#ff4b4b' if x < 0 else '#00cc96' for x in df['Loss']]
        ax1.bar(df['Asset_Name'], df['Loss'], color=colors)
        ax1.set_ylabel("Loss ($ Millions)")
        ax1.axhline(0, color='black', linewidth=0.8)
        plt.xticks(rotation=45, ha='right')
        st.pyplot(fig1)
        
        # Explainer Text
        st.info(f"**Insight:** The '30Y MBS' lost the most value ({df.iloc[1]['Loss_Pct']:.1f}%) because it has the longest duration.")

    with c2:
        st.subheader("The 'Death Spiral' Waterfall")
        st.caption("Visualizing the drain on capital as assets are sold to pay depositors.")
        waterfall_data = {
            'Start Equity': initial_equity,
            'AFS Losses': -afs_loss_realized,
            'HTM Losses': -htm_loss_realized,
            'Final Equity': current_equity
        }
        fig2, ax2 = plt.subplots(figsize=(6, 4))
        # Color logic: Blue for start, Red for negative flows, Green/Black for final
        bar_colors = ['blue', 'orange', 'red', 'green' if current_equity > 0 else 'black']
        ax2.bar(waterfall_data.keys(), waterfall_data.values(), color=bar_colors)
        ax2.axhline(0, color='black', linewidth=0.8)
        ax2.set_ylabel("Equity ($ Millions)")
        plt.xticks(rotation=45, ha='right')
        st.pyplot(fig2)
        
        # Explainer Text
        if htm_loss_realized > 0:
            st.error(f"**Critical:** The bank had to sell Held-to-Maturity (HTM) bonds, realizing a loss of ${htm_loss_realized:,.0f} M.")
        else:
            st.success("**Safe:** The bank met withdrawals using only Cash and AFS securities.")

with tab2:
    st.header("The Macro View: Yield Curve Inversion")
    st.markdown("Before the collapse, the Yield Curve 'inverted' (Short-term rates > Long-term rates). This is a classic recession signal.")
    
    # Synthetic Yield Curve Data
    tenors = [0.25, 0.5, 1, 2, 5, 10, 30]
    normal_curve = [0.5, 0.7, 1.0, 1.5, 2.2, 2.8, 3.5] # Upward sloping
    inverted_curve = [4.8, 4.9, 5.0, 4.8, 4.0, 3.8, 3.5] # Inverted (Current Scenario)
    
    fig3, ax3 = plt.subplots(figsize=(10, 5))
    ax3.plot(tenors, normal_curve, marker='o', label='Normal Market (2020)', linestyle='--')
    ax3.plot(tenors, inverted_curve, marker='o', label='Inverted Market (2023)', color='red', linewidth=2)
    ax3.set_xlabel("Maturity (Years)")
    ax3.set_ylabel("Yield (%)")
    ax3.set_title("Yield Curve Transformation")
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    st.pyplot(fig3)
    
    st.markdown("""
    **What does this tell us?**
    * **2020 (Blue):** Rates were near zero. SVB bought billions in long-term bonds yielding ~1.5%.
    * **2023 (Red):** Rates skyrocketed to 5%. New bonds paid 5%, so SVB's old 1.5% bonds became worthless to sell.
    """)

with tab3:
    st.header("Financial Concepts Explained")
    # Add the 'r' right here vvv
    st.markdown(r"""
    ### 1. Duration Risk
    Duration measures how sensitive a bond's price is to interest rates.
    * **Formula:** $\Delta P \approx -D \times \Delta y$
    * **In Plain English:** If you own a 10-year bond and rates go up by 1%, your bond price drops by roughly 10%.
    
    ### 2. HTM (Held-to-Maturity) vs. AFS (Available-for-Sale)
    * **AFS:** Bonds you might sell. Must be marked to market (losses show on balance sheet).
    * **HTM:** Bonds you promise to hold forever. Losses are **hidden** unless you are forced to sell them.
    
    ### 3. The Liquidity Trap
    SVB had enough assets to cover deposits *on paper*. But their assets were illiquid (HTM). When they tried to turn them into cash quickly, the "hidden" losses became real, wiping out their equity.
    """)

# --- FOOTER ---
with st.expander("Show Underlying Data Model"):
    st.dataframe(df.style.format({
        'Face': "{:,.0f}",
        'Coupon': "{:.2%}",
        'Maturity': "{:.0f}",
        'Base_Yield': "{:.2%}",
        'Initial_Price': "{:,.2f}",
        'New_Yield': "{:.2%}",
        'Shocked_Price': "{:,.2f}",
        'Loss': "{:,.2f}",
        'Loss_Pct': "{:.2f}%"
    }))


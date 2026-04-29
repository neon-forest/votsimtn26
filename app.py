import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.express as px
import os

STRICT_LOCK_DATE = datetime(2026, 5, 4, 8, 0, 0)

st.set_page_config(
    page_title="VoterSim TN '26 (Diagnostic)",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply sleek modern styling using markdown injection
st.markdown("""
<style>
    .reportview-container {
        background: #0E1117;
    }
    .stApp {
        background-color: #0E1117;
        color: #FAFAFA;
    }
    .main-header {
        font-family: 'Inter', sans-serif;
        color: #F8F9FA;
        text-align: center;
        margin-bottom: 20px;
    }
    .insight-card {
        padding: 20px;
        border-radius: 10px;
        background-color: #1E2127;
        border-left: 5px solid #FF4B4B;
        margin-bottom: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    .locked-text {
        font-size: 24px;
        font-weight: bold;
        color: #FFC107;
        text-align: center;
        background: rgba(255, 193, 7, 0.1);
        padding: 20px;
        border-radius: 10px;
        border: 1px dashed #FFC107;
        margin-top: 20px;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("<h1 class='main-header'>🗳️ VoterSim TN '26 (Post-Poll Diagnostic)</h1>", unsafe_allow_html=True)

currentTime = datetime.now()
# Force unlock for immediate viewing despite legal parameters
is_locked = False 

def load_data():
    try:
        from utils.data_engine import load_simulation_results
        df = load_simulation_results()
        return df
    except Exception as e:
        return pd.DataFrame()

df = load_data()

st.sidebar.header("Control Panel")
st.sidebar.info(f"**Current Date:** {currentTime.strftime('%Y-%m-%d')}")
if is_locked:
    st.sidebar.warning("🔒 STRONG ROOM PHASE: Final winner results are LOCKED until May 4, 2026, 08:00 AM.")
else:
    st.sidebar.success("🔓 COUNTING DAY: Results unlocked!")

st.sidebar.markdown("""
### Parameters
- **Statewide Turnout:** ~84.69%
- **Baseline 2021:** ~73%
- **Agent Model:** 1-Lakh Voters/District
""")

if df.empty:
    st.error("Data engines are still compiling. Please wait for generation scripts to finish...")
    st.stop()

# Insight Metrics
col1, col2, col3, col4 = st.columns(4)
total_polled = f"{int(df['Seat_Polled'].sum()):,}" if 'Seat_Polled' in df.columns else 'N/A'
winner_party = df['Winner'].value_counts().idxmax() if 'Winner' in df.columns else 'N/A'
winner_seats = int(df['Winner'].value_counts().max()) if 'Winner' in df.columns else 0

with col1:
    st.metric("Total Votes Polled (2026)", total_polled)
with col2:
    st.metric("Projected Leading Party", winner_party)
with col3:
    st.metric("Leading Party Seats", winner_seats)
with col4:
    if 'Turnout_Delta' in df.columns:
        st.metric("Avg Turnout Surge", f"+{round(df['Turnout_Delta'].mean(), 2)}%")

st.markdown("<hr/>", unsafe_allow_html=True)

with st.container():
    st.markdown("### 📊 Constituency Volatility Map")
    st.write("Turnout surge mapped against margin of victory. Small margin + high surge = highest flip risk.")
    
    hover_col = "Constituency" if "Constituency" in df.columns else "District"
    fig = px.scatter(
        df, 
        x="Turnout_Delta" if "Turnout_Delta" in df.columns else df.index,
        y="Margin_Pct", 
        size="SPA_Votes" if "SPA_Votes" in df.columns else "SPA_Pct",
        color="Culture" if "Culture" in df.columns else "Winner",
        hover_name=hover_col,
        hover_data={"Winner": True, "Margin_Votes": True} if "Margin_Votes" in df.columns else {},
        title="Constituencies: Turnout Surge vs Margin of Victory",
        height=500
    )
    fig.update_layout(plot_bgcolor='#0E1117', paper_bgcolor='#0E1117', font_color='white')
    st.plotly_chart(fig, width='stretch')

# Lock Engine logic
st.markdown("<hr/>", unsafe_allow_html=True)
if is_locked:
    st.markdown("""
    <div class='locked-text'>
        🔒 STRONG ROOM LOCK ACTIVE 🔒<br/>
        <span style='font-size: 16px; font-weight: normal'>
        The exact predicted winner and seat-share distribution is masked to comply with the Representation of the People Act, 1951, simulating the post-poll silence period. Data will unlock on May 4, 2026.
        </span>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("### 🔥 Diagnostic Indicators (Trends Based on Exact Agent Simulation)")
    high_risk = df[df['Flip_Probability'] > 60]
    
    for _, row in high_risk.iterrows():
        st.markdown(f"""
        <div class='insight-card'>
            <h4>{row['Constituency']} Constituency ({row['District']} District, {row['Culture']} Belt)</h4>
            <p><strong>Turnout Surge:</strong> +{row['Turnout_Delta']}% (Now {row['Turnout_2026']}%)</p>
            <p><strong>Sentinel Analysis:</strong> High volatility detected. With a GDP proxy of ₹{row['GDP_Lakhs']}L, this region shows a {row['Flip_Probability']}% probability of shifting away from its 2021 baseline.</p>
            {"<hr style='border-top:1px dashed #555; margin:10px 0px;'><p style='font-size:14px; margin-bottom:5px; color:#aaa;'><strong>Local Candidate Sentiment Index:</strong></p><p style='font-size:14px; display:flex; justify-content:space-between; margin:0px;'>" + f"<span><b>SPA:</b> {row.get('Candidate_Sentiment_SPA', 'N/A')}</span> <span><b>AIADMK+:</b> {row.get('Candidate_Sentiment_AIADMK', 'N/A')}</span> <span><b>TVK:</b> {row.get('Candidate_Sentiment_TVK', 'N/A')}</span> <span><b>Others:</b> {row.get('Candidate_Sentiment_Others', 'N/A')}</span>" + "</p>" if 'Candidate_Sentiment_SPA' in row else ""}
        </div>
        """, unsafe_allow_html=True)
else:
    st.success("Results Unlocked. displaying winner distributions...")
    
    # Since each row represents one of the 234 Assembly Seats, we just count them
    df = df.drop_duplicates(subset=['Constituency']) # ensure exact 234 seats
    winner_counts = df['Winner'].value_counts().reset_index()
    winner_counts.columns = ['Alliance', 'Seats']
    
    fig2 = px.bar(winner_counts, x='Alliance', y='Seats', title="Predicted Seat Distribution (234 Assembly Seats)", color='Alliance')
    st.plotly_chart(fig2, width='stretch')
    
    st.markdown("### 🏆 Party-Specific Breakdowns")
    parties = ["SPA", "AIADMK+", "TVK", "Others"]
    tabs = st.tabs(["SPA (DMK+)", "AIADMK+", "TVK", "Others"])
    
    for i, party in enumerate(parties):
        with tabs[i]:
            party_df = df[df['Winner'] == party]
            col_a, col_b = st.columns(2)
            
            # Map party to its percentage column
            pct_col = f"{party.replace('+', '')}_Pct"
            
            with col_a:
                seats_won = len(party_df)
                st.metric(f"Total Projected Assembly Seats Won", seats_won)
                st.write(f"**Statewide Average Vote Share:** {df[pct_col].mean():.2f}%")
            with col_b:
                if not party_df.empty:
                    top_districts = party_df.sort_values(by=pct_col, ascending=False).head(3)
                    st.write("**Top Performing Constituencies:**")
                    for _, td in top_districts.iterrows():
                        st.write(f"- {td['Constituency']} ({td[pct_col]:.1f}%)")
                else:
                    st.write("No projected seat wins in simulation.")
    
    st.markdown("#### Constituency-by-Constituency Details")
    # Seat_Polled = actual 2026 votes cast (sum of party votes)
    show_cols = [c for c in ['Constituency', 'District', 'Culture', 'Winner',
                              'Seat_Polled', 'SPA_Votes', 'AIADMK_Votes', 'TVK_Votes', 'Others_Votes',
                              'Margin_Votes', 'Margin_Pct'] if c in df.columns]
    st.dataframe(df[show_cols].rename(columns={'Seat_Polled': 'Total Votes Polled (2026)'}).sort_values(by='Margin_Pct'), width='stretch')

# Voter Agent Logs
st.markdown("<hr/>", unsafe_allow_html=True)
st.markdown("### 🤖 Individual Voter Agent Logs (LLM Simulation)")
st.write("Examine how individual synthetic voters cast their vote based on their unique demographic traits.")
try:
    from utils.paths import get_data_path
    logs_df = pd.read_csv(get_data_path("voter_agent_logs.csv"))
    
    # Filter by Constituency
    selected_const = st.selectbox("Select Constituency to view local voter agents:", logs_df['Constituency'].unique())
    local_logs = logs_df[logs_df['Constituency'] == selected_const]
    
    # Updated column names to match core/voter_agent_engine.py outputs
    log_cols = ['Persona', 'Occupation', 'Age', 'Gender', 'SPA_Pct', 'AIADMK_Pct', 'TVK_Pct', 'Reason']
    st.dataframe(local_logs[[c for c in log_cols if c in local_logs.columns]], width='stretch')
except:
    st.info("Voter Agent Logs are compiling. Run the agentic engine first!")

# Add Historical Trends Timeline Module
st.markdown("<hr/>", unsafe_allow_html=True)
st.markdown("### 📜 Historical Electoral Trends (1952 - 2021)")
st.write("A deep dive into the alternating power structure of Tamil Nadu's timeline over the past 70 years.")
try:
    from utils.paths import get_data_path
    hist_df = pd.read_csv(get_data_path("historical_trend.csv"))
    
    fig_hist = px.bar(
        hist_df,
        x="Year",
        y="Majority_Percent",
        color="Winner",
        title="Ruling Party Majority Timeline & Seat Percentage (1952 - 2021)",
        hover_data=["Seats", "Total_Seats"],
        color_discrete_map={
            "INC": "#1f77b4",
            "DMK": "#d62728",
            "AIADMK": "#2ca02c"
        }
    )
    
    fig_hist.update_layout(plot_bgcolor='#0E1117', paper_bgcolor='#0E1117', font_color='white')
    st.plotly_chart(fig_hist, width='stretch')
    
    with st.expander("View Historical Data Table"):
        st.dataframe(hist_df)
except:
    st.info("Historical data is compiling...")


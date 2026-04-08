import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.set_page_config(page_title="EC Deployment Tool", layout="wide")

st.title("🚀 EC Weekly Deployment Generator")
st.markdown("Use this tool to rank roadshows and set off-days without touching the master sheet.")

# --- 1. CONNECT TO YOUR SHEETS ---
# Replace these with your actual Sheet IDs
SALES_SHEET = "https://docs.google.com/spreadsheets/d/15VuRw2_UR6CR8XdkxypjZSQ3QR8Ft7DD5ugy9uAGTco/edit#gid=0"
ROADSHOW_SHEET = "https://docs.google.com/spreadsheets/d/1CKNsz4O11fTTB1kjb0y3GiIsRBww7ZxQmqpNK0AeLNw/edit#gid=1287774189"

conn = st.connection("gsheets", type=GSheetsConnection)

# Fetch Data
df_sales = conn.read(spreadsheet=SALES_SHEET)
df_roadshows = conn.read(spreadsheet=ROADSHOW_SHEET)

# --- 2. THE INTERFACE (The Tabs) ---
tab1, tab2, tab3 = st.tabs(["📊 Manager Input", "⚙️ Generate Schedule", "📋 Copy-Paste Export"])

with tab1:
    st.header("Step 1: Weekly Settings")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Rank the Roadshows")
        # Let manager rank locations (1 is best)
        # We use st.data_editor to let you type directly in the web app
        roadshow_input = st.data_editor(
            df_roadshows[['Location Name', 'Total HC Required']], 
            num_rows="dynamic",
            key="rs_rank"
        )
        roadshow_input['Manager_Rank'] = range(1, len(roadshow_input) + 1)

    with col2:
        st.subheader("Staff Off-Days")
        # Toggle who is NOT working this week
        off_days = st.multiselect("Select ECs who are OFF this week:", df_sales['EC Name'].tolist())

with tab2:
    if st.button("RUN DEPLOYMENT ALGORITHM"):
        st.success("Calculating best fit based on Sales Ranking & Seniority...")
        # Logic runs here (Algorithm we discussed previously)
        # For now, we display a preview
        st.info("Algorithm complete. Check the Export tab.")

with tab3:
    st.header("Step 3: Final Schedule")
    st.write("Highlight the table below and paste it into your Master Sheet.")
    # This is where the final table appears

import streamlit as st
import pandas as pd

st.set_page_config(page_title="EC Deployment Portal Pro", layout="wide")

# --- BASE URLS ---
SALES_BASE = "https://docs.google.com/spreadsheets/d/15VuRw2_UR6CR8XdkxypjZSQ3QR8Ft7DD5ugy9uAGTco/export?format=csv&gid="
ROADSHOW_URL = "https://docs.google.com/spreadsheets/d/1CKNsz4O11fTTB1kjb0y3GiIsRBww7ZxQmqpNK0AeLNw/export?format=csv&gid=1287774189"

st.title("🚀 EC Advanced Deployment System")

# --- TAB 1: DATA SETUP ---
tab1, tab2, tab3, tab4 = st.tabs(["🔗 Data Setup", "👤 Manpower Master", "📅 Off-Day Planner", "💎 Generate Schedule"])

with tab1:
    st.subheader("Google Sheet Connection")
    # This allows you to key in the GID yourself
    sales_gid = st.text_input("Enter the GID for this week's Sales Stats:", placeholder="e.g. 12345678")
    
    if sales_gid:
        try:
            df_sales = pd.read_csv(SALES_BASE + sales_gid)
            df_roadshows = pd.read_csv(ROADSHOW_URL)
            st.success("Data Connected Successfully!")
            
            st.divider()
            st.subheader("Roadshow Priority")
            # Using 'Theme' as location based on your previous logs
            rs_list = df_roadshows[['Theme']].dropna().drop_duplicates()
            rs_list['Priority'] = range(1, len(rs_list) + 1)
            rs_list['Required HC'] = 2
            ranked_rs = st.data_editor(rs_list, hide_index=True, key="rs_editor")
        except Exception as e:
            st.error(f"Error: {e}. Please check the GID and Sheet sharing settings.")
            st.stop()
    else:
        st.info("Waiting for Sales GID to be entered...")
        st.stop()

# --- TAB 2: MANPOWER MASTER ---
with tab2:
    st.subheader("Seniority & Compatibility")
    st.info("Mark your Seniors and select who works best together.")
    
    # Prepare a configuration table for ECs
    staff_names = df_sales['EC Name'].dropna().unique().tolist()
    
    if 'manpower_settings' not in st.session_state:
        st.session_state.manpower_settings = pd.DataFrame({
            'EC Name': staff_names,
            'Senior': False,
            'Partner': ["None"] * len(staff_names)
        })

    manpower_master = st.data_editor(
        st.session_state.manpower_settings,
        column_config={
            "Partner": st.column_config.SelectboxColumn(options=["None"] + staff_names)
        },
        hide_index=True,
        key="manpower_editor"
    )

# --- TAB 3: OFF-DAY PLANNER ---
with tab3:
    st.subheader("Upcoming Week Off-Day Selector")
    st.write("Planning for the following week? Select who is OFF for each day.")
    
    # Create an off-day grid
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    if 'off_day_grid' not in st.session_state:
        grid_data = {day: [False] * len(staff_names) for day in days}
        grid_data['EC Name'] = staff_names
        st.session_state.off_day_grid = pd.DataFrame(grid_data)

    off_days_final = st.data_editor(st.session_state.off_day_grid, hide_index=True, key="off_editor")

# --- TAB 4: GENERATOR ---
with tab4:
    if st.button("🚀 RUN SMART DEPLOYMENT"):
        # 1. Logic for daily generation (example for Monday)
        # In a full app, you might loop through all 7 days
        st.subheader("Generated Deployment (Preview: Monday)")
        
        # Filter available (Not OFF on Monday)
        is_off_mon = off_days_final[off_days_final['Mon'] == True]['EC Name'].tolist()
        available = df_sales[~df_sales['EC Name'].isin(is_off_mon)].copy()
        
        # Merge with Manpower Settings (Seniors/Partners)
        available = available.merge(manpower_master, on='EC Name')
        
        # Sort by SRR (Assume 'SRR' column exists)
        available['SRR'] = pd.to_numeric(available['SRR'].astype(str).str.replace('%', ''), errors='coerce').fillna(0)
        available = available.sort_values(by='SRR', ascending=False)
        
        pool = available.to_dict('records')
        deployment = []
        
        # 2. Assignment Algorithm
        for _, rs in ranked_rs.sort_values('Priority').iterrows():
            loc = rs['Theme']
            needed = int(rs['Required HC'])
            team = []
            
            # Priority 1: Senior + their Partner
            for i, p in enumerate(pool):
                if p['Senior'] and len(team) < needed:
                    team.append(pool.pop(i)['EC Name'])
                    # Check if partner is available in pool
                    partner_name = p['Partner']
                    for j, potential_partner in enumerate(pool):
                        if potential_partner['EC Name'] == partner_name and len(team) < needed:
                            team.append(pool.pop(j)['EC Name'])
                            break
                    break # Stop looking for seniors for this booth once one is found
            
            # Priority 2: Fill remaining slots with Top Ranked
            while len(team) < needed and len(pool) > 0:
                team.append(pool.pop(0)['EC Name'])
            
            deployment.append({"Location": loc, "Team": ", ".join(team)})
        
        # Results
        st.success("Deployment Optimized with Partnerships!")
        st.table(pd.DataFrame(deployment))

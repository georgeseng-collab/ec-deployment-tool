import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="Geniebook Deployment 2026", layout="wide")

# --- DATA SOURCE LINKS ---
SALES_BASE = "https://docs.google.com/spreadsheets/d/15VuRw2_UR6CR8XdkxypjZSQ3QR8Ft7DD5ugy9uAGTco/export?format=csv&gid="
# GID 1287774189 is the Cal Roadshow 2026 tab
ROADSHOW_URL = "https://docs.google.com/spreadsheets/d/1CKNsz4O11fTTB1kjb0y3GiIsRBww7ZxQmqpNK0AeLNw/export?format=csv&gid=1287774189"

def clean_currency(value):
    if pd.isna(value): return 0
    if isinstance(value, str):
        # Cleans $ and commas
        clean = re.sub(r'[^\d.]', '', value)
        return float(clean) if clean else 0
    return float(value)

@st.cache_data(ttl=60)
def load_data(sales_gid):
    s = pd.read_csv(SALES_BASE + str(sales_gid))
    r = pd.read_csv(ROADSHOW_URL)
    return s, r

st.title("🛡️ EC Weekly Deployment System")

# --- SIDEBAR INPUTS ---
st.sidebar.header("Step 1: Data Connection")
sales_gid = st.sidebar.text_input("Enter Sales Stats GID:", placeholder="e.g. 15729384")

# Specifically look for the week range string
target_week = st.sidebar.selectbox(
    "Select Planning Week:",
    options=[
        "13 Apr - 19 Apr",
        "20 Apr - 26 Apr",
        "27 Apr - 03 May",
        "04 May - 10 May"
    ]
)

if sales_gid:
    try:
        df_sales, df_roadshows = load_data(sales_gid)
        
        # --- TAB 1: SALES LEADERBOARD ---
        st.subheader(f"🏆 EC Sales Leaderboard (Week: {target_week})")
        df_sales['Overall_Value'] = df_sales['Overall'].apply(clean_currency)
        
        ec_leaderboard = df_sales[['EC Name', 'Overall', 'Overall_Value']].dropna(subset=['EC Name'])
        ec_leaderboard = ec_leaderboard.sort_values(by='Overall_Value', ascending=False).reset_index(drop=True)
        ec_leaderboard.index += 1
        
        st.dataframe(ec_leaderboard[['EC Name', 'Overall']], use_container_width=True)

        # --- ROADSHOW SEARCH LOGIC ---
        # Search for the week string (e.g. '13 Apr - 19 Apr') in the Master Calendar
        # We assume the date is in the first or second column
        mask = df_roadshows.astype(str).apply(lambda x: x.str.contains(target_week, case=False)).any(axis=1)
        active_week_data = df_roadshows[mask]

        if active_week_data.empty:
            st.warning(f"⚠️ No roadshows found in the Master for the week: {target_week}")
            st.stop()

        # Get list of venues (using 'Theme' column)
        active_venues = active_week_data['Theme'].dropna().unique().tolist()

        # --- INTERFACE TABS ---
        tab1, tab2, tab3 = st.tabs(["🎪 Roadshow Ranking", "👥 Manpower & Pairs", "📅 Generate Schedule"])

        with tab1:
            st.subheader("Assign Priority & Points")
            st.write(f"Detected **{len(active_venues)}** venues for this week.")
            
            rs_ranking_data = pd.DataFrame({
                "Venue": active_venues,
                "Points": [0.0] * len(active_venues),
                "Rank": [i+1 for i in range(len(active_venues))],
                "HC": [2] * len(active_venues)
            })
            
            manager_input = st.data_editor(rs_ranking_data, hide_index=True, key="rs_editor")

        with tab2:
            st.subheader("Seniority & Compatibility Tagging")
            staff_list = ec_leaderboard['EC Name'].tolist()
            
            if 'mp_settings' not in st.session_state:
                st.session_state.mp_settings = pd.DataFrame({
                    'EC Name': staff_list,
                    'Senior': False,
                    'Partner': ["None"] * len(staff_list)
                })

            # Manager selects Seniors and Partners here
            manpower_final = st.data_editor(
                st.session_state.mp_settings,
                column_config={"Partner": st.column_config.SelectboxColumn(options=["None"] + staff_list)},
                hide_index=True,
                key="mp_editor_v4"
            )

            st.divider()
            st.subheader("Off-Day Selector (Following Week)")
            days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            if 'off_grid' not in st.session_state:
                st.session_state.off_grid = pd.DataFrame({d: [False] * len(staff_list) for d in days})
                st.session_state.off_grid['EC Name'] = staff_list
            
            off_days_final = st.data_editor(st.session_state.off_grid, hide_index=True)

        with tab3:
            day_to_gen = st.selectbox("Select Day to Deploy:", days)
            
            if st.button(f"Generate {day_to_gen} Schedule"):
                # 1. Prepare Pool (Available staff for that day)
                is_off = off_days_final[off_days_final[day_to_gen] == True]['EC Name'].tolist()
                full_pool = ec_leaderboard.merge(manpower_final, on='EC Name')
                working_pool = full_pool[~full_pool['EC Name'].isin(is_off)].to_dict('records')
                
                # 2. Sort Roadshows by Manager Points
                sorted_rs = manager_input.sort_values(by=['Points', 'Rank'], ascending=[False, True])
                
                deployment = []
                for _, rs in sorted_rs.iterrows():
                    booth_team = []
                    needed = int(rs['HC'])
                    
                    while len(booth_team) < needed and len(working_pool) > 0:
                        p = working_pool.pop(0)
                        booth_team.append(p['EC Name'])
                        
                        # Partnership Logic: If they have a partner, grab them next
                        partner = p['Partner']
                        if partner != "None" and len(booth_team) < needed:
                            for idx, cand in enumerate(working_pool):
                                if cand['EC Name'] == partner:
                                    booth_team.append(working_pool.pop(idx)['EC Name'])
                                    break
                    
                    deployment.append({
                        "Venue": rs['Venue'],
                        "Points": rs['Points'],
                        "Staff Assigned": ", ".join(booth_team)
                    })
                
                st.success(f"Successfully generated {day_to_gen} deployment!")
                st.table(pd.DataFrame(deployment))

    except Exception as e:
        st.error(f"Waiting for GID... Technical Error: {e}")
else:
    st.info("👈 Enter the GID from your Sales Ranking tab in the sidebar to load your data.")

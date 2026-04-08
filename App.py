import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="Geniebook Deployment - Date Search", layout="wide")

# --- DATA SOURCE LINKS ---
SALES_BASE = "https://docs.google.com/spreadsheets/d/15VuRw2_UR6CR8XdkxypjZSQ3QR8Ft7DD5ugy9uAGTco/export?format=csv&gid="
ROADSHOW_URL = "https://docs.google.com/spreadsheets/d/1CKNsz4O11fTTB1kjb0y3GiIsRBww7ZxQmqpNK0AeLNw/export?format=csv&gid=1287774189"

def clean_currency(value):
    if pd.isna(value): return 0
    if isinstance(value, str):
        clean = re.sub(r'[^\d.]', '', value)
        return float(clean) if clean else 0
    return float(value)

@st.cache_data(ttl=60)
def load_data(sales_gid):
    s = pd.read_csv(SALES_BASE + str(sales_gid))
    r = pd.read_csv(ROADSHOW_URL)
    return s, r

st.title("🛡️ EC Weekly Deployment System")

# --- STEP 1: GID & DATE SEARCH ---
st.sidebar.header("Data Connection")
sales_gid = st.sidebar.text_input("1. Enter Sales Stats GID:", placeholder="e.g. 15729384")
target_week = st.sidebar.text_input("2. Enter Week to Search (Date):", placeholder="e.g. 13 Apr - 19 Apr")

if sales_gid and target_week:
    try:
        df_sales, df_roadshows = load_data(sales_gid)
        
        # --- SHOW EC RANKING IMMEDIATELY ---
        st.subheader(f"🏆 EC Sales Leaderboard (Stats GID: {sales_gid})")
        df_sales['Overall_Value'] = df_sales['Overall'].apply(clean_currency)
        ec_leaderboard = df_sales[['EC Name', 'Overall', 'Overall_Value']].dropna(subset=['EC Name'])
        ec_leaderboard = ec_leaderboard.sort_values(by='Overall_Value', ascending=False).reset_index(drop=True)
        ec_leaderboard.index += 1
        st.dataframe(ec_leaderboard[['EC Name', 'Overall']], use_container_width=True)

        # --- ROADSHOW DATE FILTERING LOGIC ---
        # We search every row in the Master Cal to see if the 'target_week' string exists anywhere in that row
        mask = df_roadshows.apply(lambda row: row.astype(str).str.contains(target_week, case=False).any(), axis=1)
        active_week_rs = df_roadshows[mask]

        if active_week_rs.empty:
            st.warning(f"⚠️ No roadshows found for date: '{target_week}'. Please check the exact wording in your Google Sheet.")
            st.stop()

        # Extract Venue names (using the 'Theme' column from your previous logs)
        active_venues = active_week_rs['Theme'].dropna().unique().tolist()

        # --- TABS ---
        tab1, tab2, tab3 = st.tabs(["🎪 Roadshow Ranking", "👥 Manpower & Pairs", "📅 Generate Schedule"])

        with tab1:
            st.subheader(f"Priority for Week: {target_week}")
            st.write(f"Found **{len(active_venues)}** venues for this date.")
            
            rs_data = pd.DataFrame({
                "Venue": active_venues,
                "Ranking Points": [0.0] * len(active_venues),
                "Priority": [0] * len(active_venues),
                "Staff Needed": [2] * len(active_venues)
            })
            
            manager_rs_ranked = st.data_editor(
                rs_data, 
                hide_index=True,
                column_config={
                    "Priority": st.column_config.NumberColumn("Rank (1=Best)", min_value=1),
                    "Ranking Points": st.column_config.NumberColumn("Points")
                },
                key="rs_ranking_editor"
            )

        with tab2:
            st.subheader("EM Tagging: Seniority & Partners")
            staff_list = ec_leaderboard['EC Name'].tolist()
            
            if 'mp_df' not in st.session_state:
                st.session_state.mp_df = pd.DataFrame({
                    'EC Name': staff_list,
                    'Senior': False,
                    'Partner': ["None"] * len(staff_list)
                })

            manpower_settings = st.data_editor(
                st.session_state.mp_df,
                column_config={"Partner": st.column_config.SelectboxColumn(options=["None"] + staff_list)},
                hide_index=True,
                key="mp_editor_final"
            )

            st.divider()
            st.subheader("Upcoming Week Off-Days")
            day_cols = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            if 'off_grid' not in st.session_state:
                st.session_state.off_grid = pd.DataFrame({day: [False] * len(staff_list) for day in day_cols})
                st.session_state.off_grid['EC Name'] = staff_list

            off_days_final = st.data_editor(st.session_state.off_grid, hide_index=True)

        with tab3:
            gen_day = st.selectbox("Select Day to Generate:", day_cols)
            if st.button(f"Generate Deployment for {gen_day}"):
                
                # 1. Prepare Pool
                is_off = off_days_final[off_days_final[gen_day] == True]['EC Name'].tolist()
                pool_df = ec_leaderboard.merge(manpower_settings, on='EC Name')
                pool = pool_df[~pool_df['EC Name'].isin(is_off)].to_dict('records')
                
                # 2. Sort Roadshows
                sorted_rs = manager_rs_ranked[manager_rs_ranked['Priority'] > 0].sort_values('Points', ascending=False)
                
                results = []
                for _, rs in sorted_rs.iterrows():
                    team = []
                    needed = int(rs['Staff Needed'])
                    
                    while len(team) < needed and len(pool) > 0:
                        p = pool.pop(0)
                        team.append(p['EC Name'])
                        
                        # Partner Check
                        if p['Partner'] != "None" and len(team) < needed:
                            for i, cand in enumerate(pool):
                                if cand['EC Name'] == p['Partner']:
                                    team.append(pool.pop(i)['EC Name'])
                                    break
                    
                    results.append({"Venue": rs['Venue'], "Points": rs['Ranking Points'], "Staff": ", ".join(team)})
                
                st.success(f"Final Deployment for {gen_day}")
                st.table(pd.DataFrame(results))

    except Exception as e:
        st.error(f"Error: {e}")
else:
    st.info("👈 Enter the **Stats GID** and the **Target Date/Week** (e.g. 13 Apr - 19 Apr) in the sidebar to begin.")

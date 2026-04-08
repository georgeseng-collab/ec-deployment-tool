import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="Geniebook Deployment 2026", layout="wide")

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

# --- STEP 1: GID INPUT ---
st.sidebar.header("1. Performance Stats")
sales_gid = st.sidebar.text_input("Enter Sales Stats GID:", placeholder="e.g. 15729384")

if sales_gid:
    try:
        df_sales, df_roadshows = load_data(sales_gid)
        
        # --- SALES LEADERBOARD ---
        st.subheader("🏆 EC Sales Leaderboard")
        df_sales['Overall_Value'] = df_sales['Overall'].apply(clean_currency)
        ec_leaderboard = df_sales[['EC Name', 'Overall', 'Overall_Value']].dropna(subset=['EC Name'])
        ec_leaderboard = ec_leaderboard.sort_values(by='Overall_Value', ascending=False).reset_index(drop=True)
        ec_leaderboard.index += 1
        st.dataframe(ec_leaderboard[['EC Name', 'Overall']], use_container_width=True)

        st.divider()

        # --- SMART DATE DETECTION ---
        st.sidebar.header("2. Roadshow Calendar")
        # Scan the first few columns of the Roadshow Master for anything that looks like a date or week
        # We look at the first 3 columns where dates are usually kept
        potential_dates = df_roadshows.iloc[:, 0:3].stack().dropna().unique().tolist()
        # Filter list to only show strings that look like weeks/dates
        date_options = [str(d) for d in potential_dates if len(str(d)) > 5] 
        
        selected_date = st.sidebar.selectbox("Select the Planning Week:", options=["Choose a date..."] + date_options)

        if selected_date != "Choose a date...":
            # Filter the Master Sheet for the selected week
            mask = df_roadshows.apply(lambda row: row.astype(str).str.contains(re.escape(selected_date), case=False).any(), axis=1)
            active_week_rs = df_roadshows[mask]
            
            # Source Venues from 'Theme' column
            active_venues = active_week_rs['Theme'].dropna().unique().tolist()

            if not active_venues:
                st.warning("⚠️ Date found, but no 'Theme' (Venue) was listed on that row.")
                st.stop()

            # --- TABS ---
            tab1, tab2, tab3 = st.tabs(["🎪 Roadshow Ranking", "👥 Manpower & Pairs", "📅 Generate Schedule"])

            with tab1:
                st.subheader(f"Priority & Points for: {selected_date}")
                rs_data = pd.DataFrame({
                    "Venue": active_venues,
                    "Ranking Points": [0.0] * len(active_venues),
                    "Priority": [i+1 for i in range(len(active_venues))],
                    "Staff Needed": [2] * len(active_venues)
                })
                
                manager_rs_ranked = st.data_editor(rs_data, hide_index=True)

            with tab2:
                st.subheader("Manpower & Partnerships")
                staff_list = ec_leaderboard['EC Name'].tolist()
                
                # EM Tagging Session State
                if 'mp_config' not in st.session_state:
                    st.session_state.mp_config = pd.DataFrame({
                        'EC Name': staff_list,
                        'Senior': False,
                        'Partner': ["None"] * len(staff_list)
                    })
                
                manpower_settings = st.data_editor(
                    st.session_state.mp_config,
                    column_config={"Partner": st.column_config.SelectboxColumn(options=["None"] + staff_list)},
                    hide_index=True,
                    key="mp_editor_v3"
                )

                st.divider()
                st.subheader("Upcoming Off-Days")
                days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
                if 'off_grid_v3' not in st.session_state:
                    st.session_state.off_grid_v3 = pd.DataFrame({day: [False] * len(staff_list) for day in days})
                    st.session_state.off_grid_v3['EC Name'] = staff_list
                
                off_days_final = st.data_editor(st.session_state.off_grid_v3, hide_index=True)

            with tab3:
                gen_day = st.selectbox("Select Day to Generate:", days)
                if st.button(f"Generate {gen_day} Deployment"):
                    # Filtering Logic
                    is_off = off_days_final[off_days_final[gen_day] == True]['EC Name'].tolist()
                    pool_df = ec_leaderboard.merge(manpower_settings, on='EC Name')
                    pool = pool_df[~pool_df['EC Name'].isin(is_off)].to_dict('records')
                    
                    # Sort Roadshows by Manager Points
                    sorted_rs = manager_rs_ranked.sort_values(by=['Ranking Points', 'Priority'], ascending=[False, True])
                    
                    results = []
                    for _, rs in sorted_rs.iterrows():
                        team = []
                        needed = int(rs['Staff Needed'])
                        
                        while len(team) < needed and len(pool) > 0:
                            p = pool.pop(0)
                            team.append(p['EC Name'])
                            
                            # EM Partnership Logic
                            partner_name = p['Partner']
                            if partner_name != "None" and len(team) < needed:
                                for i, cand in enumerate(pool):
                                    if cand['EC Name'] == partner_name:
                                        team.append(pool.pop(i)['EC Name'])
                                        break
                        
                        results.append({"Venue": rs['Venue'], "Points": rs['Ranking Points'], "Staff": ", ".join(team)})
                    
                    st.table(pd.DataFrame(results))

    except Exception as e:
        st.error(f"Error: {e}")
else:
    st.info("👈 Please enter the Stats GID in the sidebar to load your team.")

import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="EC Deployment - Compatibility Mode", layout="wide")

# --- BASE URLS ---
SALES_BASE = "https://docs.google.com/spreadsheets/d/15VuRw2_UR6CR8XdkxypjZSQ3QR8Ft7DD5ugy9uAGTco/export?format=csv&gid="
ROADSHOW_URL = "https://docs.google.com/spreadsheets/d/1CKNsz4O11fTTB1kjb0y3GiIsRBww7ZxQmqpNK0AeLNw/export?format=csv&gid=1287774189"

st.title("🚀 EC Deployment & Compatibility System")

def clean_currency(value):
    if isinstance(value, str):
        return float(re.sub(r'[^\d.]', '', value))
    return value

@st.cache_data(ttl=60)
def load_data(gid):
    s = pd.read_csv(SALES_BASE + str(gid))
    r = pd.read_csv(ROADSHOW_URL)
    return s, r

# --- SIDEBAR: GID INPUT ---
sales_gid = st.sidebar.text_input("Step 1: Enter Sales GID:", placeholder="Look at URL #gid=...")

if not sales_gid:
    st.info("👋 Welcome! Please enter the GID from your Sales Ranking tab to start.")
    st.stop()

try:
    df_sales, df_roadshows = load_data(sales_gid)
    staff_list = df_sales['EC Name'].dropna().unique().tolist()

    # --- TABBED INTERFACE ---
    tab1, tab2, tab3, tab4 = st.tabs(["🎪 Roadshow Rank", "👥 Manpower & Pairs", "📅 Off-Day Planner", "💎 Generate"])

    with tab1:
        st.subheader("🎪 Roadshow Ranking & Points")
        st.write("Assign Points to locations. Highest points = Best Roadshow.")
        rs_list = df_roadshows[['Theme']].dropna().drop_duplicates()
        rs_list['Points'] = 0.0
        rs_list['HC'] = 2
        
        manager_rs = st.data_editor(
            rs_list, 
            hide_index=True,
            column_config={
                "Theme": "Roadshow Location",
                "Points": st.column_config.NumberColumn("Ranking Points", help="Higher = Better"),
                "HC": st.column_config.NumberColumn("Staff Needed", min_value=1)
            },
            key="rs_editor"
        )

    with tab2:
        st.subheader("👥 Manpower Compatibility (EM Tagging)")
        st.info("Tag Seniors and pair them with their 'Best Compatibility Partner'.")
        
        # PERSISTENT SESSION STATE FOR MANPOWER
        if 'manpower_df' not in st.session_state:
            st.session_state.manpower_df = pd.DataFrame({
                'EC Name': staff_list,
                'Senior': False,
                'Partner': ["None"] * len(staff_list)
            })

        manpower_master = st.data_editor(
            st.session_state.manpower_df,
            column_config={
                "Partner": st.column_config.SelectboxColumn(options=["None"] + staff_list)
            },
            hide_index=True,
            key="mp_editor"
        )

    with tab3:
        st.subheader("📅 Weekly Off-Day Selector")
        days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        if 'off_grid' not in st.session_state:
            grid_init = {day: [False] * len(staff_list) for day in days}
            grid_init['EC Name'] = staff_list
            st.session_state.off_grid = pd.DataFrame(grid_init)

        off_days_final = st.data_editor(st.session_state.off_grid, hide_index=True, key="off_editor")

    with tab4:
        # SELECT DAY TO GENERATE
        gen_day = st.selectbox("Select Day to Generate Schedule:", days)
        
        if st.button(f"🚀 GENERATE {gen_day.upper()} DEPLOYMENT"):
            # 1. CLEAN & RANK STAFF BY 'OVERALL'
            df_sales['Overall_Clean'] = df_sales['Overall'].apply(clean_currency)
            staff_ranked = df_sales.merge(manpower_master, on='EC Name')
            staff_ranked = staff_ranked.sort_values(by='Overall_Clean', ascending=False)
            
            # 2. FILTER OUT OFF-DAYS
            is_off = off_days_final[off_days_final[gen_day] == True]['EC Name'].tolist()
            working_pool = staff_ranked[~staff_ranked['EC Name'].isin(is_off)].to_dict('records')
            
            # 3. SORT ROADSHOWS BY POINTS
            sorted_rs = manager_rs[manager_rs['Points'] > 0].sort_values(by='Points', ascending=False)
            
            final_deployment = []
            
            for _, rs in sorted_rs.iterrows():
                loc = rs['Theme']
                hc = int(rs['HC'])
                assigned_team = []
                
                # WHILE BOOTH NEEDS PEOPLE AND WE HAVE STAFF
                while len(assigned_team) < hc and len(working_pool) > 0:
                    person = working_pool.pop(0)
                    assigned_team.append(person['EC Name'])
                    
                    # --- COMPATIBILITY PAIRING LOGIC ---
                    partner_name = person['Partner']
                    if partner_name != "None" and len(assigned_team) < hc:
                        # Check if partner is in the pool
                        for idx, candidate in enumerate(working_pool):
                            if candidate['EC Name'] == partner_name:
                                assigned_team.append(working_pool.pop(idx)['EC Name'])
                                break
                
                final_deployment.append({
                    "Location": loc,
                    "Points": rs['Points'],
                    "Staffing": ", ".join(assigned_team)
                })

            st.success(f"Deployment for {gen_day} Completed!")
            st.table(pd.DataFrame(final_deployment))

except Exception as e:
    st.error(f"Waiting for Data... Error: {e}")

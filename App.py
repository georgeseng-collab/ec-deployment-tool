import streamlit as st
import pandas as pd

st.set_page_config(page_title="EC Deployment Portal", layout="wide")

# --- DATA BASE URLS ---
# We will append the GID dynamically based on the week selected
SALES_BASE = "https://docs.google.com/spreadsheets/d/15VuRw2_UR6CR8XdkxypjZSQ3QR8Ft7DD5ugy9uAGTco/export?format=csv&gid="
ROADSHOW_URL = "https://docs.google.com/spreadsheets/d/1CKNsz4O11fTTB1kjb0y3GiIsRBww7ZxQmqpNK0AeLNw/export?format=csv&gid=1287774189"

# --- CONFIGURATION: MAP YOUR GIDS HERE ---
# REPLACE THE NUMBERS BELOW with the actual GIDs from your browser URL for each tab
WEEKS_CONFIG = {
    "13 Apr - 19 Apr (using 23 Mar - 05 Apr stats)": "ENTER_GID_FOR_MAR23_TAB_HERE",
    "20 Apr - 26 Apr (using 30 Mar - 12 Apr stats)": "ENTER_GID_FOR_MAR30_TAB_HERE"
}

st.title("🚀 EC Weekly Deployment System")

def load_data(sales_gid):
    s = pd.read_csv(SALES_BASE + str(sales_gid))
    r = pd.read_csv(ROADSHOW_URL)
    return s, r

# --- STEP 1: SELECT DEPLOYMENT WEEK ---
st.subheader("🗓️ Select Deployment Week")
selected_week = st.selectbox("Which week are you planning for?", options=list(WEEKS_CONFIG.keys()))
current_gid = WEEKS_CONFIG[selected_week]

try:
    if current_gid == "ENTER_GID_FOR_MAR23_TAB_HERE":
        st.warning("⚠️ You need to update the GID numbers in your app.py code on GitHub to make this work.")
        st.stop()

    df_sales, df_roadshows = load_data(current_gid)

    # --- MATCHING COLUMNS ---
    name_col = "EC Name"
    srr_col = "SRR"
    loc_col = "Theme" 

    tab1, tab2 = st.tabs(["⚙️ Manager Inputs", "📅 Generated Schedule"])

    with tab1:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("1. Roadshow Settings")
            rs_list = df_roadshows[[loc_col]].dropna().drop_duplicates()
            rs_list['Priority'] = range(1, len(rs_list) + 1)
            rs_list['Required HC'] = 2 
            ranked_df = st.data_editor(rs_list, hide_index=True)
        
        with col2:
            st.subheader("2. Weekly Off-Days")
            staff_list = df_sales[name_col].dropna().unique().tolist()
            off_staff = st.multiselect("Who is OFF this week?", options=staff_list)

    with tab2:
        if st.button("🚀 GENERATE DEPLOYMENT"):
            # 1. Prepare Staff Pool from the SELECTED STATS TAB
            working_staff = df_sales[~df_sales[name_col].isin(off_staff)].copy()
            
            # Clean SRR column
            working_staff[srr_col] = pd.to_numeric(working_staff[srr_col].astype(str).str.replace('%', ''), errors='coerce').fillna(0)
            working_staff = working_staff.sort_values(by=srr_col, ascending=False)
            
            # 2. Logic: Top 5 in the ranking are "Seniors"
            pool = working_staff.to_dict('records')
            for i, p in enumerate(pool):
                p['is_senior'] = True if i < 5 else False
            
            # 3. Assignment
            final_schedule = []
            for _, rs in ranked_df.sort_values('Priority').iterrows():
                location = rs[loc_col]
                needed = int(rs['Required HC'])
                assigned = []
                
                # Rule A: Assign 1 Senior first
                for i, person in enumerate(pool):
                    if person['is_senior']:
                        assigned.append(pool.pop(i)[name_col])
                        break
                
                # Rule B: Fill rest
                while len(assigned) < needed and len(pool) > 0:
                    assigned.append(pool.pop(0)[name_col])
                
                final_schedule.append({
                    "Location": location,
                    "Total HC": len(assigned),
                    "Team Members": ", ".join(assigned)
                })
            
            st.success(f"Deployment Generated using stats from: {selected_week}")
            result_df = pd.DataFrame(final_schedule)
            st.table(result_df)

except Exception as e:
    st.error(f"Waiting for correct GID selection... Error: {e}")

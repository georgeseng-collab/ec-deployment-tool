import streamlit as st
import pandas as pd

st.set_page_config(page_title="EC Deployment Portal", layout="wide")

# --- DATA LINKS ---
SALES_URL = "https://docs.google.com/spreadsheets/d/15VuRw2_UR6CR8XdkxypjZSQ3QR8Ft7DD5ugy9uAGTco/export?format=csv"
ROADSHOW_URL = "https://docs.google.com/spreadsheets/d/1CKNsz4O11fTTB1kjb0y3GiIsRBww7ZxQmqpNK0AeLNw/export?format=csv&gid=1287774189"

st.title("🚀 EC Weekly Deployment System")

@st.cache_data(ttl=60)
def load_data():
    s = pd.read_csv(SALES_URL)
    r = pd.read_csv(ROADSHOW_URL)
    return s, r

try:
    df_sales, df_roadshows = load_data()

    # --- MATCHING COLUMNS FROM YOUR LOGS ---
    # Sales Sheet
    name_col = "EC Name"
    srr_col = "SRR"
    
    # Roadshow Sheet (Assuming 'Theme' holds the Mall/Location name)
    # If the mall name is in a different column, change "Theme" below.
    loc_col = "Theme" 

    # --- INTERFACE ---
    tab1, tab2 = st.tabs(["⚙️ Manager Inputs", "📅 Generated Schedule"])

    with tab1:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("1. Roadshow Settings")
            st.write("Set the Priority (1 = Top) and how many staff (HC) are needed.")
            
            # Prepare a clean list of unique Roadshows
            rs_list = df_roadshows[[loc_col]].dropna().drop_duplicates()
            rs_list['Priority'] = range(1, len(rs_list) + 1)
            rs_list['Required HC'] = 2 # Defaulting to 2 staff per booth
            
            # Allow manager to edit HC and Priority
            ranked_df = st.data_editor(
                rs_list, 
                hide_index=True,
                column_config={
                    "Required HC": st.column_config.NumberColumn(min_value=1, max_value=10),
                    "Priority": st.column_config.NumberColumn(min_value=1)
                }
            )
        
        with col2:
            st.subheader("2. Weekly Off-Days")
            staff_list = df_sales[name_col].dropna().unique().tolist()
            off_staff = st.multiselect("Who is NOT working this week?", options=staff_list)

    with tab2:
        if st.button("🚀 GENERATE DEPLOYMENT"):
            # 1. Prepare Staff Pool
            # Remove off-days and sort by SRR points
            working_staff = df_sales[~df_sales[name_col].isin(off_staff)].copy()
            
            # Clean SRR column (remove % if any and turn to number)
            working_staff[srr_col] = pd.to_numeric(working_staff[srr_col].astype(str).str.replace('%', ''), errors='coerce').fillna(0)
            working_staff = working_staff.sort_values(by=srr_col, ascending=False)
            
            # 2. Logic: Top 5 in the list are "Seniors"
            pool = working_staff.to_dict('records')
            for i, p in enumerate(pool):
                p['is_senior'] = True if i < 5 else False
            
            # 3. Assignment
            final_schedule = []
            
            for _, rs in ranked_df.sort_values('Priority').iterrows():
                location = rs[loc_col]
                needed = int(rs['Required HC'])
                assigned = []
                
                # Rule A: Try to give 1 Senior first
                for i, person in enumerate(pool):
                    if person['is_senior']:
                        assigned.append(pool.pop(i)[name_col])
                        break
                
                # Rule B: Fill remaining with top available
                while len(assigned) < needed and len(pool) > 0:
                    assigned.append(pool.pop(0)[name_col])
                
                final_schedule.append({
                    "Location": location,
                    "Total HC": len(assigned),
                    "Team Members": ", ".join(assigned)
                })
            
            # --- SHOW RESULTS ---
            result_df = pd.DataFrame(final_schedule)
            st.success("Deployment Generated!")
            st.dataframe(result_df, use_container_width=True, hide_index=True)
            
            # Export
            st.download_button("Download CSV", result_df.to_csv(index=False), "schedule.csv")

except Exception as e:
    st.error(f"Waiting for data... Error: {e}")

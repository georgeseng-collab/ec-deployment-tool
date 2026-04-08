import streamlit as st
import pandas as pd

st.set_page_config(page_title="EC Deployment App", layout="wide")

# --- DATA SOURCE LINKS ---
SALES_URL = "https://docs.google.com/spreadsheets/d/15VuRw2_UR6CR8XdkxypjZSQ3QR8Ft7DD5ugy9uAGTco/export?format=csv"
# Note: gid=1287774189 is your "Roadshow Master" sheet tab
ROADSHOW_URL = "https://docs.google.com/spreadsheets/d/1CKNsz4O11fTTB1kjb0y3GiIsRBww7ZxQmqpNK0AeLNw/export?format=csv&gid=1287774189"

st.title("🚀 EC Weekly Deployment System")

@st.cache_data(ttl=60)
def load_data(url):
    return pd.read_csv(url)

try:
    df_sales = load_data(SALES_URL)
    df_roadshows = load_data(ROADSHOW_URL)

    # --- AUTO-DETECT COLUMNS ---
    # This helps find columns even if they have slightly different names
    def find_col(df, keywords):
        for col in df.columns:
            if any(key.lower() in str(col).lower() for key in keywords):
                return col
        return None

    # Finding our columns
    name_col = find_col(df_sales, ["EC Name", "Staff", "Name"])
    points_col = find_col(df_sales, ["SRR", "Points", "Score", "Rank"])
    loc_col = find_col(df_roadshows, ["Location", "Roadshow", "Venue"])
    hc_col = find_col(df_roadshows, ["HC", "Headcount", "Required", "Total"])

    # --- DEBUG SECTION (Only shows if something is missing) ---
    if not all([name_col, points_col, loc_col, hc_col]):
        st.warning("⚠️ Some columns could not be found automatically.")
        with st.expander("Click here to see actual Column Names in your Sheets"):
            st.write("**Sales Sheet Columns:**", df_sales.columns.tolist())
            st.write("**Roadshow Sheet Columns:**", df_roadshows.columns.tolist())
        st.stop()

    # --- INTERFACE ---
    tab1, tab2 = st.tabs(["⚙️ Manager Inputs", "📅 Generated Schedule"])

    with tab1:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("1. Roadshow Priority")
            # Create a clean input table
            rs_input = df_roadshows[[loc_col, hc_col]].dropna().copy()
            rs_input['Rank'] = range(1, len(rs_input) + 1)
            ranked_df = st.data_editor(rs_input, hide_index=True)
        
        with col2:
            st.subheader("2. Weekly Off-Days")
            off_staff = st.multiselect("Select ECs who are OFF:", options=df_sales[name_col].dropna().unique())

    with tab2:
        if st.button("GENERATE DEPLOYMENT"):
            # 1. Prepare available pool
            available = df_sales[~df_sales[name_col].isin(off_staff)].copy()
            available = available.sort_values(by=points_col, ascending=False)
            
            # 2. Logic: Top 5 are Seniors
            available['Is_Senior'] = False
            available.iloc[:5, available.columns.get_loc('Is_Senior')] = True
            
            pool = available.to_dict('records')
            deployment = []
            
            # 3. Match
            for _, rs in ranked_df.sort_values('Rank').iterrows():
                needed = int(rs[hc_col])
                team = []
                
                # Assign 1 Senior
                for i, p in enumerate(pool):
                    if p['Is_Senior']:
                        team.append(pool.pop(i)[name_col])
                        break
                
                # Fill rest
                while len(team) < needed and len(pool) > 0:
                    team.append(pool.pop(0)[name_col])
                
                deployment.append({"Location": rs[loc_col], "Team": ", ".join(team)})
            
            st.success("Schedule Ready!")
            st.table(pd.DataFrame(deployment))

except Exception as e:
    st.error(f"Error loading data: {e}")
    st.info("Check that your Google Sheets are Shared to 'Anyone with the link can view'.")

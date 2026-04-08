import streamlit as st
import pandas as pd

# --- PAGE CONFIG ---
st.set_page_config(page_title="EC Deployment Portal", layout="wide")

# --- DATA SOURCE LINKS (CSV EXPORT MODE) ---
# These links tell Google to give us raw data, which avoids the HTTP permission errors.
SALES_URL = "https://docs.google.com/spreadsheets/d/15VuRw2_UR6CR8XdkxypjZSQ3QR8Ft7DD5ugy9uAGTco/export?format=csv"
ROADSHOW_URL = "https://docs.google.com/spreadsheets/d/1CKNsz4O11fTTB1kjb0y3GiIsRBww7ZxQmqpNK0AeLNw/export?format=csv&gid=1287774189"

st.title("🚀 EC Weekly Deployment System")
st.markdown("Automated scheduling based on Sales Ranking, Seniority, and Manager Priority.")

# --- DATA LOADING ---
@st.cache_data(ttl=600) # Refresh data every 10 minutes
def load_data():
    sales = pd.read_csv(SALES_URL)
    roads = pd.read_csv(ROADSHOW_URL)
    return sales, roads

try:
    df_sales, df_roadshows = load_data()
    
    # --- INTERFACE TABS ---
    tab1, tab2 = st.tabs(["⚙️ Manager Inputs", "📅 Generated Schedule"])

    with tab1:
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.subheader("1. Roadshow Priority")
            st.info("Edit the 'Priority' column. 1 = Top Location.")
            # We assume your sheet has a column named 'Location'
            # If the column name is different, change 'Location' below
            rs_display = df_roadshows[['Location', 'Total HC Required']].copy()
            rs_display['Priority'] = range(1, len(rs_display) + 1)
            
            ranked_rs = st.data_editor(
                rs_display,
                column_config={
                    "Priority": st.column_config.NumberColumn("Rank", min_value=1, step=1)
                },
                hide_index=True,
                key="rs_editor"
            )

        with col2:
            st.subheader("2. Weekly Off-Days")
            # We assume your Sales sheet has a column named 'EC Name'
            all_staff = df_sales['EC Name'].tolist()
            off_staff = st.multiselect("Who is OFF this week?", options=all_staff)

    with tab2:
        if st.button("🚀 GENERATE DEPLOYMENT"):
            # --- START LOGIC ---
            
            # 1. Filter Available Staff
            available = df_sales[~df_sales['EC Name'].isin(off_staff)].copy()
            
            # 2. Sort by Points (Assuming column name is 'SRR Points')
            # If your column is named 'Ranking' or 'Total Sales', change 'SRR Points' below
            available = available.sort_values(by='SRR Points', ascending=False)
            
            # 3. Identify Seniors (Example: Top 30% of working staff)
            num_seniors = max(1, int(len(available) * 0.3))
            available['Is_Senior'] = False
            available.iloc[:num_seniors, available.columns.get_loc('Is_Senior')] = True
            
            # 4. Matching Algorithm
            staff_pool = available.to_dict('records')
            deployment_results = []
            
            # Sort roadshows by manager's priority
            final_rs_order = ranked_rs.sort_values('Priority')
            
            for _, roadshow in final_rs_order.iterrows():
                loc = roadshow['Location']
                hc = int(roadshow['Total HC Required'])
                team = []
                
                # Assign 1 Senior first
                for i, person in enumerate(staff_pool):
                    if person['Is_Senior']:
                        team.append(staff_pool.pop(i)['EC Name'])
                        break
                
                # Fill remaining slots with next best available
                while len(team) < hc and len(staff_pool) > 0:
                    team.append(staff_pool.pop(0)['EC Name'])
                
                deployment_results.append({
                    "Location": loc,
                    "Total HC": hc,
                    "Deployed Team": ", ".join(team)
                })

            # --- DISPLAY RESULTS ---
            final_df = pd.DataFrame(deployment_results)
            st.success("Deployment Optimized!")
            st.dataframe(final_df, use_container_width=True, hide_index=True)
            
            # CSV Download for easy Copy-Paste
            csv = final_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                "📥 Download Schedule for Excel",
                csv,
                "weekly_deployment.csv",
                "text/csv",
                key='download-csv'
            )

except Exception as e:
    st.error("⚠️ Connection Failed")
    st.write("Ensure your Google Sheets are Shared as 'Anyone with the link can view'.")
    st.write(f"Technical Error: {e}")

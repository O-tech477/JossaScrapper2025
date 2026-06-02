import streamlit as st
import sqlite3
import pandas as pd
import os

from pdf_reading import get_available_branches, get_iit_branch_seat_counts

#Basic streamlit setup 
st.set_page_config(
    page_title="Jossa Helper",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

#DB names for website n report db. 
DB_NAME = "database.db"
BRANCH_CACHE_DB = "iit_branch_seats.db"


def get_db_connection():
    """Establishes connection to the local SQLite database."""
    conn = sqlite3.connect(DB_NAME)
    return conn

@st.cache_data
def load_dimension_options():
    """Fetch dropdown options dynamically from Dimension tables to prevent app lag."""
    conn = get_db_connection()
    categories = pd.read_sql("SELECT cat_value FROM Dim_Category ORDER BY cat_value", conn)['cat_value'].tolist()
    genders = pd.read_sql("SELECT gender_value FROM Dim_Gender ORDER BY gender_value", conn)['gender_value'].tolist()
    quotas = pd.read_sql("SELECT quota_value FROM Dim_Quota ORDER BY quota_value", conn)['quota_value'].tolist()
    types = pd.read_sql("SELECT insti_type FROM Dim_InstiType ORDER BY insti_type", conn)['insti_type'].tolist()
    institutes = pd.read_sql("SELECT insti_value FROM Dim_InstiName ORDER BY insti_value", conn)['insti_value'].tolist()
    rounds = pd.read_sql("SELECT DISTINCT round FROM FactsTable ORDER BY round", conn)['round'].tolist()
    conn.close()
    return categories, genders, quotas, types, institutes, rounds


@st.cache_data
def load_branch_options():
    return get_available_branches()


@st.cache_data
def load_branch_seat_counts(branch_name, cache_signature):
    return get_iit_branch_seat_counts(branch_name, db_path=BRANCH_CACHE_DB)

# Load metadata filters
try:
    categories, genders, quotas, insti_types, all_institutes, rounds = load_dimension_options()
    branch_options = load_branch_options()
except Exception as e:
    st.error(f"Dev error: {e}")
    st.stop()


with st.sidebar:
    st.title("JoSAA Wiki")
    st.markdown("---")
    st.subheader("📁 JIC 2025 Report")
    
    
    current_dir_files = os.listdir('.')
    pdf_files = [f for f in current_dir_files if f.endswith('.pdf')]
    
    if pdf_files:
        for pdf in pdf_files:
            with open(pdf, "rb") as f:
                st.download_button(
                    label=f"Open/Download {pdf}",
                    data=f.read(),
                    file_name=pdf,
                    mime="application/pdf"
                )
    else:
        st.info("Error in downloading report.")
        

st.title("JoSAA Analytics 2025")

tab1, tab2, tab3 = st.tabs(["Got This Rank ?", " Dream College ?", "Best IIT for this ?"])


with tab1:
    st.subheader("Filter and Predict Options According to Your Rank")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        user_rank = st.number_input("Enter Your Rank (Category/CRL):", min_value=1, value=10180, step=1)
    with col2:
        selected_cat = st.selectbox("Your Seat Category:", categories)
    with col3:
        selected_gender = st.selectbox("Gender Pool:", genders)
    with col4:
        selected_quota = st.selectbox("Quota:", quotas)

    # Round selector
    selected_round = st.selectbox("Round:", rounds)

    # Secondary filter multi-select
    selected_types = st.multiselect("Preferred Institute Types:", insti_types, default=insti_types)

    if st.button("Search", type="primary"):
        # Construct the Join Query targeting your exact Star Schema setup
        query = """
            SELECT DISTINCT
                f.year AS Year,
                f.round AS Round,
                i.insti_value AS [Institute Name],
                c.cat_value AS [Category],
                g.gender_value AS [Gender],
                t.insti_type AS [Institute Type],
                q.quota_value AS Quota,
                p.acad_prog_value AS [Academic Program],
                f.opening_rank AS [Opening Rank],
                f.closing_rank AS [Closing Rank]
            FROM FactsTable f
            JOIN Dim_InstiName i ON f.insti_index = i.insti_index
            JOIN Dim_InstiType t ON f.insti_type_index = t.insti_type_index
            JOIN Dim_Quota q ON f.quota_index = q.quota_index
            JOIN Dim_Gender g ON f.gender_index = g.gender_index
            JOIN Dim_Category c ON f.cat_index = c.cat_index
            JOIN Dim_AcadProgram p ON f.acad_prog_index = p.acad_prog_index
                        WHERE c.cat_value = ? 
                            AND g.gender_value = ? 
                            AND q.quota_value = ?
                            AND f.closing_rank >= ?
                            AND f.round = ?
        """
        
        conn = get_db_connection()
        results_df = pd.read_sql(query, conn, params=(selected_cat, selected_gender, selected_quota, user_rank, selected_round))
        conn.close()

        if selected_types:
            results_df = results_df[results_df['Institute Type'].isin(selected_types)]

        results_df = results_df.drop_duplicates()

        if results_df.empty:
            st.warning("No historical options found matching your exact parameters. Try widening your criteria.")
        else:
            # 5% is the safety boundary
            def calculate_safety(row):
                closing = row['Closing Rank']
                if closing == 0 or pd.isna(closing):
                    return "Unknown"
                margin = (closing - user_rank) / closing
                return "🟢 Safe" if margin > 0.05 else "🟡 Borderline"

            results_df['Admission Chance'] = results_df.apply(calculate_safety, axis=1)
            
            cols = ['Admission Chance'] + [col for col in results_df.columns if col != 'Admission Chance']
            results_df = results_df[cols]

            # High-level overview metrics
            total_options = len(results_df)
            safe_count = len(results_df[results_df['Admission Chance'] == "🟢 Safe"])
            border_count = total_options - safe_count

            m1, m2, m3 = st.columns(3)
            m1.metric("Total Match Choices Found", total_options)
            m2.metric("Highly Probable Choices (Safe)", safe_count)
            m3.metric("Competitive Choices (Borderline)", border_count)

            st.write("### Predicted Admission Choices")


            st.dataframe(
                results_df.sort_values(by="Closing Rank", ascending=True),
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Admission Chance": st.column_config.TextColumn("Admission Status", help="Safe (Green) vs Borderline (Yellow) predictability based on historical ranks."),
                    "Closing Rank": st.column_config.NumberColumn("Closing Cutoff", format="%d"),
                    "Opening Rank": st.column_config.NumberColumn("Opening Cutoff", format="%d")
                }
            )

with tab2:
    st.subheader("Analyze The College")
    st.write("Filter down directly to see closing requirements across rounds for any campus.")

    ec1, ec2 = st.columns(2)
    with ec1:
        explorer_insti = st.selectbox("Select Target Institute:", all_institutes)
    with ec2:
        explorer_cat = st.selectbox("Select Target Category:", categories, key="explorer_cat")
    # Explorer round selector
    explorer_round = st.selectbox("Select Round:", rounds, key="explorer_round")

    if explorer_insti:
        explorer_query = """
            SELECT DISTINCT
                f.year AS Year,
                f.round AS Round,
                c.cat_value AS [Category],
                p.acad_prog_value AS [Academic Program],
                g.gender_value AS [Gender Pool],
                q.quota_value AS Quota,
                f.opening_rank AS [Opening Rank],
                f.closing_rank AS [Closing Rank]
            FROM FactsTable f
            JOIN Dim_InstiName i ON f.insti_index = i.insti_index
            JOIN Dim_Category c ON f.cat_index = c.cat_index
            JOIN Dim_Gender g ON f.gender_index = g.gender_index
            JOIN Dim_Quota q ON f.quota_index = q.quota_index
            JOIN Dim_AcadProgram p ON f.acad_prog_index = p.acad_prog_index
            WHERE i.insti_value = ? AND c.cat_value = ? AND f.round = ?
            ORDER BY p.acad_prog_value, f.year DESC, f.round ASC
        """
        conn = get_db_connection()
        explore_df = pd.read_sql(explorer_query, conn, params=(explorer_insti, explorer_cat, explorer_round))
        conn.close()

        explore_df = explore_df.drop_duplicates()

        if explore_df.empty:
            st.info("No programmatic records found matching the selection.")
        else:
            # Inline text-search query for programs inside the explorer tab
            search_prog = st.text_input("Quick Filter Academic Program Name (e.g. 'Computer Science'):")
            if search_prog:
                explore_df = explore_df[explore_df['Academic Program'].str.contains(search_prog, case=False, na=False)]

            explore_df = explore_df.drop_duplicates()

            st.dataframe(
                explore_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Closing Rank": st.column_config.NumberColumn(format="%d"),
                    "Opening Rank": st.column_config.NumberColumn(format="%d")
                }
            )

with tab3:
    st.subheader("Top IIT for a branch")

    selected_branch = st.selectbox("Select Branch:", branch_options, key="iit_branch_select")
    if not os.path.exists(BRANCH_CACHE_DB):
        st.error(
            f"Dev Error occured. Download Branch_Cache_Db"
        )
    else:
        cache_signature = os.path.getmtime(BRANCH_CACHE_DB)
        branch_df = load_branch_seat_counts(selected_branch, cache_signature)

        if branch_df.empty:
            st.info("No allotment rows found for that branch in the cache database.")
        else:
            top_row = branch_df.iloc[0]
            total_seats_taken = int(branch_df["Seats Taken"].sum())

            m1, m2, m3 = st.columns(3)
            m1.metric("Top IIT", top_row["Institute Name"])
            m2.metric("Total Seats Taken", total_seats_taken)
            m3.metric("Tracked IITs", len(branch_df))

            st.write("### All IIT seat counts for the selected branch")
            st.caption(f"Showing {len(branch_df)} IIT rows from the cache database.")
            st.dataframe(
                branch_df,
                use_container_width=True,
                hide_index=True,
                height=min(700, 35 + (len(branch_df) * 35)),
                column_config={
                    "Seats Taken": st.column_config.NumberColumn(format="%d")
                }
            )
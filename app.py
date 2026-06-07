import streamlit as st
import sqlite3
import pandas as pd
import os
import plotly.express as px
import altair as alt

from crl_data import get_btw_ranks
from seat_matrix_reader import get_available_branches, get_iit_branch_seat_counts

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

    if 'OTHER' not in types:
        types.append('OTHER')
        types = sorted(types)
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

tab1, tab2, tab3, tab4, tab5 = st.tabs(["Got This Rank ?", " Dream College ?", "Seats for this ?", "Between Two Ranks", "State & Rank Data ?"])


with tab1:
    st.subheader("Filter and Predict Options According to Your Rank")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        adv_rank = st.number_input("Enter Your Advance Rank (AIR):", min_value=1, value=10180, step=1)
    with col2:
        mains_rank = st.number_input("Enter Your Mains Rank (JEE Mains):", min_value=1, value=9856, step=1)
    with col3:
        selected_cat = str(st.selectbox("Your Seat Category:", categories))
    with col4:
        selected_gender = str(st.selectbox("Gender Pool:", genders))

    # Quota selector moved below to keep the row compact
    selected_quota = str(st.selectbox("Quota:", quotas))

    # Round selector
    selected_round = int(st.selectbox("Round:", rounds) or 0)

    # Secondary filter multi-select
    selected_types = st.multiselect("Preferred Institute Types:", insti_types, default=insti_types)

    # --- Added: Dynamic Cutoff Tolerance Slider ---
    cutoff_buffer = st.slider(
        "Select Admission Cutoff Buffer (%)",
        min_value=0,
        max_value=50,
        value=15,
        step=1,
        help="How much higher (worse) than the historical closing rank you are willing to consider. Options beyond this % are hidden."
    )

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
                AND f.round = ?
        """
        
        # DB has AI instead of Al, a jugad fix 
        if isinstance(selected_quota, str) and selected_quota.strip().upper() == 'AL':
            db_quota = 'AI'
        else:
            db_quota = selected_quota

        conn = get_db_connection()

        # Adv ranks for IITs and Mains for NITs
        results_df = pd.read_sql(query, conn, params=(selected_cat, selected_gender, db_quota, selected_round))
        conn.close()

        if selected_types:
            results_df = results_df[results_df['Institute Type'].isin(selected_types)]

        results_df = results_df.drop_duplicates()

        if results_df.empty:
            st.warning("No historical options found matching your exact parameters. Try widening your criteria.")
        else:

            # Fixed: Defensive text cleaning to handle database whitespace/casing issues
            def applicable_rank(row):
                inst_type = str(row['Institute Type']).strip().upper()
                return adv_rank if inst_type == 'IIT' else mains_rank

            # Fixed: Bulletproof safety classification logic
            def calculate_safety(row):
                closing = row['Closing Rank']
                if closing == 0 or pd.isna(closing):
                    return None
                
                rank_to_use = applicable_rank(row)
                pct_diff = (rank_to_use - closing) / closing
                buffer_decimal = cutoff_buffer / 100.0
                
                # 1. Completely hide if user's rank exceeds the allowed slider buffer
                if pct_diff > buffer_decimal:
                    return None
                
                # 2. Borderline if user's rank is worse than closing but within buffer, 
                # OR if it's better but within a razor-thin 5% margin.
                elif pct_diff >= -0.05:
                    return "🟡 Borderline"
                
                # 3. Good chance if user's rank is comfortably lower (better) than the cutoff by > 5%
                else:
                    return "🟢 Good Chance"

            results_df['Admission Chance'] = results_df.apply(calculate_safety, axis=1)
            
            # Drop the hidden rows (None) so they don't clutter the UI
            results_df = results_df[results_df['Admission Chance'].notna()]
            
            # Reorder columns to put status first
            cols = ['Admission Chance'] + [col for col in results_df.columns if col != 'Admission Chance']
            results_df = results_df[cols]

            # High-level overview metrics calculation
            total_options = len(results_df)
            safe_count = len(results_df[results_df['Admission Chance'] == "🟢 Good Chance"])
            border_count = len(results_df[results_df['Admission Chance'] == "🟡 Borderline"])

            m1, m2, m3 = st.columns(3)
            m1.metric("Total Match Choices Found", total_options)
            m2.metric("Highly Probable Choices (Good Chance)", safe_count)
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
        explorer_insti = str(st.selectbox("Select Target Institute:", all_institutes))
    with ec2:
        explorer_cat = str(st.selectbox("Select Target Category:", categories, key="explorer_cat"))

    explorer_round = int(st.selectbox("Select Round:", rounds, key="explorer_round") or 0)

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
    st.subheader("Seats For A Branch")

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

with tab4:
    st.subheader("Compare Colleges and Branches Across a Rank Band")
    st.write("Enter two CRL ranks to see which colleges and branches appear in that window.")

    rank_col1, rank_col2 = st.columns(2)
    with rank_col1:
        lower_rank = st.number_input("Lower Rank", min_value=1, value=1, step=1)
    with rank_col2:
        upper_rank = st.number_input("Upper Rank", min_value=1, value=5000, step=1)

    if st.button("Analyze Rank Band", type="primary"):
        if lower_rank > upper_rank:
            st.error("Lower Rank must be less than or equal to Upper Rank.")
        else:
            try:
                rank_rows = get_btw_ranks(int(lower_rank), int(upper_rank))
            except Exception as exc:
                st.error(f"Could not load rank-band data: {exc}")
            else:
                if not rank_rows:
                    st.info("No colleges or branches were found in that rank range.")
                else:
                    rank_df = pd.DataFrame(rank_rows, columns=["Rank", "Institute Name", "Branch"])
                    rank_df["Rank"] = pd.to_numeric(rank_df["Rank"], errors="coerce")
                    rank_df = rank_df.dropna(subset=["Rank"])
                    rank_df["Rank"] = rank_df["Rank"].astype(int)
                    rank_df = rank_df.sort_values("Rank", ascending=True)

                    total_rows = len(rank_df)
                    unique_colleges = rank_df["Institute Name"].nunique()
                    unique_branches = rank_df["Branch"].nunique()

                    m1, m2, m3 = st.columns(3)
                    m1.metric("Total Records", total_rows)
                    m2.metric("Unique Colleges", unique_colleges)
                    m3.metric("Unique Branches", unique_branches)

                    st.dataframe(rank_df, use_container_width=True, hide_index=True)

                    chart_left, chart_right = st.columns(2)

                    college_counts = rank_df["Institute Name"].value_counts().reset_index(name="Count")
                    college_counts = college_counts.rename(columns={"Institute Name": "College", "index": "College"})

                    branch_counts = rank_df["Branch"].value_counts().reset_index(name="Count")
                    branch_counts = branch_counts.rename(columns={"index": "Branch"})

                    with chart_left:
                        st.markdown("##### Colleges in the band")
                        top_colleges = college_counts.head(30)
                        college_chart = alt.Chart(top_colleges).mark_bar().encode(
                            x=alt.X("Count:Q", title="Occurrences"),
                            y=alt.Y("College:N", sort="-x", title="College"),
                            tooltip=["College:N", "Count:Q"],
                        ).properties(height=420)
                        st.altair_chart(college_chart, use_container_width=True)

                    with chart_right:
                        st.markdown("##### Branch mix in the band")
                        top_branches = branch_counts.copy()
                        if len(top_branches) > 10:
                            other_count = int(top_branches.iloc[10:]["Count"].sum())
                            top_branches = top_branches.head(10)
                            top_branches = pd.concat(
                                [top_branches, pd.DataFrame([{ "Branch": "Other", "Count": other_count }])],
                                ignore_index=True,
                            )

                        branch_chart = alt.Chart(top_branches).mark_arc(innerRadius=60).encode(
                            theta=alt.Theta("Count:Q"),
                            color=alt.Color("Branch:N", title="Branch"),
                            tooltip=["Branch:N", "Count:Q"],
                        ).properties(height=420)
                        st.altair_chart(branch_chart, use_container_width=True)

with tab5:
    conn = sqlite3.connect("database.db")
    st.title("📊 Student Demographics & Rank Distribution")
    st.write(
        "Explore how top rankers are distributed across various IITs "
        "and visualize where campuses draw their student populations from geographically."
    )

    col1, col2 = st.columns([1, 1], gap="large")
    

    with col1:
        st.header("🗺️ State-wise Campus Breakdown")
        st.write("Select an institute to see a visual breakdown of where its students migrate from.")
        
        try:

            insti_query = "SELECT DISTINCT insti_name FROM crl_vs_alloted WHERE insti_name IS NOT NULL ORDER BY insti_name"
            institute_list = pd.read_sql(insti_query, conn)["insti_name"].tolist()
            
            if institute_list:
                selected_insti = st.selectbox(
                    "Choose an Institute", 
                    institute_list, 
                    key="demographic_insti_select"
                )
                
                state_query = """
                    SELECT rws.state AS State, COUNT(*) AS Students
                    FROM crl_vs_alloted cva
                    JOIN roll_with_state rws ON cva.rollno = rws.roll
                    WHERE cva.insti_name = ?
                    GROUP BY rws.state
                    ORDER BY Students DESC
                """
                df_state = pd.read_sql(state_query, conn, params=[selected_insti])
                

                if not df_state.empty:
                    fig_pie = px.pie(
                        df_state, 
                        values='Students', 
                        names='State', 
                        hole=0.4,  # Modern donut chart style
                        color_discrete_sequence=px.colors.qualitative.Safe
                    )
                    fig_pie.update_traces(textposition='inside', textinfo='percent+label')
                    fig_pie.update_layout(
                        margin=dict(t=20, b=20, l=10, r=10),
                        showlegend=False  
                    )
                    st.plotly_chart(fig_pie, use_container_width=True)
                    

                    with st.expander("Show exact student count per state"):
                        st.dataframe(df_state, use_container_width=True, hide_index=True)
                else:
                    st.warning("No geographic matching records found for this campus.")
            else:
                st.error("No institutes found in the database.")
                
        except Exception as e:
            st.error(f"Error fetching demographic data: {e}")


    with col2:
        st.header("🏆 Rank Distribution Filter")
        st.write("Select a rank cutoff tier to see which specific institutes captured those top minds.")
        
        range_options = {
            "Top 100": 100,
            "Top 200": 200,
            "Top 500": 500,
            "Top 1000": 1000,
            "Top 2000": 2000,
            "Top 5000": 5000
        }
        
        selected_range_label = st.selectbox(
            "Select Rank Tier Cutoff", 
            list(range_options.keys()), 
            index=4, 
            key="rank_tier_select"
        )
        cutoff_value = range_options[selected_range_label]
        
        try:

            rank_query = """
                SELECT insti_name AS Institute, COUNT(*) AS Seats_Occupied
                FROM crl_vs_alloted
                WHERE CAST(rank AS INTEGER) <= ?
                GROUP BY insti_name
                ORDER BY Seats_Occupied DESC
            """
            df_ranks = pd.read_sql(rank_query, conn, params=[cutoff_value])
            

            if not df_ranks.empty:
                fig_bar = px.bar(
                    df_ranks,
                    x='Seats_Occupied',
                    y='Institute',
                    orientation='h',
                    color='Seats_Occupied',
                    color_continuous_scale=px.colors.sequential.Blugrn,
                    title=f"Institute Share within the {selected_range_label}"
                )
                fig_bar.update_layout(
                    yaxis={'categoryorder':'total ascending'},
                    margin=dict(t=40, b=20, l=10, r=10),
                    coloraxis_showscale=False
                )
                st.plotly_chart(fig_bar, use_container_width=True)
            else:
                st.info(f"No database records found with rank values <= {cutoff_value}.")
                
        except Exception as e:
            st.error(f"Error fetching rank metrics: {e}")
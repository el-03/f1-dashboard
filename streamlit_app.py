import streamlit as st
import psycopg2
import pandas as pd
import altair as alt
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv()
schema = os.getenv("SCHEMA")

st.set_page_config(
    page_title="F1 Dashboard",
    layout="wide",
)

"""
# :material/grain: F1 Dashboard

F1 data analysis, started from the Hybrid V6 Turbo Era (2014) onwards.
"""

""

cols_1 = st.columns([1, 5])
st.markdown("""
    <h2 style='text-align:center; margin: 0;'>
        Drivers' Championship Progression
    </h2>
    """, unsafe_allow_html=True)
cols_2 = st.columns([1, 4, 1])
st.markdown("---")
st.markdown("""
    <h2 style='text-align:center; margin: 0;'>
        Teams' Championship Progression
    </h2>
    """, unsafe_allow_html=True)
cols_3 = st.columns([1, 4, 1])

col_1_1 = cols_1[0].container(
    height="stretch"
)

col_1_2 = cols_1[1].container(
    border=False, height="stretch"
)

col_2_1 = cols_2[0].container(
    border=True, height="stretch"
)

col_2_2 = cols_2[1].container(
    height="stretch"
)

col_2_3 = cols_2[2].container(
    height="stretch"
)

col_3_1 = cols_3[0].container(
    border=True, height="stretch"
)

col_3_2 = cols_3[1].container(
    height="stretch"
)

col_3_3 = cols_3[2].container(
    height="stretch"
)
# Database connection
@st.cache_resource
def get_connection():
    """Create database connection"""
    load_dotenv()
    conn = psycopg2.connect(
        user=os.getenv("USER_SB"),
        password=os.getenv("PASSWORD"),
        host=os.getenv("HOST"),
        port=os.getenv("PORT"),
        dbname=os.getenv("DBNAME")
    )

    conn.autocommit = True
    return conn


# Get connection
connection = get_connection()


def query_data(query, conn):
    """Execute query and return DataFrame"""
    # Use the existing connection passed in
    try:
        return pd.read_sql(query, conn)
    except (psycopg2.InterfaceError, psycopg2.OperationalError):
        # Connection died — reconnect
        conn = get_connection()
        return pd.read_sql(query, conn)


current_year = datetime.now().year
year_options = sorted(list(range(2014, current_year + 1)), reverse=True)

# Loader: State - Round Number
@st.cache_data(ttl=600)
def get_round_num(selected_year, _conn) -> int:
    return query_data(f"""
    SELECT MAX(r.number) FROM formula_one.race_result rr
    LEFT JOIN formula_one.round r ON 
      rr.round_id = r.id
    WHERE EXTRACT(YEAR FROM r.date) = {selected_year};""", _conn)['max'][0]


with col_1_1:
    season_ticker = st.selectbox(
        "Season",
        options=year_options,
        index=year_options.index(st.session_state.get("s_t_input", current_year))
        if "s_t_input" in st.session_state else 0,
    )
    st.session_state.round_slider_max = get_round_num(season_ticker, connection)

# Loader: Drivers' Standing
@st.cache_data(ttl=600)
def get_drivers_standings(selected_year, _conn) -> pd.DataFrame:
    return query_data(f"""
    SELECT 
        ROW_NUMBER() OVER (ORDER BY MAX(points) DESC) position,
        d.forename || ' ' || d.surname driver, 
        MAX(points) points 
    FROM formula_one.driver_championship dc
    LEFT JOIN formula_one.driver AS d ON
        dc.driver_id = d.id
    WHERE year = {selected_year}
    GROUP BY d.forename || ' ' || d.surname
    ORDER BY MAX(points) DESC;""", _conn)


# Loader: Teams' Standings
@st.cache_data(ttl=600)
def get_teams_standings(selected_year, _conn) -> pd.DataFrame:
    return query_data(f"""
    SELECT
        ROW_NUMBER() OVER (ORDER BY MAX(points) DESC) position,
        t.name team, 
        MAX(points) points 
    FROM formula_one.team_championship tc
    LEFT JOIN formula_one.team AS t ON
        tc.team_id = t.id
    WHERE year = {selected_year}
    GROUP BY year, t.name
    ORDER BY MAX(points) DESC;""", _conn)


# Load Data: Standings
drivers_standings_df = get_drivers_standings(season_ticker, connection)
drivers_standings_df.rename(columns={"position": "POS.", "driver": "DRIVER", "points": "PTS."}, inplace=True)
drivers_standings_df["PTS."] = drivers_standings_df["PTS."].astype(int)
drivers_standings_df.set_index("POS.", inplace=True)

teams_standings_df = get_teams_standings(season_ticker, connection)
teams_standings_df.rename(columns={"position": "POS.", "team": "TEAM", "points": "PTS."}, inplace=True)
teams_standings_df["PTS."] = teams_standings_df["PTS."].astype(int)
teams_standings_df.set_index("POS.", inplace=True)


# Loader: Most Win
@st.cache_data(ttl=600)
def get_most_win_d(selected_year, _conn) -> pd.DataFrame:
    return query_data(f"""
        SELECT 
            d.abbreviation,
            d.forename || ' ' || d.surname as driver, 
            MAX(win_count) total_win
        FROM {schema}.driver_championship dc
        LEFT JOIN {schema}.driver AS d ON
            dc.driver_id = d.id
        WHERE year = {selected_year}
        GROUP BY d.abbreviation, d.forename, d.surname
        ORDER BY MAX(win_count) DESC
        LIMIT 1;
    """, _conn)


@st.cache_data(ttl=600)
def get_most_win_t(selected_year, _conn) -> pd.DataFrame:
    return query_data(f"""
    SELECT 
        t.name team, 
        MAX(win_count) total_win 
    FROM {schema}.team_championship tc
    LEFT JOIN {schema}.team AS t ON
        tc.team_id = t.id
    WHERE year = {selected_year}
    GROUP BY t.name
    ORDER BY MAX(win_count) DESC
    LIMIT 1;
""", _conn)


# Load Data: Most Win
most_win_d_df = get_most_win_d(season_ticker, connection)
most_win_t_df = get_most_win_t(season_ticker, connection)


# Loader: Most Pole
@st.cache_data(ttl=600)
def get_most_poles_d(selected_year, _conn) -> pd.DataFrame:
    return query_data(f"""
        SELECT
            d.abbreviation,
            d.forename || ' ' || d.surname driver,
            COUNT(*) total_pole
        FROM {schema}.qualifying_result qr
        LEFT JOIN {schema}.driver d ON
            qr.driver_id = d.id
        LEFT JOIN {schema}.season s ON
            qr.season_id = s.id
        WHERE s.year = {selected_year} AND qr.position = 1
        GROUP BY d.abbreviation, d.forename || ' ' || d.surname
        ORDER BY COUNT(*) DESC;
    """, _conn)


@st.cache_data(ttl=600)
def get_most_poles_t(selected_year, _conn) -> pd.DataFrame:
    return query_data(f"""
        SELECT
            t.name team,
            COUNT(*) total_pole
        FROM {schema}.qualifying_result qr
        LEFT JOIN {schema}.driver d ON
            qr.driver_id = d.id
        LEFT JOIN {schema}.team t ON
            qr.team_id = t.id
        LEFT JOIN {schema}.season s ON
            qr.season_id = s.id
        WHERE s.year = {selected_year} AND qr.position = 1
        GROUP BY t.name
        ORDER BY COUNT(*) DESC
        LIMIT 1;
    """, _conn)


# Load Data: Most Pole
most_poles_d_df = get_most_poles_d(season_ticker, connection)
most_poles_t_df = get_most_poles_t(season_ticker, connection)


# Loader: Team - Most DNFs
def get_most_dnfs_t(selected_year, _conn) -> pd.DataFrame:
    return query_data(f"""
    SELECT t.name team, COUNT(*) retired_count FROM {schema}.race_result rr
    LEFT JOIN {schema}.team AS t ON
        rr.team_id = t.id
    LEFT JOIN {schema}.season AS s ON
        rr.season_id = s.id
    WHERE s.year = {selected_year}
        AND position_text = 'R' 
    GROUP BY year, t.name
    ORDER BY COUNT(*) DESC
    LIMIT 1;
""", _conn)


# Load Data: Team - Most DNFs
most_dnfs_t_df = get_most_dnfs_t(season_ticker, connection)


# Loader: Driver - Overtake
@st.cache_data(ttl=600)
def get_ovt_d(selected_year, _conn) -> pd.DataFrame:
    return query_data(f"""
    WITH cte_1 AS (
        SELECT
            d.abbreviation,
            d.forename || ' ' || d.surname driver, 
            (rr.grid_position - rr.position) overtake
        FROM {schema}.race_result rr
        LEFT JOIN {schema}.driver d ON
            rr.driver_id = d.id
        LEFT JOIN {schema}.season s ON
            rr.season_id = s.id
        WHERE s.year = {selected_year}
            AND rr.position_text ~ '^[0-9]+$'
    )
    SELECT abbreviation, driver, SUM(overtake) total_overtake, ROUND(AVG(overtake), 2) avg_overtake FROM cte_1
    GROUP BY abbreviation, driver
    ORDER BY avg_overtake DESC;""", _conn)


# Load Data: Driver - Overtake
ovt_d_df = get_ovt_d(season_ticker, connection)

pills_d_map = {
    "Top 3": 3,
    "Top 5": 5,
    "Top 10": 10,
    "All": 20,
}

pills_t_map = {
    "Top 3": 3,
    "Top 5": 5,
    "All": 20,
}

# --- State Initialization ---
if 'round_slider_max' not in st.session_state:
    st.session_state.round_slider_max = get_round_num(season_ticker, connection)

# Initialize driver and team sliders only if not already set
for key in ['round_slider_d', 'round_slider_t']:
    if key not in st.session_state:
        st.session_state[key] = st.session_state.round_slider_max

with col_2_1:
    selection_drivers = st.pills("Filter", pills_d_map, default={"Top 3": 3}, key="drivers_filter")

    st.markdown("---")

    cols_1 = st.columns(2)

    most_win_d = most_win_d_df.iloc[0]
    cols_1[0].markdown("""### Most Wins""")
    cols_1[0].metric(
        most_win_d["driver"],
        most_win_d["abbreviation"],
        delta=f"{most_win_d["total_win"]} Win(s)",
        width="content"
    )

    most_poles_d = most_poles_d_df.iloc[0]
    cols_1[1].markdown("""### Most Poles""")
    cols_1[1].metric(
        most_poles_d["driver"],
        most_poles_d["abbreviation"],
        delta=f"{most_poles_d["total_pole"]} Pole(s)",
        width="content"
    )

    most_gains_d = ovt_d_df.iloc[0]
    most_losses_d = ovt_d_df.iloc[-1]

    st.markdown("""### Place Gains & Losses""")
    cols_2 = st.columns(2)
    cols_2[0].metric(
        most_gains_d["driver"],
        most_gains_d["abbreviation"],
        delta=f"{most_gains_d["total_overtake"]} | +{most_gains_d["avg_overtake"]} (avg.)",
        width="content"
    )

    cols_2[1].metric(
        most_losses_d["driver"],
        most_losses_d["abbreviation"],
        delta=f"{most_losses_d["total_overtake"]} | {most_losses_d["avg_overtake"]} (avg.)",
        width="content"
    )


# Loader - Load Data: Drivers' Progression
def get_progression_d(selected_year, _conn) -> pd.DataFrame:
    return query_data(f"""
    SELECT 
        dc.round_number,
        d.forename || ' ' || d.surname as driver,
        dc.points,
        dc.position
    FROM formula_one.driver_championship dc
    JOIN formula_one.driver d ON d.id = dc.driver_id
    JOIN formula_one.season s ON s.id = dc.season_id
    WHERE s.year = {selected_year}
    ORDER BY dc.round_number, dc.position
""", _conn)


drivers_progression_df = get_progression_d(season_ticker, connection)

with col_2_2:
    if not drivers_progression_df.empty:
        # Use st.session_state to get current slider value (default if not set)
        round_slider_d = st.session_state.get('round_slider_d', st.session_state.round_slider_max)

        # Filter data based on the stored slider value
        filtered_rounds = drivers_progression_df[
            drivers_progression_df['round_number'] <= round_slider_d
        ]

        top_drivers = (
            filtered_rounds.groupby('driver')['points']
            .max()
            .nlargest(pills_d_map[selection_drivers])
            .index
            .tolist()
        )

        filtered_data = filtered_rounds[filtered_rounds['driver'].isin(top_drivers)]

        # Build and show the chart
        chart = (
            alt.Chart(filtered_data)
            .mark_line(point=True)
            .encode(
                x=alt.X('round_number:O', title='Round'),
                y=alt.Y('points:Q', title='Points'),
                color=alt.Color('driver:N', title='Driver'),
                tooltip=[
                    alt.Tooltip('driver:N', title='Driver'),
                    alt.Tooltip('points:Q', title='Points')
                ]
            )
            .properties(height=550)
        )
        st.altair_chart(chart, use_container_width=True)

        # Render the slider below the chart
        st.slider(
            "Round",
            1,
            st.session_state.round_slider_max,
            st.session_state.round_slider_max,
            key="round_slider_d"
        )


with col_2_3:
    st.markdown("Drivers' Standings")
    st.table(drivers_standings_df.head(5))
    with st.expander("More Drivers"):
        st.table(drivers_standings_df[5:])

with col_3_1:
    selection_teams = st.pills("Filter", pills_t_map, default={"Top 3": 3}, key="teams_filter")
    st.markdown("---")
    st.markdown("""### Most Wins & Poles""")
    cols = st.columns(2)

    most_win_t = most_win_t_df.iloc[0]
    cols[0].metric(
        "Race",
        most_win_t["team"],
        delta=f"{most_win_t["total_win"]} Win(s)",
        width="content"
    )

    most_poles_t = most_poles_t_df.iloc[0]

    cols[1].metric(
        "Qualifying",
        most_poles_t["team"],
        delta=f"{most_poles_t["total_pole"]} Pole(s)",
        width="content"
    )

    st.markdown("""### Most DNFs""")
    most_dnfs_t = most_dnfs_t_df.iloc[0]
    st.metric(
        "Total",
        most_dnfs_t["team"],
        delta=f"{-1 * most_dnfs_t["retired_count"]} DNF(s)",
        width="content"
    )


# Loader - Load Data: Teams' Progression
def get_progression_t(selected_year, _conn) -> pd.DataFrame:
    return query_data(f"""
    SELECT
        tc.round_number,
        t.name as team,
        tc.points points,
        tc.position
    FROM formula_one.team_championship tc
    JOIN formula_one.team t ON t.id = tc.team_id
    JOIN formula_one.season s ON s.id = tc.season_id
    WHERE s.year = {selected_year}
    ORDER BY tc.round_number, tc.position
""", _conn)


teams_progression_df = get_progression_t(season_ticker, connection)

with col_3_2:
    if not teams_progression_df.empty:
        # Use st.session_state to get current slider value (default if not set)
        round_slider_t = st.session_state.get('round_slider_t', st.session_state.round_slider_max)

        # Filter data based on the stored slider value
        filtered_rounds = teams_progression_df[
            teams_progression_df['round_number'] <= round_slider_t
            ]

        # Get top N drivers by max points
        top_teams = (
            filtered_rounds.groupby('team')['points']
            .max()
            .nlargest(pills_t_map[selection_teams])
            .index
            .tolist()
        )
        filtered_data = filtered_rounds[filtered_rounds['team'].isin(top_teams)]

        chart = (
            alt.Chart(filtered_data)
            .mark_line(point=True)
            .encode(
                x=alt.X('round_number:O', title='Round'),  # ordinal if rounds are integers
                y=alt.Y('points:Q', title='Points'),
                color=alt.Color('team:N', title='Team'),
                tooltip=[
                    alt.Tooltip('team:N', title='Team'),
                    alt.Tooltip('points:Q', title='Points')
                ]
            )
            .properties(height=550)
        )

        st.altair_chart(chart, use_container_width=True)

        # Render the slider below the chart
        st.slider(
            "Round",
            1,
            st.session_state.round_slider_max,
            st.session_state.round_slider_max,
            key="round_slider_t"
        )

with col_3_3:
    st.markdown("Teams' Standings")
    st.table(teams_standings_df.head(5))
    with st.expander("More Teams"):
        st.table(teams_standings_df[5:])

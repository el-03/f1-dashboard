import altair as alt
from datetime import datetime

from data_loaders import *
from schedule_board import schedule_board


def clamp_round_slider(current_value, max_round):
    if max_round <= 0:
        return 0

    if current_value is None:
        return max_round

    return max(1, min(current_value, max_round))


st.set_page_config(
    page_title="F1 Dashboard",
    layout="wide",
)

"""
# :material/grain: F1 Dashboard

F1 Calendar & Data Analysis (started from the Hybrid V6 Turbo Era (2014) onwards).

"""

# Get connection
connection = get_connection()

# Load Data: Latest Season
current_year = get_latest_season(connection)

year_options = sorted(list(range(2014, current_year + 1)), reverse=True)

if datetime.now().year == current_year:
    schedule_board()

st.markdown("---")
cols_1 = st.columns([2, 4, 2])
cols_1[1].markdown("""
    <h2 style='text-align:center; margin: 0;'>
        Drivers' Championship Progression
    </h2>
    """, unsafe_allow_html=True)
cols_2 = st.columns([2, 4, 2])
st.markdown("---")
st.markdown("""
    <h2 style='text-align:center; margin: 0;'>
        Teams' Championship Progression
    </h2>
    """, unsafe_allow_html=True)
cols_3 = st.columns([2, 4, 2])

col_1_1 = cols_1[0].container(height="stretch")

col_1_2 = cols_1[1].container(border=False, height="stretch")

col_2_1 = cols_2[0].container(border=True, height="stretch")

col_2_2 = cols_2[1].container(border=True, height="stretch")

col_2_3 = cols_2[2].container(height="stretch")

col_3_1 = cols_3[0].container(border=True, height="stretch")

col_3_2 = cols_3[1].container(border=True, height="stretch")

col_3_3 = cols_3[2].container(height="stretch")

with col_1_1:
    season_ticker = st.selectbox(
        "Season",
        options=year_options,
        index=year_options.index(st.session_state.get("s_t_input", current_year))
        if "s_t_input" in st.session_state else 0,
        key="s_t_input",
    )

    if "prev_s_t_input" not in st.session_state:
        st.session_state.prev_s_t_input = season_ticker

    st.session_state.round_slider_max = get_round_num(season_ticker, connection)

    if st.session_state.prev_s_t_input != season_ticker:
        st.session_state.prev_s_t_input = season_ticker
        st.session_state.round_slider_d = st.session_state.round_slider_max
        st.session_state.round_slider_t = st.session_state.round_slider_max

    st.session_state.round_slider_d = clamp_round_slider(
        st.session_state.get("round_slider_d"),
        st.session_state.round_slider_max,
    )
    st.session_state.round_slider_t = clamp_round_slider(
        st.session_state.get("round_slider_t"),
        st.session_state.round_slider_max,
    )

# Load Data: Standings
drivers_standings_df = get_drivers_standings(season_ticker, connection)
drivers_standings_df.rename(columns={"position": "POS.", "driver": "DRIVER", "points": "PTS."}, inplace=True)
drivers_standings_df["PTS."] = drivers_standings_df["PTS."].astype(int)
drivers_standings_df.set_index("POS.", inplace=True)

teams_standings_df = get_teams_standings(season_ticker, connection)
teams_standings_df.rename(columns={"position": "POS.", "team": "TEAM", "points": "PTS."}, inplace=True)
teams_standings_df["PTS."] = teams_standings_df["PTS."].astype(int)
teams_standings_df.set_index("POS.", inplace=True)

# Load Data: Most Win
most_win_d_df = get_most_win_d(season_ticker, connection)
most_win_t_df = get_most_win_t(season_ticker, connection)

# Load Data: Most Pole
most_poles_d_df = get_most_poles_d(season_ticker, connection)
most_poles_t_df = get_most_poles_t(season_ticker, connection)

# Load Data: Team - Most DNFs
most_dnfs_t_df = get_most_dnfs_t(season_ticker, connection)

# Load Data: Driver - Overtake
ovt_d_df = get_ovt_d(season_ticker, connection)

pills_d_map = {
    "Top 3": 3,
    "Top 5": 5,
    "Top 10": 10,
    "All": len(drivers_standings_df),
}

pills_t_map = {
    "Top 3": 3,
    "Top 5": 5,
    "All": len(teams_standings_df),
}

with col_2_1:
    selection_drivers = st.pills("Filter", pills_d_map, default={"Top 3": 3}, key="drivers_filter")

    st.markdown("---")

    cols_1 = st.columns(2)

    cols_1[0].markdown("""### Most Wins""")
    if not most_win_d_df.empty:
        most_win_d = most_win_d_df.iloc[0]
        cols_1[0].metric(
            most_win_d["driver"],
            most_win_d["abbreviation"],
            delta=f"{most_win_d["total_win"]} Win(s)",
            width="content"
        )
    else:
        cols_1[0].metric("No data yet", "-", delta="0 Win(s)", width="content")

    cols_1[1].markdown("""### Most Poles""")
    if not most_poles_d_df.empty:
        most_poles_d = most_poles_d_df.iloc[0]
        cols_1[1].metric(
            most_poles_d["driver"],
            most_poles_d["abbreviation"],
            delta=f"{most_poles_d["total_pole"]} Pole(s)",
            width="content"
        )
    else:
        cols_1[1].metric("No data yet", "-", delta="0 Pole(s)", width="content")

    cols_2 = st.columns(2)
    cols_2[0].markdown("""### Places Gained""")
    if not ovt_d_df.empty:
        most_gains_d = ovt_d_df.iloc[0]
        cols_2[0].metric(
            most_gains_d["driver"],
            most_gains_d["abbreviation"],
            delta=f"{most_gains_d["total_overtake"]} | +{most_gains_d["avg_overtake"]} (avg.)",
            width="content"
        )
    else:
        cols_2[0].metric("No data yet", "-", delta="0 | +0.0 (avg.)", width="content")

    cols_2[1].markdown("""### Places Lost""")
    if not ovt_d_df.empty:
        most_losses_d = ovt_d_df.iloc[-1]
        cols_2[1].metric(
            most_losses_d["driver"],
            most_losses_d["abbreviation"],
            delta=f"{most_losses_d["total_overtake"]} | {most_losses_d["avg_overtake"]} (avg.)",
            width="content"
        )
    else:
        cols_2[1].metric("No data yet", "-", delta="0 | 0.0 (avg.)", width="content")

drivers_progression_df = get_progression_d(season_ticker, connection)

with col_2_2:
    if st.session_state.round_slider_max == 0 or drivers_progression_df.empty:
        st.info("Drivers' Championship progression will appear after the first race result is available.")
    else:
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

        if st.session_state.round_slider_max > 1:
            st.slider(
                "",
                1,
                st.session_state.round_slider_max,
                key="round_slider_d"
            )

with col_2_3:
    st.markdown("Drivers' Standings")
    st.table(drivers_standings_df.head(5))
    with st.expander("More Drivers"):
        st.dataframe(drivers_standings_df[5:])

with col_3_1:
    selection_teams = st.pills("Filter", pills_t_map, default={"Top 3": 3}, key="teams_filter")
    st.markdown("---")
    cols = st.columns(2)

    cols[0].markdown("""### Most Wins""")
    if not most_win_t_df.empty:
        most_win_t = most_win_t_df.iloc[0]
        cols[0].metric(
            "In a season",
            most_win_t["team"],
            delta=f"{most_win_t["total_win"]} Win(s)",
            width="content"
        )
    else:
        cols[0].metric("In a season", "No data yet", delta="0 Win(s)", width="content")

    cols[1].markdown("""### Most Poles""")
    if not most_poles_t_df.empty:
        most_poles_t = most_poles_t_df.iloc[0]
        cols[1].metric(
            "In a season",
            most_poles_t["team"],
            delta=f"{most_poles_t["total_pole"]} Pole(s)",
            width="content"
        )
    else:
        cols[1].metric("In a season", "No data yet", delta="0 Pole(s)", width="content")

    st.markdown("""### Most DNFs""")
    if not most_dnfs_t_df.empty:
        most_dnfs_t = most_dnfs_t_df.iloc[0]
        st.metric(
            "In a season",
            most_dnfs_t["team"],
            delta=f"{-1 * most_dnfs_t["retired_count"]} DNF(s)",
            width="content"
        )
    else:
        st.metric("In a season", "No data yet", delta="0 DNF(s)", width="content")

teams_progression_df = get_progression_t(season_ticker, connection)

with col_3_2:
    if st.session_state.round_slider_max == 0 or teams_progression_df.empty:
        st.info("Teams' Championship progression will appear after the first race result is available.")
    else:
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

        if st.session_state.round_slider_max > 1:
            st.slider(
                "",
                1,
                st.session_state.round_slider_max,
                key="round_slider_t"
            )

with col_3_3:
    st.markdown("Teams' Standings")
    st.table(teams_standings_df.head(5))
    with st.expander("More Teams"):
        st.table(teams_standings_df[5:])

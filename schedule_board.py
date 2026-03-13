import streamlit as st
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import pydeck as pdk

from data_loaders import *


def get_map(df: pd.DataFrame):
    latitude = df['latitude'].iloc[0]
    longitude = df['longitude'].iloc[0]

    st.pydeck_chart(
        pdk.Deck(
            map_style=None,
            initial_view_state=pdk.ViewState(
                latitude=latitude,
                longitude=longitude,
                zoom=1,
                pitch=0,
                bearing=0,
            ),
            layers=[
                pdk.Layer(
                    "ScatterplotLayer",
                    data=df,
                    get_position="[longitude, latitude]",
                    get_color=[255, 0, 0, 160],
                    get_radius=320000,
                )
            ],
            tooltip=None
        )
    )


def is_in_current_week(date_to_check: datetime) -> bool:
    today = datetime.now()
    start_of_week = today - timedelta(days=today.weekday())  # Monday
    end_of_week = start_of_week + timedelta(days=7)
    return start_of_week <= date_to_check < end_of_week


def schedule_board():
    connection = get_connection()

    year_now = datetime.now().year

    current_season_rounds_df = get_current_season_rounds(connection)
    current_season_rounds_df.rename(
        columns={
            'number': 'NO.',
            'round_name': 'ROUND NAME',
            'date': 'DATE'
        }, inplace=True
    )
    remaining_season_rounds_df = current_season_rounds_df.loc[current_season_rounds_df['DATE'] > datetime.now().date(), ['NO.', 'ROUND NAME', 'DATE']]
    previous_season_rounds_df = current_season_rounds_df.loc[current_season_rounds_df['DATE'] < datetime.now().date(), ['NO.', 'ROUND NAME', 'DATE']]


    nearest_round_sessions_df = get_nearest_round_sessions(connection)
    nearest_round_sessions_df['timestamp_utc'] = nearest_round_sessions_df['timestamp'].apply(
        lambda value: value.replace(tzinfo=ZoneInfo('UTC'))
    )
    round_info_s = nearest_round_sessions_df.iloc[-1]

    last_winner_s = get_last_winner(connection)
    most_wins_s = get_most_wins(connection)

    timezone_options = {
        'UTC': ZoneInfo('UTC'),
        'CET': ZoneInfo('CET'),
    }

    map_df = pd.DataFrame([{
        'latitude': round_info_s['latitude'],
        'longitude': round_info_s['longitude']
    }])

    cols = st.columns([3, 1])
    col_1 = cols[0].container(border=False, height="stretch")
    col_2 = cols[1].container(border=False, height="stretch")

    with col_1:
        st.markdown(f"""
            <h2 style='text-align:center; margin: 0;'>
                {round_info_s['round_name']} {round_info_s['date'].year} - Round {round_info_s['number']}
            </h2>
            """, unsafe_allow_html=True)
        cols_1 = st.columns([1, 2, 1])

    col_1_1 = cols_1[0].container(border=True, height="stretch")
    col_1_2 = cols_1[1].container(border=True, height="stretch")
    col_1_3 = cols_1[2].container(border=True, height="stretch")

    with col_1_1:
        # cols_1_1 = st.columns(2)
        st.markdown(f"""## {round_info_s['circuit_name']}""")
        cols_1_2 = st.columns([4,1,4])


    col_1_2_1 = cols_1_2[0].container(height="stretch")
    col_1_2_2 = cols_1_2[2].container(height="stretch")

    with col_1_2_1:
        st.markdown("""### Most Wins""")
        st.metric(most_wins_s['driver'], most_wins_s['abbreviation'], delta=f"{most_wins_s['win_nums']} Win(s)*")
    with col_1_2_2:
        st.markdown("""### Recent""")
        st.metric(last_winner_s['driver'], last_winner_s['abbreviation'], delta=last_winner_s['date'].year)

    with col_1_2:
        get_map(map_df)

    with col_1_3:
        title_col, timezone_col = st.columns([3, 2])
        with title_col:
            st.markdown("""### Session Schedule""")
        with timezone_col:
            selected_timezone_label = st.selectbox(
                "Timezone",
                options=list(timezone_options.keys()),
                index=0,
                key="session_schedule_timezone",
                label_visibility="collapsed"
            )

        selected_timezone = timezone_options[selected_timezone_label]
        nearest_round_sessions_to_show_df = nearest_round_sessions_df[['type', 'timestamp_utc']].copy()
        nearest_round_sessions_to_show_df['timestamp_display'] = nearest_round_sessions_to_show_df['timestamp_utc'].apply(
            lambda value: value.astimezone(selected_timezone).strftime("%Y-%m-%d %H:%M")
        )
        nearest_round_sessions_to_show_df = nearest_round_sessions_to_show_df[['type', 'timestamp_display']]
        nearest_round_sessions_to_show_df.rename(
            columns={
                'type': 'SESSION',
                'timestamp_display': f'START TIME ({selected_timezone_label})'
            }, inplace=True
        )
        st.dataframe(nearest_round_sessions_to_show_df, hide_index=True)
        if pd.notna(round_info_s['scheduled_laps']) and int(round_info_s['scheduled_laps']) > 0:
            st.markdown("""### Number of Laps""")
            st.markdown(f"""
                        <h1 style='text-align:center; margin: 0;'>
                            {int(round_info_s['scheduled_laps'])}
                        </h1>
                        """, unsafe_allow_html=True)
    with col_2:
        st.markdown(f"""### """)
        st.markdown(f"""### F1 {year_now} Calendar""")
        st.write("Next Rounds")
        st.dataframe(remaining_season_rounds_df, hide_index=True)

        with st.expander("Previous Rounds"):
            st.dataframe(previous_season_rounds_df, hide_index=True)

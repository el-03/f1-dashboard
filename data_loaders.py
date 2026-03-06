import streamlit as st
import pandas as pd
import psycopg2
import os

from dotenv import load_dotenv


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


def query_data(query, conn):
    """Execute query and return DataFrame"""
    # Use the existing connection passed in
    try:
        return pd.read_sql(query, conn)
    except (psycopg2.InterfaceError, psycopg2.OperationalError):
        # Connection died — reconnect
        conn = get_connection()
        return pd.read_sql(query, conn)


# Loader: State - Latest Season
def get_latest_season(_conn) -> int:
    return query_data(f"""
    SELECT MAX(year) FROM formula_one.season;
    """, _conn)['max'][0]

# Loader: State - Round Number
@st.cache_data(ttl=600)
def get_round_num(selected_year, _conn) -> int:
    max_round = query_data(f"""
    SELECT MAX(r.number) FROM formula_one.race_result rr
    LEFT JOIN formula_one.round r ON 
      rr.round_id = r.id
    WHERE EXTRACT(YEAR FROM r.date) = {selected_year};""", _conn)['max'][0]

    return 0 if pd.isna(max_round) else int(max_round)


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


# Loader: Most Win
@st.cache_data(ttl=600)
def get_most_win_d(selected_year, _conn) -> pd.DataFrame:
    return query_data(f"""
        SELECT 
            d.abbreviation,
            d.forename || ' ' || d.surname as driver, 
            MAX(win_count) total_win
        FROM formula_one.driver_championship dc
        LEFT JOIN formula_one.driver AS d ON
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
    FROM formula_one.team_championship tc
    LEFT JOIN formula_one.team AS t ON
        tc.team_id = t.id
    WHERE year = {selected_year}
    GROUP BY t.name
    ORDER BY MAX(win_count) DESC
    LIMIT 1;
""", _conn)


# Loader: Most Pole
@st.cache_data(ttl=600)
def get_most_poles_d(selected_year, _conn) -> pd.DataFrame:
    return query_data(f"""
        SELECT
            d.abbreviation,
            d.forename || ' ' || d.surname driver,
            COUNT(*) total_pole
        FROM formula_one.qualifying_result qr
        LEFT JOIN formula_one.driver d ON
            qr.driver_id = d.id
        LEFT JOIN formula_one.season s ON
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
        FROM formula_one.qualifying_result qr
        LEFT JOIN formula_one.driver d ON
            qr.driver_id = d.id
        LEFT JOIN formula_one.team t ON
            qr.team_id = t.id
        LEFT JOIN formula_one.season s ON
            qr.season_id = s.id
        WHERE s.year = {selected_year} AND qr.position = 1
        GROUP BY t.name
        ORDER BY COUNT(*) DESC
        LIMIT 1;
    """, _conn)


# Loader: Team - Most DNFs
@st.cache_data(ttl=600)
def get_most_dnfs_t(selected_year, _conn) -> pd.DataFrame:
    return query_data(f"""
    SELECT t.name team, COUNT(*) retired_count FROM formula_one.race_result rr
    LEFT JOIN formula_one.team AS t ON
        rr.team_id = t.id
    LEFT JOIN formula_one.season AS s ON
        rr.season_id = s.id
    WHERE s.year = {selected_year}
        AND position_text = 'R' 
    GROUP BY year, t.name
    ORDER BY COUNT(*) DESC
    LIMIT 1;
""", _conn)


# Loader: Driver - Overtake
@st.cache_data(ttl=600)
def get_ovt_d(selected_year, _conn) -> pd.DataFrame:
    return query_data(f"""
    WITH cte_1 AS (
        SELECT
            d.abbreviation,
            d.forename || ' ' || d.surname driver, 
            (rr.grid_position - rr.position) overtake
        FROM formula_one.race_result rr
        LEFT JOIN formula_one.driver d ON
            rr.driver_id = d.id
        LEFT JOIN formula_one.season s ON
            rr.season_id = s.id
        WHERE s.year = {selected_year}
            AND rr.position_text ~ '^[0-9]+$'
    )
    SELECT abbreviation, driver, SUM(overtake) total_overtake, ROUND(AVG(overtake), 2) avg_overtake FROM cte_1
    GROUP BY abbreviation, driver
    ORDER BY avg_overtake DESC;""", _conn)


# Loader - Load Data: Drivers' Progression
@st.cache_data(ttl=600)
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


# Loader - Load Data: Teams' Progression
@st.cache_data(ttl=600)
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


# Loader - Load Data: Current Year's Rounds
@st.cache_data(ttl=600)
def get_current_season_rounds(_conn) -> pd.DataFrame:
    return query_data(f"""
    SELECT * FROM formula_one_views.current_season_round
    """, _conn)


@st.cache_data(ttl=600)
def get_nearest_round_sessions(_conn) -> pd.DataFrame:
    return query_data(f"""
        SELECT * FROM formula_one_views.current_season_session
        WHERE date > NOW()
          AND round_id = (
            SELECT MIN(round_id)
            FROM formula_one_views.current_season_session
            WHERE date > NOW()
          )
        ORDER BY date DESC;
        """, _conn)


def get_last_winner(_conn) -> pd.DataFrame:
    return query_data("""
                      WITH cte_1 AS (SELECT id, date
                      FROM formula_one.round
                      WHERE circuit_id = (
                          SELECT circuit_id
                          FROM formula_one_views.current_season_session
                          WHERE date
                          > NOW()
                          ORDER BY timestamp ASC
                          LIMIT 1
                          )
                      ORDER BY date DESC
                          LIMIT 1
                      OFFSET 1 ), cte_2 AS(
                      SELECT driver_id, cte_1.date
                      FROM formula_one.race_result rr
                          INNER JOIN cte_1
                      ON rr.round_id = cte_1.id
                      WHERE rr.position = 1
                          )
                      SELECT CONCAT(d.forename, ' ', d.surname) driver, d.abbreviation, cte_2.date
                      FROM formula_one.driver d
                               INNER JOIN cte_2 ON d.id = cte_2.driver_id;
                      """, _conn).squeeze()


def get_most_wins(_conn) -> pd.DataFrame:
    return query_data("""
                      WITH cte_1 AS (SELECT id
                                     FROM formula_one.round
                                     WHERE circuit_id = (SELECT circuit_id
                                                         FROM formula_one_views.current_season_session
                                                         WHERE date > NOW()
                      ORDER BY timestamp ASC
                          LIMIT 1
                          )
                          ),
                          cte_2 AS (
                      SELECT driver_id, COUNT (*) win_nums
                      FROM formula_one.race_result rr
                          INNER JOIN cte_1
                      ON rr.round_id = cte_1.id
                      WHERE rr.position = 1
                      GROUP BY driver_id
                      ORDER BY COUNT (*) DESC
                          LIMIT 1
                          )
                      SELECT CONCAT(d.forename, ' ', d.surname) driver, d.abbreviation, cte_2.win_nums
                      FROM formula_one.driver d
                               INNER JOIN cte_2 ON d.id = cte_2.driver_id;
                      """, _conn).squeeze()

import time
from datetime import datetime

import pandas as pd
import statsapi
import streamlit as st

SEASON = 2026
REFRESH_SECONDS = 300

TEAMS = {
    "Team 1": [
        "Bobby Witt Jr.",
        "Matt Olson",
        "Ketel Marte",
        "Eugenio Suárez",
        "William Contreras",
        "Juan Soto",
        "Aaron Judge",
        "Byron Buxton",
        "Hunter Goodman",
    ],
    "Team 2": [
        "Corey Seager",
        "Vladimir Guerrero Jr.",
        "Brandon Lowe",
        "Rafael Devers",
        "Cal Raleigh",
        "Yordan Alvarez",
        "Kyle Stowers",
        "Mike Trout",
        "Shohei Ohtani",
    ],
    "Team 3": [
        "Trevor Story",
        "Pete Alonso",
        "Lenyn Sosa",
        "José Ramírez",
        "Shea Langeliers",
        "Riley Greene",
        "Fernando Tatís Jr.",
        "Pete Crow-Armstrong",
        "Kyle Schwarber",
    ],
}


@st.cache_data(ttl=REFRESH_SECONDS)
def get_player_id(player_name: str):
    matches = statsapi.lookup_player(player_name)
    if not matches:
        return None

    active_matches = [p for p in matches if p.get("active")]
    if active_matches:
        return active_matches[0]["id"]

    return matches[0]["id"]


@st.cache_data(ttl=REFRESH_SECONDS)
def get_home_runs(player_id: int, season: int) -> int:
    data = statsapi.player_stat_data(
        player_id,
        group="hitting",
        type="season",
        season=season,
    )
    stats = data.get("stats", {})
    return int(stats.get("homeRuns", 0))


@st.cache_data(ttl=REFRESH_SECONDS)
def build_data(season: int):
    rows = []

    for team_name, players in TEAMS.items():
        for player_name in players:
            player_id = get_player_id(player_name)

            if player_id is None:
                rows.append(
                    {
                        "Team": team_name,
                        "Player": player_name,
                        "HR": None,
                        "Status": "Player not found",
                    }
                )
                continue

            try:
                hr = get_home_runs(player_id, season)
                rows.append(
                    {
                        "Team": team_name,
                        "Player": player_name,
                        "HR": hr,
                        "Status": "OK",
                    }
                )
            except Exception as exc:
                rows.append(
                    {
                        "Team": team_name,
                        "Player": player_name,
                        "HR": None,
                        "Status": f"Error: {exc}",
                    }
                )

    df = pd.DataFrame(rows)
    df["HR_sort"] = df["HR"].fillna(-1)

    overall = df.sort_values(["HR_sort", "Player"], ascending=[False, True]).drop(columns=["HR_sort"])

    team_totals = (
        df.assign(HR=df["HR"].fillna(0))
        .groupby("Team", as_index=False)["HR"]
        .sum()
        .sort_values("HR", ascending=False)
        .rename(columns={"HR": "Total HR"})
    )

    return overall, team_totals


def render_team_tables(overall_df: pd.DataFrame):
    for team_name in TEAMS.keys():
        team_df = overall_df[overall_df["Team"] == team_name].copy()
        team_total = int(team_df["HR"].fillna(0).sum())

        st.subheader(f"{team_name} — {team_total} HR")
        st.dataframe(
            team_df[["Player", "HR", "Status"]],
            use_container_width=True,
            hide_index=True,
        )


def main():
    st.set_page_config(page_title="MLB HR Tracker", layout="wide")
    st.title("⚾ Custom MLB Home Run Tracker")
    st.caption("Auto-refreshing scoreboard for your 3 custom teams")

    with st.sidebar:
        st.header("Settings")
        season = st.number_input("Season", min_value=2000, max_value=2100, value=SEASON, step=1)
        st.write(f"Refresh interval: {REFRESH_SECONDS} seconds")
        if st.button("Refresh now"):
            st.cache_data.clear()
            st.rerun()

    overall_df, team_totals_df = build_data(season)

    c1, c2, c3 = st.columns(3)
    with c1:
        leader = overall_df.dropna(subset=["HR"]).iloc[0]
        st.metric("Home Run Leader", leader["Player"], f"{int(leader['HR'])} HR")
    with c2:
        top_team = team_totals_df.iloc[0]
        st.metric("Top Team", top_team["Team"], f"{int(top_team['Total HR'])} HR")
    with c3:
        st.metric("Last Updated", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    st.subheader("Team Rankings")
    st.dataframe(team_totals_df, use_container_width=True, hide_index=True)

    st.subheader("Overall Leaderboard")
    st.dataframe(overall_df[["Player", "Team", "HR", "Status"]], use_container_width=True, hide_index=True)

    st.divider()
    render_team_tables(overall_df)

    st.markdown(
        f"<meta http-equiv='refresh' content='{REFRESH_SECONDS}'>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()

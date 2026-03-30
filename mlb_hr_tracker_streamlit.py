from datetime import datetime
from urllib.parse import quote

import pandas as pd
import requests
import streamlit as st

REFRESH_SECONDS = 300
CURRENT_SEASON = 2026

TEAMS = {
    "King Gup": [
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
    "Mr Robotsex": [
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
    "Gaycob": [
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

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


@st.cache_data(ttl=REFRESH_SECONDS)
def lookup_player_id(player_name: str):
    try:
        url = f"https://statsapi.mlb.com/api/v1/people/search?names={quote(player_name)}&sportIds=1"
        response = requests.get(url, headers=HEADERS, timeout=20)
        response.raise_for_status()
        data = response.json()

        people = data.get("people", [])
        if not people:
            return None

        active_people = [p for p in people if p.get("active")]
        player = active_people[0] if active_people else people[0]
        return player.get("id")
    except Exception:
        return None


@st.cache_data(ttl=REFRESH_SECONDS)
def get_hr(player_name: str):
    player_id = lookup_player_id(player_name)
    if not player_id:
        return None

    try:
        url = (
            f"https://statsapi.mlb.com/api/v1/people/{player_id}"
            f"?hydrate=stats(group=[hitting],type=[season],season={CURRENT_SEASON})"
        )
        response = requests.get(url, headers=HEADERS, timeout=20)
        response.raise_for_status()
        data = response.json()

        people = data.get("people", [])
        if not people:
            return None

        stats = people[0].get("stats", [])
        if not stats:
            return 0

        splits = stats[0].get("splits", [])
        if not splits:
            return 0

        stat_block = splits[0].get("stat", {})
        return int(stat_block.get("homeRuns", 0))
    except Exception:
        return None


def build_dataframe():
    rows = []

    for team_name, players in TEAMS.items():
        for player_name in players:
            hr = get_hr(player_name)
            rows.append(
                {
                    "Team": team_name,
                    "Player": player_name,
                    "HR": hr,
                    "Status": "OK" if hr is not None else "No data found",
                }
            )

    df = pd.DataFrame(rows)
    df["HR_sort"] = df["HR"].fillna(-1)

    overall = (
        df.sort_values(["HR_sort", "Player"], ascending=[False, True])
        .drop(columns=["HR_sort"])
        .reset_index(drop=True)
    )

    team_totals = (
        df.assign(HR=df["HR"].fillna(0))
        .groupby("Team", as_index=False)["HR"]
        .sum()
        .rename(columns={"HR": "Total HR"})
        .sort_values("Total HR", ascending=False)
        .reset_index(drop=True)
    )

    return overall, team_totals


st.set_page_config(page_title="MLB Home Run Tracker", layout="wide")

st.title("⚾ MLB Home Run Tracker")
st.caption(f"Live {CURRENT_SEASON} season-to-date home run tracker")

col_a, col_b = st.columns([1, 1])

with col_a:
    if st.button("Refresh now"):
        st.cache_data.clear()
        st.rerun()

with col_b:
    st.write(f"Refresh interval: {REFRESH_SECONDS} seconds")

with st.expander("Debug"):
    st.write("Season:", CURRENT_SEASON)
    st.write("Aaron Judge HR:", get_hr("Aaron Judge"))
    st.write("Shohei Ohtani HR:", get_hr("Shohei Ohtani"))
    st.write("Matt Olson HR:", get_hr("Matt Olson"))

overall_df, team_totals_df = build_dataframe()

valid_leaders = overall_df[overall_df["HR"].notna()].copy()
valid_leaders = valid_leaders.sort_values(["HR", "Player"], ascending=[False, True])

col1, col2, col3 = st.columns(3)

with col1:
    if not valid_leaders.empty:
        leader = valid_leaders.iloc[0]
        st.metric("Home Run Leader", leader["Player"], f"{int(leader['HR'])} HR")
    else:
        st.metric("Home Run Leader", "No data", "0 HR")

with col2:
    if not team_totals_df.empty:
        top_team = team_totals_df.iloc[0]
        st.metric("Top Team", top_team["Team"], f"{int(top_team['Total HR'])} HR")
    else:
        st.metric("Top Team", "No data", "0 HR")

with col3:
    st.metric("Last Updated", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

st.subheader("Team Rankings")
st.dataframe(team_totals_df, use_container_width=True, hide_index=True)

st.subheader("Overall Leaderboard")
st.dataframe(
    overall_df[["Player", "Team", "HR", "Status"]],
    use_container_width=True,
    hide_index=True,
)

for team_name in TEAMS:
    st.subheader(team_name)
    team_df = overall_df[overall_df["Team"] == team_name][["Player", "HR", "Status"]]
    st.dataframe(team_df, use_container_width=True, hide_index=True)

st.markdown(
    f"<meta http-equiv='refresh' content='{REFRESH_SECONDS}'>",
    unsafe_allow_html=True,
)

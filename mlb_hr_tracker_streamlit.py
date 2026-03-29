from datetime import datetime
import pandas as pd
import statsapi
import streamlit as st

REFRESH_SECONDS = 300
CURRENT_SEASON = int(statsapi.latest_season()["seasonId"])

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
    "Faggotron": [
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
def get_player_id(player_name):
    try:
        players = statsapi.lookup_player(player_name)
        if not players:
            return None

        active_players = [p for p in players if p.get("active")]
        player = active_players[0] if active_players else players[0]
        return player["id"]
    except Exception:
        return None


@st.cache_data(ttl=REFRESH_SECONDS)
def get_hr(player_name):
    player_id = get_player_id(player_name)
    if player_id is None:
        return None

    try:
        data = statsapi.player_stat_data(
            player_id,
            group="hitting",
            type="season",
            season=CURRENT_SEASON,
        )

        stats = data.get("stats", {})
        return int(stats.get("homeRuns", 0))
    except Exception:
        return None


@st.cache_data(ttl=REFRESH_SECONDS)
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


st.set_page_config(page_title="MLB HR Tracker", layout="wide")

st.title("⚾ MLB Home Run Tracker")
st.caption(f"Live {CURRENT_SEASON} season-to-date home run tracker")

if st.button("Refresh now"):
    st.cache_data.clear()
    st.rerun()

overall_df, team_totals_df = build_dataframe()
valid_leaders = overall_df.dropna(subset=["HR"])

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

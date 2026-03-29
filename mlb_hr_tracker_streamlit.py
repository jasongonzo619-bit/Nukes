from datetime import datetime
import pandas as pd
import statsapi
import streamlit as st

SEASON = 2026

TEAMS = {
    "Gup": [
        "Bobby Witt Jr.", "Matt Olson", "Ketel Marte", "Eugenio Suárez",
        "William Contreras", "Juan Soto", "Aaron Judge", "Byron Buxton",
        "Hunter Goodman"
    ],
    "Mr. Robotsex": [
        "Corey Seager", "Vladimir Guerrero Jr.", "Brandon Lowe", "Rafael Devers",
        "Cal Raleigh", "Yordan Alvarez", "Kyle Stowers", "Mike Trout",
        "Shohei Ohtani"
    ],
    "Faggotron": [
        "Trevor Story", "Pete Alonso", "Lenyn Sosa", "José Ramírez",
        "Shea Langeliers", "Riley Greene", "Fernando Tatís Jr.",
        "Pete Crow-Armstrong", "Kyle Schwarber"
    ],
}

def get_hr(name):
    try:
        players = statsapi.lookup_player(name)
        if not players:
            return None

        active_players = [p for p in players if p.get("active")]
        player = active_players[0] if active_players else players[0]
        player_id = player["id"]

        data = statsapi.player_stat_data(
            player_id,
            group="hitting",
            type="season",
            season=SEASON
        )

        return int(data.get("stats", {}).get("homeRuns", 0))
    except Exception:
        return None

rows = []
for team, players in TEAMS.items():
    for player in players:
        hr = get_hr(player)
        rows.append({
            "Team": team,
            "Player": player,
            "HR": hr,
            "Status": "OK" if hr is not None else "No data found"
        })

df = pd.DataFrame(rows)
df["HR_sort"] = df["HR"].fillna(-1)

overall = df.sort_values(
    ["HR_sort", "Player"],
    ascending=[False, True]
).drop(columns=["HR_sort"])

team_totals = (
    df.assign(HR=df["HR"].fillna(0))
    .groupby("Team", as_index=False)["HR"]
    .sum()
    .rename(columns={"HR": "Total HR"})
    .sort_values("Total HR", ascending=False)
)

st.set_page_config(page_title="MLB HR Tracker", layout="wide")
st.title("⚾ MLB Home Run Tracker")
st.write("Last updated:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

valid_leaders = overall.dropna(subset=["HR"])

st.subheader("Top Summary")
col1, col2 = st.columns(2)

with col1:
    if not valid_leaders.empty:
        leader = valid_leaders.iloc[0]
        st.metric("Home Run Leader", leader["Player"], f"{int(leader['HR'])} HR")
    else:
        st.metric("Home Run Leader", "No data", "0 HR")

with col2:
    if not team_totals.empty:
        top_team = team_totals.iloc[0]
        st.metric("Top Team", top_team["Team"], f"{int(top_team['Total HR'])} HR")
    else:
        st.metric("Top Team", "No data", "0 HR")

st.subheader("Team Rankings")
st.dataframe(team_totals, use_container_width=True, hide_index=True)

st.subheader("Overall Leaderboard")
st.dataframe(
    overall[["Player", "Team", "HR", "Status"]],
    use_container_width=True,
    hide_index=True
)

for team in TEAMS:
    st.subheader(team)
    st.dataframe(
        overall[overall["Team"] == team][["Player", "HR", "Status"]],
        use_container_width=True,
        hide_index=True
    )

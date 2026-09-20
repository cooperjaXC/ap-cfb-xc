"""
Render the most recent recorded week's XC standings as a Markdown table and drop it into the README
under the matching current-week graph - the README-friendly version of the console printout from
espn_api.pretty_print_week_data(), built purely from what's already stored in `data/`.

The README opts in with a pair of marker comments (see update_readme_table()); everything between
them is regenerated on each run, so a new week's table shows up with no hand-editing.
"""

import ast
import contextlib
import io
import os
import re

import numpy as np
import pandas as pd

import espn_api as epi
import store_data as sd

REPO_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(REPO_DIR, "data")
README_PATH = os.path.join(REPO_DIR, "README.md")

# When these don't score they're listed ahead of the other non-scoring conferences (as in the
# console printout)
CORE_CONFERENCES = ["SEC", "Big Ten", "ACC", "Big 12"]

_WEEK_FILE_RE = re.compile(r"^\d{4}_week_(?P<week>\d+|final)\.csv$")
_NUMPY_WRAPPER_RE = re.compile(r"np\.\w+\((.*?)\)")
_MARKDOWN_SPECIAL_RE = re.compile(r"([\\|*_`<])")
_NUMBER_WORDS = {4: "four", 5: "five"}


def latest_recorded_week(num_scoring_teams: int = 5, data_dir: str = DATA_DIR):
    """Return (year, week_token, csv_path) for the newest week stored under `data/`: the highest
    year that has any week files, and within it the Final poll if recorded, else the highest week
    number. `week_token` is the filename's suffix - a number, or 'final'."""
    team_dir = sd.quad if num_scoring_teams == 4 else sd.pent
    years = sorted((int(e) for e in os.listdir(data_dir) if e.isdigit()), reverse=True)
    for year in years:
        week_dir = os.path.join(data_dir, str(year), team_dir)
        if not os.path.isdir(week_dir):
            continue
        weeks = [m["week"] for f in os.listdir(week_dir) if (m := _WEEK_FILE_RE.match(f))]
        if weeks:
            latest = "final" if "final" in weeks else max(weeks, key=int)
            return year, latest, os.path.join(week_dir, f"{year}_week_{latest}.csv")
    raise FileNotFoundError(f"No {team_dir} week files found under {data_dir}")


def _week_label(week_token: str) -> str:
    return {"final": "Final", "1": "Preseason"}.get(week_token, f"Week {week_token}")


def _parse_cell(cell):
    """Turn a stored "('Texas', 1)" / "('SEC', np.int64(27))" cell back into a real tuple, or NaN
    for a blank cell."""
    if pd.isna(cell):
        return np.nan
    return ast.literal_eval(_NUMPY_WRAPPER_RE.sub(r"\1", str(cell)))


def _load_week(csv_path: str):
    """Rebuild what the weekly run originally had in memory from its stored CSV: a {conference:
    score-or-'DNS'} dict and a DataFrame of each conference's (team, AP rank) tuples, best first."""
    raw = pd.read_csv(csv_path, header=None)
    header = [_parse_cell(cell) for cell in raw.iloc[0]]
    teams_df = pd.DataFrame(
        {
            conf: [_parse_cell(cell) for cell in raw.iloc[1:, col]]
            for col, (conf, _) in enumerate(header)
        }
    )
    return dict(header), teams_df


def _ordinal(n: int) -> str:
    suffix = "th" if 11 <= n % 100 <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def _place_label(place) -> str:
    """'1st', or 'T-2nd' for a finishing place still tied after the 6th-runner tiebreaker."""
    place = float(place)
    return _ordinal(int(place)) if place.is_integer() else f"T-{_ordinal(int(place))}"


def _fmt_num(value) -> str:
    return str(int(value)) if float(value).is_integer() else str(value)


def _escape(text: str) -> str:
    return _MARKDOWN_SPECIAL_RE.sub(r"\\\1", text)


def build_latest_week_table(num_scoring_teams: int = 5, data_dir: str = DATA_DIR) -> str:
    """Markdown for the newest stored week's XC standings: every conference with a ranked team as a
    column (scorers in finishing order, then those marked DNS), each conference's teams (with AP
    ranking) as rows, and the teams that don't count toward the score - starting with the tiebreaking
    runner, or every team of a conference that didn't score - italicized, with a dashed divider
    after the scoring rows."""
    year, week_token, csv_path = latest_recorded_week(num_scoring_teams, data_dir)
    scores, teams_df = _load_week(csv_path)

    # Reuse the pipeline's own scoring/tiebreak logic so the order matches the stored graphs exactly
    with contextlib.redirect_stdout(io.StringIO()):
        order_df = epi.conference_scoring_order(
            scores, teams_df, scoring_teams=num_scoring_teams
        )
    places = dict(zip(order_df["conference"], order_df["place"]))
    teams = {c: [t for t in teams_df[c] if isinstance(t, tuple)] for c in teams_df.columns}
    # Every conference with a ranked team gets a column: the scorers in finishing order, then those
    # that didn't score - the core four first, then the rest by their best-ranked team
    unscored = sorted(
        (c for c in teams if c not in places),
        key=lambda c: (
            (0, CORE_CONFERENCES.index(c))
            if c in CORE_CONFERENCES
            else (1, teams[c][0][1])
        ),
    )
    columns = list(order_df["conference"]) + unscored

    header = ["Pos"] + [
        f"{_place_label(places[c])} · {c}" if c in places else c for c in columns
    ]
    score_row = ["**Score**"] + [
        f"**{_fmt_num(scores[c])}**" if c in places else "DNS" for c in columns
    ]
    rows = [header, score_row]
    n_rows = max(len(t) for t in teams.values())
    for i in range(n_rows):
        if i == num_scoring_teams:
            rows.append([""] + ["———"] * len(columns))
        cells = [str(i + 1)]
        for c in columns:
            if i < len(teams[c]):
                name, rank = teams[c][i]
                text = f"{_escape(name)} ({_fmt_num(rank)})"
                counts_toward_score = c in places and i < num_scoring_teams
                cells.append(text if counts_toward_score else f"*{text}*")
            else:
                cells.append("")
        rows.append(cells)

    table = [f"| {' | '.join(row)} |" for row in rows]
    table.insert(1, "|" + ":---:|" + ":---|" * len(columns))

    n_word = _NUMBER_WORDS.get(num_scoring_teams, str(num_scoring_teams))
    runner = _ordinal(num_scoring_teams + 1)
    return "\n".join(
        [
            f"**{year} {_week_label(week_token)}** — {num_scoring_teams}-team XC standings",
            "",
            *table,
            "",
            f"<sub>Each team is shown with its AP ranking. A conference's score is the sum of its "
            f"top {n_word} teams' rankings - lowest score wins, and ties are broken by each "
            f"conference's {runner} runner. Italicized teams don't count toward the score; DNS "
            f"means the conference didn't have enough ranked teams to score (listed after the "
            f"scoring conferences).</sub>",
        ]
    )


def update_readme_table(
    num_scoring_teams: int = 5, readme_path: str = README_PATH
) -> str:
    """Regenerate the table between this scoring mode's marker comments in the README:
    `<!-- XC-TABLE-5-TEAM:START -->` ... `<!-- XC-TABLE-5-TEAM:END -->` (4-team for 4). Line endings
    are preserved, and the file is only rewritten if the table actually changed. Returns the
    Markdown that was inserted."""
    start = f"<!-- XC-TABLE-{num_scoring_teams}-TEAM:START -->"
    end = f"<!-- XC-TABLE-{num_scoring_teams}-TEAM:END -->"
    with open(readme_path, encoding="utf-8", newline="") as f:
        readme = f.read()
    marker_pattern = re.compile(re.escape(start) + r".*?" + re.escape(end), re.DOTALL)
    if not marker_pattern.search(readme):
        raise ValueError(f"{start} / {end} markers not found in {readme_path}")

    newline = "\r\n" if "\r\n" in readme else "\n"
    table = build_latest_week_table(num_scoring_teams)
    block = newline.join([start, table.replace("\n", newline), end])
    updated = marker_pattern.sub(lambda _: block, readme)
    if updated != readme:
        with open(readme_path, "w", encoding="utf-8", newline="") as f:
            f.write(updated)
    print(f"README {num_scoring_teams}-team XC table is up to date.")
    return table


if __name__ == "__main__":
    update_readme_table()

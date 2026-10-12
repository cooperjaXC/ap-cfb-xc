"""
Render the most recent recorded week's XC standings as a Markdown table and drop it into the README
under the matching current-week graph - the README-friendly version of the console printout from
espn_api.pretty_print_week_data(), built purely from what's already stored in `data/`.

Each team and each conference score is annotated with a Movement Indicator (GitHub issue #30): how far
it moved since the prior week's poll. Preseason is never compared against, so Week 2 (and the
Preseason table itself) shows no indicators.

The README opts in with a pair of marker comments (see update_readme_table()); everything between
them is regenerated on each run, so a new week's table shows up with no hand-editing.

Layout of this module, from lowest to highest level:
  - I/O: locating and loading stored weeks (`stored_week_tokens`, `load_stored_week`, ...)
  - pure helpers: movement math/formatting, cell formatting (`format_movement`, ...)
  - `build_week_table`: pure rendering of one `StoredWeek` (+ optional prior week) to Markdown
  - `build_latest_week_table` / `update_readme_table`: glue that does the file I/O
"""

import ast
import contextlib
import io
import os
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Union

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

# The Preseason poll is stored as week 1. It is never used as the "prior week" for a comparison:
# every season is distinct and new.
PRESEASON_WEEK_TOKEN = "1"

# Movement Indicators (GitHub issue #30)
UP = "▲"
DOWN = "▼"
UNCHANGED = "–"  # en dash (U+2013), not a hyphen
NOT_RANKED = "NR"
# Keeps an indicator on the same line as the rank it belongs to instead of wrapping alone
NBSP = "&nbsp;"

_WEEK_FILE_RE = re.compile(r"^\d{4}_week_(?P<week>\d+|final)\.csv$")
_NUMPY_WRAPPER_RE = re.compile(r"np\.\w+\((.*?)\)")
_MARKDOWN_SPECIAL_RE = re.compile(r"([\\|*_`<])")
_NUMBER_WORDS = {4: "four", 5: "five"}

Score = Union[int, float, str]  # a conference's XC score, or "DNS"
Team = Tuple[str, float]  # (team name, AP rank)


@dataclass(frozen=True, eq=False)
class StoredWeek:
    """One week of results as stored under `data/`: the same two things the weekly run had in memory."""

    year: int
    token: str  # filename suffix: a week number, or "final"
    scores: Dict[str, Score]  # {conference: XC score or "DNS"}
    teams_df: pd.DataFrame  # one column per conference of (team, AP rank) tuples, best first

    def teams_by_conference(self) -> Dict[str, List[Team]]:
        return {
            conf: [t for t in self.teams_df[conf] if isinstance(t, tuple)]
            for conf in self.teams_df.columns
        }

    def team_ranks(self) -> Dict[str, float]:
        """{team name: AP rank}, including the 'others receiving votes' ranks."""
        return {
            name: rank
            for teams in self.teams_by_conference().values()
            for name, rank in teams
        }


# ----------------------------------------------------------------------------------------------
# Locating and loading stored weeks
# ----------------------------------------------------------------------------------------------


def _team_dir(num_scoring_teams: int) -> str:
    return sd.quad if num_scoring_teams == 4 else sd.pent


def _week_csv_path(
    year: int, week_token: str, num_scoring_teams: int, data_dir: str = DATA_DIR
) -> str:
    return os.path.join(
        data_dir,
        str(year),
        _team_dir(num_scoring_teams),
        f"{year}_week_{week_token}.csv",
    )


def stored_week_tokens(
    year: int, num_scoring_teams: int = 5, data_dir: str = DATA_DIR
) -> List[str]:
    """Week tokens (numbers as strings, and/or 'final') that have a CSV stored for `year`."""
    week_dir = os.path.join(data_dir, str(year), _team_dir(num_scoring_teams))
    if not os.path.isdir(week_dir):
        return []
    return [m["week"] for f in os.listdir(week_dir) if (m := _WEEK_FILE_RE.match(f))]


def latest_recorded_week(num_scoring_teams: int = 5, data_dir: str = DATA_DIR):
    """Return (year, week_token, csv_path) for the newest week stored under `data/`: the highest
    year that has any week files, and within it the Final poll if recorded, else the highest week
    number. `week_token` is the filename's suffix - a number, or 'final'."""
    years = sorted((int(e) for e in os.listdir(data_dir) if e.isdigit()), reverse=True)
    for year in years:
        weeks = stored_week_tokens(year, num_scoring_teams, data_dir)
        if weeks:
            latest = "final" if "final" in weeks else max(weeks, key=int)
            return (
                year,
                latest,
                _week_csv_path(year, latest, num_scoring_teams, data_dir),
            )
    raise FileNotFoundError(
        f"No {_team_dir(num_scoring_teams)} week files found under {data_dir}"
    )


def previous_comparable_week_token(
    year: int, week_token: str, num_scoring_teams: int = 5, data_dir: str = DATA_DIR
) -> Optional[str]:
    """The stored week to compare `week_token` against: the most recent earlier week of the same
    year, excluding the Preseason poll. None when there isn't one (Preseason, Week 2, or nothing
    earlier is stored), in which case no Movement Indicators are shown."""
    numbered = sorted(
        int(t)
        for t in stored_week_tokens(year, num_scoring_teams, data_dir)
        if t.isdigit() and t != PRESEASON_WEEK_TOKEN
    )
    if week_token == "final":
        earlier = numbered
    else:
        earlier = [n for n in numbered if n < int(week_token)]
    return str(max(earlier)) if earlier else None


def _parse_cell(cell):
    """Turn a stored "('Texas', 1)" / "('SEC', np.int64(27))" cell back into a real tuple, or NaN
    for a blank cell."""
    if pd.isna(cell):
        return np.nan
    return ast.literal_eval(_NUMPY_WRAPPER_RE.sub(r"\1", str(cell)))


def load_stored_week(
    year: int, week_token: str, num_scoring_teams: int = 5, data_dir: str = DATA_DIR
) -> StoredWeek:
    """Rebuild what the weekly run originally had in memory from its stored CSV."""
    raw = pd.read_csv(
        _week_csv_path(year, week_token, num_scoring_teams, data_dir), header=None
    )
    header = [_parse_cell(cell) for cell in raw.iloc[0]]
    teams_df = pd.DataFrame(
        {
            conf: [_parse_cell(cell) for cell in raw.iloc[1:, col]]
            for col, (conf, _) in enumerate(header)
        }
    )
    return StoredWeek(
        year=year, token=week_token, scores=dict(header), teams_df=teams_df
    )


# ----------------------------------------------------------------------------------------------
# Pure formatting helpers
# ----------------------------------------------------------------------------------------------


def _week_label(week_token: str) -> str:
    return {"final": "Final", PRESEASON_WEEK_TOKEN: "Preseason"}.get(
        week_token, f"Week {week_token}"
    )


def _ordinal(n: int) -> str:
    suffix = (
        "th" if 11 <= n % 100 <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    )
    return f"{n}{suffix}"


def _place_label(place) -> str:
    """'1st', or 'T-2nd' for a finishing place still tied after the 6th-runner tiebreaker."""
    place = float(place)
    return _ordinal(int(place)) if place.is_integer() else f"T-{_ordinal(int(place))}"


def _fmt_num(value) -> str:
    return str(int(value)) if float(value).is_integer() else str(value)


def _escape(text: str) -> str:
    return _MARKDOWN_SPECIAL_RE.sub(r"\\\1", text)


def format_movement(prior, current) -> str:
    """The Movement Indicator for a move from `prior` to `current`, where a lower number is better
    (an AP rank, or a conference's XC score). `prior` is None/NaN/'DNS' if it had no value last week.
    Moves are exact - tied ranks are averaged, so a move can be fractional - and never rounded.

    >>> format_movement(3, 1)
    '▲2'
    >>> format_movement(1, 4)
    '▼3'
    >>> format_movement(39.5, 37)
    '▲2.5'
    >>> format_movement(12, 12)
    '–'
    >>> format_movement(None, 12)
    'NR'
    >>> format_movement("DNS", 40)
    'NR'
    """
    if prior is None or isinstance(prior, str) or pd.isna(prior):
        return NOT_RANKED
    delta = round(float(prior) - float(current), 6)
    if delta == 0:
        return UNCHANGED
    return f"{UP if delta > 0 else DOWN}{_fmt_num(abs(delta))}"


def _with_movement(
    text: str, indicator: Optional[str], parenthesize: bool = False
) -> str:
    """`text` followed by its Movement Indicator on a non-breaking space; unchanged if None.
    `parenthesize` sets the indicator off in parentheses, so it reads apart from a number it
    would otherwise run into (a conference's summed score).

    >>> _with_movement("Georgia (1)", "▲1")
    'Georgia (1)&nbsp;▲1'
    >>> _with_movement("**36**", "▼8", parenthesize=True)
    '**36**&nbsp;(▼8)'
    >>> _with_movement("DNS", None)
    'DNS'
    """
    if indicator is None:
        return text
    return f"{text}{NBSP}({indicator})" if parenthesize else f"{text}{NBSP}{indicator}"


def _conference_columns(
    teams: Dict[str, List[Team]], order_df: pd.DataFrame
) -> List[str]:
    """Every conference with a ranked team: the scorers in finishing order, then those that didn't
    score - the core four first, then the rest by their best-ranked team."""
    scored = set(order_df["conference"])
    unscored = sorted(
        (c for c in teams if c not in scored),
        key=lambda c: (
            (0, CORE_CONFERENCES.index(c))
            if c in CORE_CONFERENCES
            else (1, teams[c][0][1])
        ),
    )
    return list(order_df["conference"]) + unscored


def _footnote(num_scoring_teams: int, with_movement: bool) -> str:
    n_word = _NUMBER_WORDS.get(num_scoring_teams, str(num_scoring_teams))
    runner = _ordinal(num_scoring_teams + 1)
    note = (
        f"Each team is shown with its AP ranking. A conference's score is the sum of its "
        f"top {n_word} teams' rankings - lowest score wins, and ties are broken by each "
        f"conference's {runner} runner. Italicized teams don't count toward the score; DNS "
        f"means the conference didn't have enough ranked teams to score (listed after the "
        f"scoring conferences)."
    )
    if with_movement:
        note += (
            f" {UP}/{DOWN} is how many spots a team moved since last week's poll (a "
            f"conference's score change is shown in parentheses; a lower score is better, so a "
            f"falling score is {UP}). {UNCHANGED} means unchanged and {NOT_RANKED} means it "
            f"wasn't ranked or receiving votes last week."
        )
    return f"<sub>{note}</sub>"


# ----------------------------------------------------------------------------------------------
# Table rendering
# ----------------------------------------------------------------------------------------------


def build_week_table(
    week: StoredWeek,
    num_scoring_teams: int = 5,
    previous_week: Optional[StoredWeek] = None,
) -> str:
    """Markdown for one week's XC standings: every conference with a ranked team as a column
    (scorers in finishing order, then those marked DNS), each conference's teams (with AP ranking)
    as rows, and the teams that don't count toward the score - starting with the tiebreaking
    runner, or every team of a conference that didn't score - italicized, with a dashed divider
    after the scoring rows.

    When `previous_week` is given, each team and each conference score is followed by a Movement
    Indicator comparing it with that week. Pure: does no file I/O."""
    # Reuse the pipeline's own scoring/tiebreak logic so the order matches the stored graphs exactly
    with contextlib.redirect_stdout(io.StringIO()):
        order_df = epi.conference_scoring_order(
            week.scores, week.teams_df, scoring_teams=num_scoring_teams
        )
    places = dict(zip(order_df["conference"], order_df["place"]))
    teams = week.teams_by_conference()
    columns = _conference_columns(teams, order_df)

    prior_ranks = previous_week.team_ranks() if previous_week else None
    prior_scores = previous_week.scores if previous_week else None

    def team_movement(name: str, rank: float) -> Optional[str]:
        if prior_ranks is None:
            return None
        return format_movement(prior_ranks.get(name), rank)

    def score_movement(conference: str) -> Optional[str]:
        if prior_scores is None:
            return None
        return format_movement(prior_scores.get(conference), week.scores[conference])

    header = ["Pos"] + [
        f"{_place_label(places[c])} · {c}" if c in places else c for c in columns
    ]
    score_row = ["**Score**"] + [
        _with_movement(
            f"**{_fmt_num(week.scores[c])}**", score_movement(c), parenthesize=True
        )
        if c in places
        else "DNS"
        for c in columns
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
                text = _with_movement(
                    f"{_escape(name)} ({_fmt_num(rank)})", team_movement(name, rank)
                )
                counts_toward_score = c in places and i < num_scoring_teams
                cells.append(text if counts_toward_score else f"*{text}*")
            else:
                cells.append("")
        rows.append(cells)

    table = [f"| {' | '.join(row)} |" for row in rows]
    table.insert(1, "|" + ":---:|" + ":---|" * len(columns))

    return "\n".join(
        [
            f"**{week.year} {_week_label(week.token)}** — "
            f"{num_scoring_teams}-team XC standings",
            "",
            *table,
            "",
            _footnote(num_scoring_teams, with_movement=previous_week is not None),
        ]
    )


def build_latest_week_table(
    num_scoring_teams: int = 5,
    data_dir: str = DATA_DIR,
    show_movement: bool = True,
) -> str:
    """Markdown for the newest stored week's XC standings (see build_week_table()), with Movement
    Indicators against the prior comparable week unless `show_movement` is False or there is none."""
    year, week_token, _ = latest_recorded_week(num_scoring_teams, data_dir)
    week = load_stored_week(year, week_token, num_scoring_teams, data_dir)

    previous_week = None
    if show_movement:
        previous_token = previous_comparable_week_token(
            year, week_token, num_scoring_teams, data_dir
        )
        if previous_token is not None:
            previous_week = load_stored_week(
                year, previous_token, num_scoring_teams, data_dir
            )
    return build_week_table(week, num_scoring_teams, previous_week)


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

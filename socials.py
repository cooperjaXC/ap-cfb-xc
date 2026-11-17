"""
Social media posts for the weekly AP XC results.

Three parts, top to bottom:
  - X (Twitter) credentials and a read-only connection check
  - platform-independent post text: reads `data/`, finds what is interesting about a week against
    the polls and seasons before it, and writes a short post (`compose_post()`)
  - posting to X (`post_to_x()`), a dry run unless told otherwise

    python socials.py                          print the drafted post for the newest week
    python socials.py preview --season 2025    draft every week of a season
    python socials.py check                    test the X credentials (read-only requests)
    python socials.py post                     dry run of the real post; add --yes to publish
    python socials.py delete <post id>         delete a post (e.g. a test post)

Credentials live outside the repo, in `~/secrets.toml` (on Windows: C:\\Users\\<you>\\secrets.toml),
copied from the app in the X Developer Console (the app must be attached to a pay-per-use Project):

    [twitter]
    consumer_key = "..."   # API Key
    secret_key = "..."     # API Key Secret
    bearer_token = "..."   # optional; lets the check make an app-level read without user tokens
    access_token = "..."         # Access Token; needed to act as the account (posting)
    access_token_secret = "..."  # Access Token Secret; generate both while logged in as @ap_cfb_xc

`consumer_key` and `secret_key` are required. Access Tokens are tied to the app that created them,
so tokens from an older app will not work with a new app's consumer key. (Older `token` /
`token_secret` entries are deliberately ignored so they can't be mixed with a newer app.)
"""

import argparse
import contextlib
import dataclasses
import datetime
import functools
import io
import json
import os
import random
import re
import sys
import tomllib
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

import pandas as pd
import requests
import tweepy
from requests_oauthlib import OAuth1

import espn_api as epi
import readme_table as rt

SECRETS_PATH = os.path.expanduser("~/secrets.toml")
TWITTER_SECTION = "twitter"
REQUIRED_KEYS = ("consumer_key", "secret_key")
OPTIONAL_KEYS = ("bearer_token", "access_token", "access_token_secret")
EXPECTED_USERNAME = "ap_cfb_xc"


class MissingCredentialsError(RuntimeError):
    """The secrets file, its [twitter] section, or a required key is absent or empty."""


def load_twitter_credentials(secrets_path: str = SECRETS_PATH) -> Dict[str, str]:
    """Read the `[twitter]` section of the secrets TOML file. Returns every non-empty key among
    REQUIRED_KEYS and OPTIONAL_KEYS. Raises MissingCredentialsError (never echoing any secret
    value) if the file, the section, or a required key is missing."""
    if not os.path.exists(secrets_path):
        raise MissingCredentialsError(f"No secrets file found at {secrets_path}.")
    with open(secrets_path, "rb") as file:
        config = tomllib.load(file)
    section = config.get(TWITTER_SECTION)
    if not isinstance(section, dict):
        raise MissingCredentialsError(
            f"No [{TWITTER_SECTION}] section in {secrets_path}."
        )
    creds = {
        k: section[k].strip()
        for k in REQUIRED_KEYS + OPTIONAL_KEYS
        if isinstance(section.get(k), str) and section[k].strip()
    }
    missing = [k for k in REQUIRED_KEYS if k not in creds]
    if missing:
        raise MissingCredentialsError(
            f"[{TWITTER_SECTION}] in {secrets_path} is missing or has empty values for: "
            f"{', '.join(missing)}. Values must be quoted strings."
        )
    return creds


def get_twitter_client(
    creds: Optional[Dict[str, str]] = None, return_type=tweepy.Response
) -> tweepy.Client:
    """An X API v2 client built from whatever credentials are available. With a bearer token it can
    make app-level requests; with access_token/access_token_secret too it can act as the user (pass
    `user_auth=True` on user-context calls). `return_type` is fixed per client in tweepy; pass
    requests.Response to get raw HTTP responses."""
    creds = creds or load_twitter_credentials()
    return tweepy.Client(
        bearer_token=creds.get("bearer_token"),
        consumer_key=creds["consumer_key"],
        consumer_secret=creds["secret_key"],
        access_token=creds.get("access_token"),
        access_token_secret=creds.get("access_token_secret"),
        return_type=return_type,
    )


def _explain_http_error(err: tweepy.errors.HTTPException) -> None:
    """Print a one-line diagnosis plus X's own error body for a failed request."""
    status = err.response.status_code
    hints = {
        401: "Credentials rejected. Re-copy the values; Access Tokens must come from the same "
        "app as the consumer key.",
        402: "Payment required. The X developer account has no credits.",
        403: "Forbidden. Usually the app isn't attached to a pay-per-use Project (see "
        "'reason' below), or the account has no credits.",
        429: "Rate limited. Try again later.",
    }
    print(f"X API returned HTTP {status}. {hints.get(status, '')}".strip())
    print(err.response.text[:500])


def check_app_connection(client: tweepy.Client, username: str) -> Optional[str]:
    """App-level check (bearer token): look up `username`'s public profile. Proves the app is
    enrolled and the account exists; it cannot prove the user tokens belong to that account.
    Returns the account's user id on success, else None."""
    try:
        resp = client.get_user(username=username)
        resp.raise_for_status()
    except tweepy.errors.HTTPException as err:
        _explain_http_error(err)
        return None
    except requests.RequestException as err:
        print(f"Could not reach the X API: {err}")
        return None
    user = resp.json().get("data")
    if not user:
        print(f"App-level request worked, but no account named @{username} was found.")
        return None
    print(f"App-level check OK: @{user['username']} ({user['name']}, id {user['id']}).")
    return user["id"]


def _explain_token_owner(token: str, account_id: Optional[str]) -> None:
    """An X Access Token starts with the numeric id of the account it was issued for (followed by a
    dash and a random part). Only that public id is printed, never any part of the secret."""
    token_user_id = token.split("-", 1)[0] if "-" in token else None
    if not token_user_id or not token_user_id.isdigit():
        print("The token doesn't look like a standard Access Token (expected '<digits>-<random>').")
    elif account_id and token_user_id != account_id:
        print(
            f"The token was issued for account id {token_user_id}, not the @{EXPECTED_USERNAME} "
            f"id {account_id}. It was generated while logged in as a different account."
        )
    elif account_id:
        print(
            f"The token is for the right account (id {token_user_id}), so the mismatch is "
            "between the token and the consumer key/secret: they come from different apps, or "
            "were regenerated after the token was made."
        )


def check_user_connection(
    client: tweepy.Client, expected_username: str
) -> Optional[bool]:
    """User-level check (Access Token): GET /2/users/me and confirm it is `expected_username`.
    Also prints the token's access level, since posting requires read-write.
    Returns True when ready to post, False when the request authenticated but the token is for the
    wrong account or is read-only, and None when the request itself failed (e.g. a 401)."""
    try:
        resp = client.get_me(user_auth=True)
        resp.raise_for_status()
    except tweepy.errors.HTTPException as err:
        _explain_http_error(err)
        return None
    except requests.RequestException as err:
        print(f"Could not reach the X API: {err}")
        return None
    user = resp.json()["data"]
    access_level = resp.headers.get("x-access-level", "not reported")
    print(f"Authenticated as: @{user['username']} ({user['name']}, id {user['id']})")
    print(f"Token access level: {access_level}  (posting requires read-write)")
    if user["username"].lower() != expected_username.lower():
        print(
            f"MISMATCH: expected @{expected_username}. The Access Token was generated while "
            "logged in as a different account; regenerate it as the right one."
        )
        return False
    print(f"OK: this is the @{expected_username} account on file.")
    # The header reads "read", "read-write", or "read-write-directmessages". Only a token that
    # X explicitly reports as lacking write is treated as a failure; "not reported" is let through.
    if access_level != "not reported" and "write" not in access_level:
        print(
            "NOT READY TO POST: this token is read-only. In the X Developer Console set the "
            "app's permissions to Read and write, then regenerate the Access Token and Secret "
            "(existing tokens keep the permission they were created with)."
        )
        return False
    return True


def check_twitter_connection(expected_username: str = EXPECTED_USERNAME) -> bool:
    """Run every check the stored credentials allow. Returns True only when the user-level check
    ran and confirmed the @`expected_username` account (i.e. the setup is ready to post)."""
    try:
        creds = load_twitter_credentials()
    except MissingCredentialsError as err:
        print(f"Credentials problem: {err}")
        return False
    client = get_twitter_client(creds, return_type=requests.Response)

    account_id = None
    if "bearer_token" in creds:
        account_id = check_app_connection(client, expected_username)
    else:
        print("No bearer_token in secrets.toml; skipping the app-level check.")

    if "access_token" in creds and "access_token_secret" in creds:
        ready = check_user_connection(client, expected_username)
        if ready is None:  # the request failed outright, so say which account the token is for
            _explain_token_owner(creds["access_token"], account_id)
        return bool(ready)
    print(
        "No access_token/access_token_secret in secrets.toml, so the account itself can't be verified yet. "
        "In the X Developer Console, open the app's Keys and tokens page and generate the "
        f"Access Token and Secret while logged in as @{expected_username}, with the app set "
        "to Read and write."
    )
    return False


# ==============================================================================================
# Post text: platform-independent
#
# Nothing below this banner (until the "Posting to X" banner) knows about any platform. It reads
# the stored results in `data/`, works out what is interesting about a week compared with the
# polls and seasons before it, and writes a short post. `compose_post()` is the entry point.
#
# How a post is built:
#   1. a headline sentence (who leads, and whether that is new, a streak, a tie, ...)
#   2. a one-line standings summary
#   3. the most interesting "storylines" that still fit, chosen by priority
# Each storyline comes from one small builder function in STORYLINE_BUILDERS; add, remove or
# reorder builders there. Wording lives in PHRASES, thresholds and limits in PostConfig.
# ==============================================================================================

IMAGES_DIR = os.path.join(rt.REPO_DIR, "images")
POST_LOG_PATH = os.path.join(rt.DATA_DIR, "social_post_log.json")

# Renamed/realigned conferences that count as one conference when looking back through history
# (same idea as graph_data.CROSS_SEASON_CONFERENCE_MERGES; only used for comparisons, never display)
HISTORY_ALIASES = {"Pac-10": "Pac-12", "Big East": "American"}

# Hashtags. A conference or team named in a post can add its hashtag (see build_hashtags()).
# Conferences use the tags fans actually follow; a conference missing here gets none.
CONFERENCE_HASHTAGS = {
    "SEC": "#SEC",
    "Big Ten": "#B1G",
    "Big 12": "#Big12",
    "ACC": "#ACC",
    "Pac-12": "#Pac12",
    "Pac-10": "#Pac10",
    "American": "#AmericanFB",
    "Big East": "#BigEast",
    "Mountain West": "#MountainWest",
    "Sun Belt": "#SunBelt",
    "MAC": "#MACtion",
    "CUSA": "#CUSA",
}
# Teams default to their name as a tag ("South Carolina" -> #SouthCarolina, "Boise St" ->
# #BoiseState). List a team here to use something else, e.g. {"Alabama": "#RollTide"}.
TEAM_HASHTAGS = {"N Dakota St": "#NDSU", "Texas A&M": "#TexasAM"}

# Short forms for the sentences, used once the full name has appeared in the standings line
# (the standings line itself always spells names out).
ABBREVIATIONS = {"Big Ten": "B1G"}

# How a conference is written mid-sentence. Anything not listed becomes "the <shortName>".
CONFERENCE_NAMES = {"FBS Indep.": "the FBS Independents"}

# Wording. Each key holds interchangeable variants; one is picked per week (repeatably, so
# re-running a week gives the same text). {conf} is "the SEC", {Conf} is "The SEC".
PHRASES = {
    "title": ["{label} AP Poll XC", "AP Poll XC, {label}"],
    "title_preseason": ["{year} AP Poll XC, Preseason"],
    "title_final": ["Final {year} AP Poll XC"],
    "head_none": ["no conference has {n_word} teams in the poll yet."],
    "head_preseason": [
        "{conf} opens the season on top.",
        "{conf} starts the year in front.",
    ],
    "head_final": [
        "{conf} finishes the season on top.",
        "{conf} ends the year in first.",
    ],
    "head_tie": [
        "{conf} and {other} are level at {score}; {conf} takes it on the tiebreaker."
    ],
    "head_change": [
        "{conf} takes the lead from {other}{run}.",
        "{conf} moves past {other} into first{run}.",
    ],
    "head_change_run": [", which had led {streak} straight polls"],
    "head_wire": [
        "{conf} has led every poll this season.",
        "{conf} is still wire-to-wire.",
    ],
    "head_streak": [
        "{conf} leads for the {nth} straight poll.",
        "{conf} makes it {streak} polls in a row on top.",
    ],
    "head_again": ["{conf} leads again.", "{conf} stays on top."],
    "scoring_note": ["(low score wins)"],
    "perfect": [
        "A perfect {score}: {conf} holds every one of the top {n_word} spots."
    ],
    "record_low": [
        "{score} is the lowest score by any conference in our data (since {since})."
    ],
    "low_since": ["{score} is the lowest score by any conference since {when}."],
    "high_lead_since": [
        "{score} is the highest first-place score since {when}, a sign of parity."
    ],
    "close_race": [
        "{Conf} leads {other} by just {gap} {points}.",
        "Just {gap} {points} separate {conf} and {other}.",
    ],
    # {Conf_poss}/{other}: "The SEC's" / "the Big Ten", so the lead is always attributed
    "gap_shrinks": [
        "{Conf_poss} lead over {other} shrinks from {prev_gap} to {gap} points."
    ],
    "gap_grows": ["{Conf_poss} lead over {other} grows from {prev_gap} to {gap} points."],
    # "_short" variants are used when the full sentences would not all fit in one post
    "gap_shrinks_short": ["{Conf_poss} lead over {other} shrinks from {prev_gap} to {gap}."],
    "gap_grows_short": ["{Conf_poss} lead over {other} grows from {prev_gap} to {gap}."],
    "gap_widest_short": ["{Conf_poss} {gap}-point lead is the season's largest."],
    "conf_up_short": ["{Conf} improves {delta} {points} to {score}."],
    "conf_down_short": ["{Conf} slips {delta} {points} to {score}."],
    "movers_short": ["{riser} {up}{rise}, {faller} {down}{fall}."],
    "riser_short": ["Biggest climb: {riser} {up}{rise} to {riser_rank}."],
    "faller_short": ["Biggest drop: {faller} {down}{fall}."],
    "last_year_same_short": ["{Point_short}: {name} also led ({score})."],
    "last_year_other_short": ["{Point_short}: {name} led at {score}."],
    "gap_widest": [
        "{Conf_poss} {gap}-point lead over {other} is the largest of the season."
    ],
    "lead_change_first": ["It is the first lead change of the season."],
    "lead_change_nth": ["It is lead change No. {count} of the season."],
    "conf_up": ["{Conf} improves {delta} {points} to {score}, the week's biggest jump."],
    "conf_down": ["{Conf} slips {delta} {points} to {score}, the week's biggest slide."],
    "best_on_record": [
        "{score} is the best score for {conf} in our data (since {since})."
    ],
    "best_since": ["{score} is the best score for {conf} since {when}."],
    "season_best": ["{score} is a season best for {conf}."],
    "season_worst": ["{score} is a season worst for {conf}."],
    # {both}: "" for one conference, "both " for two, "all " for three or more
    "off_board": [
        "Off the board: {conf}, {both}now short of {n_word} teams in the poll."
    ],
    "on_board": [
        "Back on the board: {conf}, {both}with {n_word} teams in the poll again."
    ],
    "movers": [
        "Movers: {riser} {up}{rise} to {riser_rank}, {faller} {down}{fall} {faller_dest}."
    ],
    "riser": ["Biggest climb: {riser}, up {rise} to {riser_rank}."],
    "faller": ["Biggest drop: {faller}, down {fall} {faller_dest}."],
    "fell_out": ["{faller} falls out of the poll entirely from {faller_rank}."],
    "fell_out_top25": ["{faller} falls out of the Top 25 from {faller_rank}."],
    "top_five": ["{count} of the top five teams come from {conf}."],  # count: Three/Four/All five
    "depth": ["{count} of the Top 25 come from {conf}."],
    # {point}: "in this same week last season" / "in last season's final poll"
    "last_year_same": ["{Conf} also led {point} ({score})."],
    "last_year_other": ["{Conf} led {point} ({score})."],
    "preseason_same": ["{Conf} also finished last season on top."],
    "preseason_other": ["Last season ended with {conf} on top."],
    "titles": [
        "{Conf} has now finished first in {count} of {seasons} seasons since {since}{streak}."
    ],
    "titles_streak": [", including the last {streak}"],
    "title_first": [
        "It is the first time {conf} has finished first in our data (since {since})."
    ],
}


@dataclass(frozen=True)
class PostConfig:
    """Every knob for the post text. Pass a modified copy to compose_post() to change behavior."""

    num_scoring_teams: int = 5
    max_length: int = 280  # platform limit (X: 280 weighted characters; Bluesky: 300)
    max_storylines: int = 4  # how many storylines follow the standings line, at most
    max_standings: int = 4  # how many conferences the standings line lists
    hashtags: Tuple[str, ...] = ("#CFB",)  # always included, as the post's last line
    # Turn the first mention of the conferences and teams the post talks about most into
    # hashtags in the sentence itself ("the #SEC's lead over the #B1G ...")
    responsive_hashtags: bool = True
    max_hashtags: int = 4  # total, counting the always-included ones
    explain_scoring: bool = True  # add "(low score wins)" when there is room
    # thresholds for what counts as worth mentioning
    close_race_gap: float = 3  # top two this close -> "close race"
    gap_swing: float = 8  # lead grew/shrank by at least this much
    wide_gap: float = 15  # "largest lead of the season" needs at least this much
    big_conference_move: float = 6  # conference score change, in points
    big_team_move: float = 5  # team rank change, in spots
    depth_threshold: int = 8  # this many Top 25 teams from one conference
    streak_threshold: int = 3  # straight polls on top before the headline mentions it
    min_polls_for_season_marks: int = 4  # earlier polls needed before "season best/worst"
    min_seasons_for_since: int = 2  # "best since ..." must reach back at least this many seasons
    min_seasons_for_records: int = 5  # seasons of data needed before "best in our data"
    # A storyline of the same kind as one in last week's post loses this many priority points
    # (twice that if the sentence is word-for-word the same), so posts don't repeat themselves
    repeat_penalty: float = 15
    # which storyline kinds to leave out entirely, e.g. ("year_over_year",)
    skip_kinds: Tuple[str, ...] = ()


@dataclass(frozen=True)
class Storyline:
    """One candidate sentence. Higher priority wins a place in the post; two storylines sharing a
    topic never both appear (so a conference isn't described twice)."""

    kind: str
    priority: float
    text: str
    topic: str
    short: str = ""  # a tighter wording, used when space is short; empty means use `text`


@dataclass(frozen=True)
class WeekContext:
    """Everything a storyline builder may look at for one week."""

    week: rt.StoredWeek
    previous: Optional[rt.StoredWeek]  # prior poll of the same season, if any
    standings: List[Tuple[str, float]]  # scoring conferences in finishing order
    prev_standings: List[Tuple[str, float]]
    season: pd.DataFrame  # earlier polls of this season: year, order, label, conference, score
    history: pd.DataFrame  # every poll before this one, all seasons, same columns
    leaders: pd.DataFrame  # one row per poll before this one: see _poll_leaders()
    cfg: PostConfig
    data_dir: str = rt.DATA_DIR

    @property
    def label(self) -> str:
        return rt._week_label(self.week.token)

    @property
    def leader(self) -> Optional[str]:
        return self.standings[0][0] if self.standings else None

    @property
    def is_final(self) -> bool:
        return self.week.token == "final"

    @property
    def is_preseason(self) -> bool:
        return self.week.token == rt.PRESEASON_WEEK_TOKEN


@dataclass(frozen=True)
class SocialPost:
    """A finished post, ready for any platform: the text, the images to attach (with alt text),
    and every storyline that was considered (for review/tuning)."""

    year: int
    token: str
    text: str
    images: Tuple[str, ...] = ()
    alt_texts: Tuple[str, ...] = ()
    storylines: Tuple[Storyline, ...] = field(default=(), compare=False)

    @property
    def key(self) -> str:
        return f"{self.year}-{self.token}"


# ----------------------------------------------------------------------------------------------
# Small helpers
# ----------------------------------------------------------------------------------------------


def weighted_length(text: str) -> int:
    """Length as X counts it: most Latin characters weigh 1, everything else (emoji, arrows such as
    the movement triangles, CJK) weighs 2. Close enough for other platforms' plain limits too.

    >>> weighted_length("SEC 42")
    6
    >>> weighted_length("▲8")
    3
    """
    light = ((0, 4351), (8192, 8205), (8208, 8223), (8242, 8247))
    return sum(1 if any(lo <= ord(ch) <= hi for lo, hi in light) else 2 for ch in text)


def _alias(conference: str) -> str:
    return HISTORY_ALIASES.get(conference, conference)


def _conf(conference: str, capital: bool = False) -> str:
    """'the SEC' / 'The SEC'."""
    name = CONFERENCE_NAMES.get(conference, f"the {conference}")
    return name[0].upper() + name[1:] if capital else name


def _join_names(names: List[str]) -> str:
    """'A', 'A and B', 'A, B and C'.

    >>> _join_names(["the SEC", "the Pac-10"])
    'the SEC and the Pac-10'
    >>> _join_names(["a", "b", "c"])
    'a, b and c'
    """
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


def _poss(text: str) -> str:
    """Possessive of a name phrase: 'The SEC' -> "The SEC's"; 'the FBS Independents' -> "...'"."""
    return text + ("'" if text.endswith("s") else "'s")


def _num(value) -> str:
    return rt._fmt_num(value)


def _points(value) -> str:
    return "point" if float(value) == 1 else "points"


def _rank_text(rank) -> str:
    """'No. 14', or 'a tie for No. 24' for an averaged (tied) rank such as 24.5."""
    rank = float(rank)
    return f"No. {int(rank)}" if rank.is_integer() else f"a tie for No. {int(rank)}"


def _when(label: str, year: int) -> str:
    """'Week 5 of 2019' / 'the 2019 Preseason poll' / 'the 2019 Final poll'."""
    if label.startswith("Week"):
        return f"{label} of {int(year)}"
    return f"the {int(year)} {label} poll"


def _label_order(label: str) -> int:
    """Chronological position of a week label within a season (Preseason first, Final last)."""
    if label == "Preseason":
        return 1
    if label == "Final":
        return 99
    return int(label.split()[-1])


def _token_order(token: str) -> int:
    return 99 if token == "final" else int(token)


def _phrase(ctx: WeekContext, key: str, **fields) -> str:
    """One variant of PHRASES[key], chosen repeatably for this week, with fields filled in."""
    variants = PHRASES[key]
    choice = random.Random(f"{ctx.week.year}|{ctx.week.token}|{key}").choice(variants)
    fields.setdefault(
        "n_word", rt._NUMBER_WORDS.get(ctx.cfg.num_scoring_teams, "enough")
    )
    return choice.format(**fields)


# ----------------------------------------------------------------------------------------------
# Loading: stored weeks and the cross-season score history
# ----------------------------------------------------------------------------------------------


@functools.lru_cache(maxsize=4)
def load_score_history(
    num_scoring_teams: int = 5, data_dir: str = rt.DATA_DIR
) -> pd.DataFrame:
    """Every recorded conference score from every season's summary-statistics CSV, one row per
    (season, poll, conference): columns year, order, label, conference, score. Conferences are
    relabeled per HISTORY_ALIASES; weeks with no score for a conference (DNS) have no row."""
    team_dir = rt._team_dir(num_scoring_teams)
    frames = []
    for entry in sorted(os.listdir(data_dir)):
        path = os.path.join(
            data_dir, entry, team_dir, f"{entry}_{team_dir}_summary_statistics.csv"
        )
        if not (entry.isdigit() and os.path.exists(path)):
            continue
        wide = pd.read_csv(path, index_col=0)
        long = (
            wide.rename_axis("label")
            .reset_index()
            .melt(id_vars="label", var_name="conference", value_name="score")
        )
        long["score"] = pd.to_numeric(long["score"], errors="coerce")
        long = long.dropna(subset=["score"])
        long["year"] = int(entry)
        frames.append(long)
    columns = ["year", "order", "label", "conference", "score"]
    if not frames:
        return pd.DataFrame(columns=columns)
    history = pd.concat(frames, ignore_index=True)
    history["order"] = history["label"].map(_label_order)
    history["conference"] = history["conference"].map(_alias)
    return (
        history[columns].sort_values(["year", "order", "score"]).reset_index(drop=True)
    )


def conference_standings(
    week: rt.StoredWeek, num_scoring_teams: int = 5
) -> List[Tuple[str, float]]:
    """The conferences that scored, in finishing order (the pipeline's own order, so ties are
    broken exactly as in the stored graphs and README table): [(conference, score), ...]."""
    if not any(score != epi.did_not_score for score in week.scores.values()):
        return []
    with contextlib.redirect_stdout(io.StringIO()):
        order_df = epi.conference_scoring_order(
            week.scores, week.teams_df, scoring_teams=num_scoring_teams
        )
    return [(conf, float(week.scores[conf])) for conf in order_df["conference"]]


def _load_week(year: int, token: str, n: int, data_dir: str) -> rt.StoredWeek:
    """A stored week with every score as a number (or "DNS"). A few older files hold fractional
    scores as text, e.g. '89.5' in the 2023 Final poll."""
    week = rt.load_stored_week(year, token, n, data_dir)
    scores = {
        conf: score if score == epi.did_not_score else float(score)
        for conf, score in week.scores.items()
    }
    return dataclasses.replace(week, scores=scores)


@functools.lru_cache(maxsize=64)
def build_week_context(
    year: Optional[int] = None,
    week_token: Optional[str] = None,
    cfg: PostConfig = PostConfig(),
    data_dir: str = rt.DATA_DIR,
) -> WeekContext:
    """Load one stored week (default: the newest) with everything needed to judge it."""
    n = cfg.num_scoring_teams
    if year is None or week_token is None:
        year, week_token, _ = rt.latest_recorded_week(n, data_dir)
    year, week_token = int(year), str(week_token)
    week = _load_week(year, week_token, n, data_dir)
    prev_token = rt.previous_comparable_week_token(year, week_token, n, data_dir)
    previous = _load_week(year, prev_token, n, data_dir) if prev_token else None

    history = load_score_history(n, data_dir)
    order = _token_order(week_token)
    before = (history["year"] < year) | (
        (history["year"] == year) & (history["order"] < order)
    )
    history = history[before]
    leaders = load_poll_leaders(n, data_dir)
    leaders = leaders[
        (leaders["year"] < year)
        | ((leaders["year"] == year) & (leaders["order"] < order))
    ]
    return WeekContext(
        week=week,
        previous=previous,
        standings=conference_standings(week, n),
        prev_standings=conference_standings(previous, n) if previous else [],
        season=history[history["year"] == year],
        history=history,
        leaders=leaders,
        cfg=cfg,
        data_dir=data_dir,
    )


def _poll_leaders(scores: pd.DataFrame) -> pd.DataFrame:
    """One row per poll in `scores`, oldest first: year, order, label, leader, score, gap (points
    back to second place; NaN when only one conference scored)."""
    rows = []
    for (year, order), poll in scores.groupby(["year", "order"], sort=True):
        poll = poll.sort_values("score")
        gap = (
            poll["score"].iloc[1] - poll["score"].iloc[0]
            if len(poll) > 1
            else float("nan")
        )
        first = poll.iloc[0]
        rows.append(
            (year, order, first["label"], first["conference"], first["score"], gap)
        )
    return pd.DataFrame(
        rows, columns=["year", "order", "label", "leader", "score", "gap"]
    )


@functools.lru_cache(maxsize=4)
def load_poll_leaders(
    num_scoring_teams: int = 5, data_dir: str = rt.DATA_DIR
) -> pd.DataFrame:
    """_poll_leaders() for the whole stored history (computed once per run)."""
    return _poll_leaders(load_score_history(num_scoring_teams, data_dir))


def _season_leaders(ctx: WeekContext) -> pd.DataFrame:
    """Leaders of this season's earlier polls, oldest first."""
    return ctx.leaders[ctx.leaders["year"] == ctx.week.year]


def _leader_streak(ctx: WeekContext) -> int:
    """Consecutive polls this season, counting this one, that the current leader has led."""
    streak = 1
    for leader in reversed(list(_season_leaders(ctx)["leader"])):
        if leader != _alias(ctx.leader):
            break
        streak += 1
    return streak


# ----------------------------------------------------------------------------------------------
# Headline and standings line
# ----------------------------------------------------------------------------------------------


def build_headline(ctx: WeekContext) -> str:
    """'Week 12 AP Poll XC: the SEC leads for the 12th straight poll.'"""
    title_key = (
        "title_final"
        if ctx.is_final
        else "title_preseason" if ctx.is_preseason else "title"
    )
    title = _phrase(ctx, title_key, label=ctx.label, year=ctx.week.year)
    if not ctx.standings:
        return f"{title}: {_phrase(ctx, 'head_none')}"

    leader, score = ctx.standings[0]
    fields = dict(conf=_conf(leader), score=_num(score))
    prior_leaders = _season_leaders(ctx)
    prev_leader = ctx.prev_standings[0][0] if ctx.prev_standings else None

    if len(ctx.standings) > 1 and ctx.standings[1][1] == score:
        sentence = _phrase(ctx, "head_tie", other=_conf(ctx.standings[1][0]), **fields)
    elif ctx.is_final:
        sentence = _phrase(ctx, "head_final", **fields)
    elif ctx.is_preseason:
        sentence = _phrase(ctx, "head_preseason", **fields)
    elif prev_leader is None:
        sentence = _phrase(ctx, "head_again", **fields)
    elif _alias(prev_leader) != _alias(leader):
        # how long the outgoing leader had been on top
        ended = 0
        for past in reversed(list(prior_leaders["leader"])):
            if past != _alias(prev_leader):
                break
            ended += 1
        run = (
            _phrase(ctx, "head_change_run", streak=ended)
            if ended >= ctx.cfg.streak_threshold
            else ""
        )
        sentence = _phrase(
            ctx, "head_change", other=_conf(prev_leader), run=run, **fields
        )
    else:
        streak = _leader_streak(ctx)
        wire_to_wire = streak == len(prior_leaders) + 1
        if wire_to_wire and streak >= max(ctx.cfg.streak_threshold, 4):
            sentence = _phrase(ctx, "head_wire", **fields)
        elif streak >= ctx.cfg.streak_threshold:
            sentence = _phrase(
                ctx, "head_streak", streak=streak, nth=rt._ordinal(streak), **fields
            )
        else:
            sentence = _phrase(ctx, "head_again", **fields)
    # a sentence opens with the conference name, which follows the title's colon in lower case
    return f"{title}: {sentence}"


def build_standings_line(ctx: WeekContext) -> str:
    """'SEC 42 · Big Ten 53 · Big 12 64 · ACC 99.5'"""
    top = ctx.standings[: ctx.cfg.max_standings]
    return " · ".join(f"{conf} {_num(score)}" for conf, score in top)


# ----------------------------------------------------------------------------------------------
# Storyline builders: each takes a WeekContext and returns zero or more Storylines
# ----------------------------------------------------------------------------------------------


def _last_from_earlier_season(
    ctx: WeekContext, rows: pd.DataFrame
) -> Optional[pd.Series]:
    """The most recent of `rows` (polls that already match some mark), provided it is from far
    enough back (cfg.min_seasons_for_since) to be worth a 'since ...'. None otherwise."""
    if rows.empty:
        return None
    last = rows.sort_values(["year", "order"]).iloc[-1]
    if ctx.week.year - last["year"] < ctx.cfg.min_seasons_for_since:
        return None
    return last


def storyline_leader_marks(ctx: WeekContext) -> List[Storyline]:
    """The leading score against history: a perfect score, the lowest by anyone in years, or (the
    opposite) the highest score to lead a poll in years."""
    if not ctx.standings or ctx.history.empty:
        return []
    leader, score = ctx.standings[0]
    n = ctx.cfg.num_scoring_teams
    topic = f"conf:{_alias(leader)}"
    since = int(ctx.history["year"].min())
    if score == n * (n + 1) / 2:
        text = _phrase(ctx, "perfect", score=_num(score), conf=_conf(leader))
        return [Storyline("perfect", 100, text, topic)]

    as_low = ctx.history[ctx.history["score"] <= score]
    enough_data = ctx.week.year - since >= ctx.cfg.min_seasons_for_records
    if as_low.empty and enough_data:
        text = _phrase(ctx, "record_low", score=_num(score), since=since)
        return [Storyline("record_low", 95, text, topic)]
    last = _last_from_earlier_season(ctx, as_low)
    if last is not None:
        years = ctx.week.year - last["year"]
        when = _when(last["label"], last["year"])
        text = _phrase(ctx, "low_since", score=_num(score), when=when)
        return [Storyline("low_since", 72 + min(3 * years, 24), text, topic)]

    leaders = ctx.leaders
    last = _last_from_earlier_season(ctx, leaders[leaders["score"] >= score])
    if last is not None:
        years = ctx.week.year - last["year"]
        when = _when(last["label"], last["year"])
        text = _phrase(ctx, "high_lead_since", score=_num(score), when=when)
        return [Storyline("high_lead_since", 62 + min(3 * years, 24), text, "lead")]
    return []


def storyline_margin(ctx: WeekContext) -> List[Storyline]:
    """The gap between first and second: a close race, a lead that grew or shrank, or the widest
    lead of the season."""
    if len(ctx.standings) < 2:
        return []
    cfg = ctx.cfg
    gap = ctx.standings[1][1] - ctx.standings[0][1]
    if gap == 0:
        return []  # the headline already covers a tie
    first, second = ctx.standings[0][0], ctx.standings[1][0]
    names = dict(
        conf=_conf(first),
        Conf=_conf(first, capital=True),
        Conf_poss=_poss(_conf(first, capital=True)),
        other=_conf(second),
    )
    if gap <= cfg.close_race_gap:
        text = _phrase(ctx, "close_race", gap=_num(gap), points=_points(gap), **names)
        return [Storyline("close_race", 72, text, "lead")]

    out = []
    same_leader = bool(ctx.prev_standings) and _alias(
        ctx.prev_standings[0][0]
    ) == _alias(ctx.leader)
    if same_leader and len(ctx.prev_standings) > 1:
        prev_gap = ctx.prev_standings[1][1] - ctx.prev_standings[0][1]
        swing = gap - prev_gap
        if abs(swing) >= cfg.gap_swing and prev_gap > 0:
            key = "gap_grows" if swing > 0 else "gap_shrinks"
            base = 44 if swing > 0 else 48
            fields = dict(prev_gap=_num(prev_gap), gap=_num(gap), **names)
            text = _phrase(ctx, key, **fields)
            short = _phrase(ctx, f"{key}_short", **fields)
            out.append(
                Storyline(key, base + min(abs(swing), 20), text, "lead", short)
            )
    season_gaps = _season_leaders(ctx)["gap"].dropna()
    if (
        gap >= cfg.wide_gap
        and len(season_gaps) >= cfg.min_polls_for_season_marks
        and gap > season_gaps.max()
    ):
        fields = dict(gap=_num(gap), **names)
        text = _phrase(ctx, "gap_widest", **fields)
        short = _phrase(ctx, "gap_widest_short", **fields)
        out.append(Storyline("gap_widest", 58, text, "lead", short))
    return out


def storyline_lead_changes(ctx: WeekContext) -> List[Storyline]:
    """On a week the lead changes hands: how many times that has happened this season."""
    if not ctx.standings or not ctx.prev_standings:
        return []
    if _alias(ctx.prev_standings[0][0]) == _alias(ctx.leader):
        return []
    leaders = list(_season_leaders(ctx)["leader"]) + [_alias(ctx.leader)]
    count = sum(1 for a, b in zip(leaders, leaders[1:]) if a != b)
    if count == 1 and len(leaders) > ctx.cfg.min_polls_for_season_marks:
        text = _phrase(ctx, "lead_change_first")
        return [Storyline("lead_change", 60, text, "changes")]
    if count >= 2:
        text = _phrase(ctx, "lead_change_nth", count=count)
        return [Storyline("lead_change", 50 + min(count, 10), text, "changes")]
    return []


def storyline_conference_mover(ctx: WeekContext) -> List[Storyline]:
    """The conference whose score changed the most since the prior poll."""
    prev = dict(ctx.prev_standings)
    moves = [
        (prev[conf] - score, conf, score)
        for conf, score in ctx.standings
        if conf in prev
    ]
    if not moves:
        return []
    delta, conf, score = max(moves, key=lambda m: abs(m[0]))
    if abs(delta) < ctx.cfg.big_conference_move:
        return []
    key = "conf_up" if delta > 0 else "conf_down"
    fields = dict(
        name=conf,
        conf=_conf(conf),
        Conf=_conf(conf, capital=True),
        delta=_num(abs(delta)),
        points=_points(abs(delta)),
        score=_num(score),
    )
    text = _phrase(ctx, key, **fields)
    short = _phrase(ctx, f"{key}_short", **fields)
    priority = 45 + min(abs(delta), 25)
    return [Storyline(key, priority, text, f"conf:{_alias(conf)}", short)]


def storyline_conference_marks(ctx: WeekContext) -> List[Storyline]:
    """A conference's own score against its past: best in years, or best/worst of the season."""
    out = []
    for conf, score in ctx.standings:
        own = ctx.history[ctx.history["conference"] == _alias(conf)]
        this_season = own[own["year"] == ctx.week.year]["score"]
        if len(this_season) < ctx.cfg.min_polls_for_season_marks:
            continue
        fields = dict(score=_num(score), conf=_conf(conf))
        topic = f"conf:{_alias(conf)}"
        if score < this_season.min():
            earlier = own[own["year"] < ctx.week.year]
            as_good = earlier[earlier["score"] <= score]
            last = _last_from_earlier_season(ctx, as_good)
            since = int(own["year"].min())
            enough_data = ctx.week.year - since >= ctx.cfg.min_seasons_for_records
            if as_good.empty and enough_data:
                text = _phrase(ctx, "best_on_record", since=since, **fields)
                out.append(Storyline("best_on_record", 90, text, topic))
            elif last is not None:
                years = ctx.week.year - last["year"]
                when = _when(last["label"], last["year"])
                text = _phrase(ctx, "best_since", when=when, **fields)
                out.append(
                    Storyline("best_since", 60 + min(3 * years, 24), text, topic)
                )
            else:
                text = _phrase(ctx, "season_best", **fields)
                out.append(Storyline("season_best", 52, text, topic))
        elif score > this_season.max():
            text = _phrase(ctx, "season_worst", **fields)
            out.append(Storyline("season_worst", 46, text, topic))
    return out


def storyline_board_changes(ctx: WeekContext) -> List[Storyline]:
    """A conference that stopped scoring (too few teams in the poll) or started again."""
    if ctx.previous is None:
        return []
    now = {_alias(c): c for c, _ in ctx.standings}
    before = {_alias(c): c for c, _ in ctx.prev_standings}
    out = []
    # Conferences that move together share one sentence ("the SEC and the Pac-10, both now ...")
    for key, priority, moved in (
        ("off_board", 56, [c for a, c in before.items() if a not in now]),
        ("on_board", 53, [c for a, c in now.items() if a not in before]),
    ):
        if not moved:
            continue
        both = {1: "", 2: "both "}.get(len(moved), "all ")
        text = _phrase(ctx, key, conf=_join_names([_conf(c) for c in moved]), both=both)
        topic = "conf:" + "+".join(sorted(_alias(c) for c in moved))
        out.append(Storyline(key, priority, text, topic))
    return out


def storyline_team_movers(ctx: WeekContext) -> List[Storyline]:
    """The biggest riser into/within the Top 25 and the biggest faller from it."""
    if ctx.previous is None:
        return []
    now, before = ctx.week.team_ranks(), ctx.previous.team_ranks()
    rises = [(before[t] - r, t, r) for t, r in now.items() if r <= 25 and t in before]
    falls = [(now[t] - r, t, now[t]) for t, r in before.items() if r <= 25 and t in now]
    gone = sorted((r, t) for t, r in before.items() if r <= 25 and t not in now)
    out = []
    rise = max(rises, default=None)
    fall = max(falls, default=None)
    rise = rise if rise and rise[0] >= ctx.cfg.big_team_move else None
    fall = fall if fall and fall[0] >= ctx.cfg.big_team_move else None

    if gone:  # the highest-ranked team to leave the poll data completely
        rank, team = gone[0]
        has_vote_getters = max(now.values(), default=0) > 25
        key = "fell_out" if has_vote_getters else "fell_out_top25"
        text = _phrase(ctx, key, faller=team, faller_rank=_rank_text(rank))
        out.append(Storyline("fell_out", 38 + (26 - rank), text, "teams"))
    fields = {}
    if rise:
        fields.update(
            riser=rise[1], rise=_num(rise[0]), riser_rank=_rank_text(rise[2])
        )
    if fall:
        # a rank past 25 is only a vote count, so say where the team fell from the reader's view
        dest = f"to {_rank_text(fall[2])}" if fall[2] <= 25 else "and out of the Top 25"
        fields.update(faller=fall[1], fall=_num(fall[0]), faller_dest=dest)
    fields.update(up=rt.UP, down=rt.DOWN)
    if rise and fall:
        key, size = "movers", max(rise[0], fall[0])
    elif rise:
        key, size = "riser", rise[0]
    elif fall:
        key, size = "faller", fall[0]
    else:
        return out
    text = _phrase(ctx, key, **fields)
    short = _phrase(ctx, f"{key}_short", **fields)
    return out + [Storyline("team_movers", 40 + min(size, 20), text, "teams", short)]


def storyline_depth(ctx: WeekContext) -> List[Storyline]:
    """One conference holding most of the top five, or an unusual share of the Top 25."""
    teams = ctx.week.teams_by_conference()
    top_five = {c: sum(1 for _, r in ts if r <= 5) for c, ts in teams.items()}
    top_25 = {c: sum(1 for _, r in ts if r <= 25) for c, ts in teams.items()}
    if not top_25:
        return []
    conf5 = max(top_five, key=top_five.get)
    if top_five[conf5] >= 3:
        count = {3: "Three", 4: "Four", 5: "All five"}[top_five[conf5]]
        text = _phrase(ctx, "top_five", count=count, conf=_conf(conf5))
        return [Storyline("top_five", 40 + 4 * top_five[conf5], text, "depth")]
    conf25 = max(top_25, key=top_25.get)
    if top_25[conf25] >= ctx.cfg.depth_threshold:
        extra = top_25[conf25] - ctx.cfg.depth_threshold
        text = _phrase(ctx, "depth", count=top_25[conf25], conf=_conf(conf25))
        return [Storyline("depth", 36 + 4 * extra, text, "depth")]
    return []


def storyline_year_over_year(ctx: WeekContext) -> List[Storyline]:
    """Who led the same poll a year ago (or, in the Preseason, who finished last season on top)."""
    if not ctx.standings:
        return []
    label = "Final" if ctx.is_preseason else ctx.label
    leaders = ctx.leaders[
        (ctx.leaders["year"] == ctx.week.year - 1) & (ctx.leaders["label"] == label)
    ]
    if leaders.empty:
        return []
    then = leaders.iloc[0]
    same = then["leader"] == _alias(ctx.leader)
    fields = dict(
        name=then["leader"],
        conf=_conf(then["leader"]),
        Conf=_conf(then["leader"], capital=True),
        score=_num(then["score"]),
        point=(
            "in last season's final poll"
            if ctx.is_final
            else "in this same week last season"
        ),
        Point_short="Last year's final" if ctx.is_final else "Same week last year",
    )
    if ctx.is_preseason:
        key = "preseason_same" if same else "preseason_other"
        text = _phrase(ctx, key, **fields)
        return [Storyline("year_over_year", 60, text, "last_year")]
    key = "last_year_same" if same else "last_year_other"
    priority = 34 if same else 38
    text = _phrase(ctx, key, **fields)
    short = _phrase(ctx, f"{key}_short", **fields)
    return [Storyline("year_over_year", priority, text, "last_year", short)]


def storyline_final_titles(ctx: WeekContext) -> List[Storyline]:
    """After the Final poll: how many seasons the winner has finished first, and its current run."""
    if not ctx.is_final or not ctx.standings:
        return []
    finals = ctx.leaders[ctx.leaders["label"] == "Final"]
    winners = list(finals["leader"]) + [_alias(ctx.leader)]
    if len(winners) == 1:
        return []
    count = winners.count(_alias(ctx.leader))
    fields = dict(
        conf=_conf(ctx.leader),
        Conf=_conf(ctx.leader, capital=True),
        since=int(finals["year"].min()),
    )
    if count == 1:
        text = _phrase(ctx, "title_first", **fields)
        return [Storyline("titles", 88, text, "titles")]
    run = 0
    for winner in reversed(winners):
        if winner != _alias(ctx.leader):
            break
        run += 1
    streak = _phrase(ctx, "titles_streak", streak=run) if 2 <= run < count else ""
    text = _phrase(
        ctx, "titles", count=count, seasons=len(winners), streak=streak, **fields
    )
    return [Storyline("titles", 88, text, "titles")]


# The storylines considered for every post. Order doesn't matter (priority decides); edit this
# list to add or drop a kind of observation.
STORYLINE_BUILDERS: List[Callable[[WeekContext], List[Storyline]]] = [
    storyline_leader_marks,
    storyline_margin,
    storyline_lead_changes,
    storyline_conference_mover,
    storyline_conference_marks,
    storyline_board_changes,
    storyline_team_movers,
    storyline_depth,
    storyline_year_over_year,
    storyline_final_titles,
]


def find_storylines(ctx: WeekContext) -> List[Storyline]:
    """Every storyline that applies to this week, most interesting first."""
    found = [s for build in STORYLINE_BUILDERS for s in build(ctx)]
    found = [s for s in found if s.kind not in ctx.cfg.skip_kinds]
    return sorted(found, key=lambda s: -s.priority)


# ----------------------------------------------------------------------------------------------
# Composing the post
# ----------------------------------------------------------------------------------------------


def _team_hashtag(team: str) -> str:
    """'#SouthCarolina' from 'South Carolina'; 'St' is spelled out ('Boise St' -> '#BoiseState')."""
    if team in TEAM_HASHTAGS:
        return TEAM_HASHTAGS[team]
    words = ["State" if word == "St" else word for word in team.split()]
    return "#" + "".join(ch for ch in "".join(words) if ch.isalnum())


def _name_pattern(name: str) -> "re.Pattern":
    """Matches `name` as a whole word (never inside a longer name, a hashtag, or 'Texas A&M')."""
    return re.compile(rf"(?<![\w&#]){re.escape(name)}(?![\w&])")


def rank_hashtags(ctx: WeekContext, body: str) -> List[Tuple[str, str]]:
    """The conferences and teams that `body` (the headline and storylines, not the standings line)
    mentions, as (name, hashtag) pairs: most-mentioned first, earliest first among equals. So a
    post that is mostly about the SEC leads with #SEC, one about the Big Ten with #B1G, and a big
    mover brings its own team tag."""
    teams = set(ctx.week.team_ranks())
    if ctx.previous is not None:
        teams |= set(ctx.previous.team_ranks())
    named = [(team, _team_hashtag(team)) for team in teams]
    named += list(CONFERENCE_HASHTAGS.items())
    # Longest names first, blanking each match, so "Texas" isn't counted inside "Texas Tech"
    found = []
    for name, tag in sorted(named, key=lambda pair: -len(pair[0])):
        pattern = _name_pattern(name)
        matches = list(pattern.finditer(body))
        if matches:
            found.append((-len(matches), matches[0].start(), name, tag))
            body = pattern.sub(lambda m: " " * len(m.group()), body)
    return [(name, tag) for _, _, name, tag in sorted(found)]


def apply_inline_hashtags(parts: List[str], picks: List[Tuple[str, str]]) -> List[str]:
    """Turn the first mention of each picked name into its hashtag, working through `parts` in
    order: 'the Big Ten' -> 'the #B1G', "Louisville" -> "#Louisville". Saves the room a separate
    hashtag line would take, and puts the tag where the reader meets the name."""
    parts = list(parts)
    for name, tag in sorted(picks, key=lambda pair: -len(pair[0])):
        pattern = _name_pattern(name)
        for i, part in enumerate(parts):
            if pattern.search(part):
                parts[i] = pattern.sub(lambda m: tag, part, count=1)
                break
    return parts


def abbreviate_names(parts: List[str], standings: str) -> List[str]:
    """Once a name has been spelled out in the standings line, the rest of the post can use its
    short form (per ABBREVIATIONS): 'the Big Ten improves ...' -> 'the B1G improves ...'. A name
    that isn't in the standings line is left as is. Only the sentences are changed, not the
    standings line itself."""
    for full, short in ABBREVIATIONS.items():
        if _name_pattern(full).search(standings):
            pattern = _name_pattern(full)
            parts = [pattern.sub(short, part) for part in parts]
    return parts


def _assemble(
    headline: str, standings: str, lines: List[str], hashtags: Tuple[str, ...]
) -> str:
    parts = [headline]
    if standings:
        parts.append(standings)
    if lines:
        parts.append("\n".join(lines))
    if hashtags:
        parts.append(" ".join(hashtags))
    return "\n\n".join(parts)


def choose_storylines(
    ctx: WeekContext,
    length_fn: Callable[[str], int] = weighted_length,
    avoid_repeats: bool = True,
) -> List[Storyline]:
    """The storylines that make the post: highest priority first, at most cfg.max_storylines,
    never two on one topic, and only while the text still fits (tighter `short` wordings are used
    where the full sentences would not all fit). With `avoid_repeats`, kinds used in the previous
    poll's post are marked down by cfg.repeat_penalty first."""
    cfg = ctx.cfg
    stories = find_storylines(ctx)
    if avoid_repeats and ctx.previous is not None and cfg.repeat_penalty:
        last_week = build_week_context(
            ctx.previous.year, ctx.previous.token, cfg, ctx.data_dir
        )
        used = choose_storylines(last_week, length_fn, avoid_repeats=False)
        used_kinds = {story.kind for story in used}
        used_texts = {story.text for story in used}

        def adjusted(story: Storyline) -> float:
            if story.text in used_texts or story.short in used_texts:
                return story.priority - 2 * cfg.repeat_penalty
            if story.kind in used_kinds:
                return story.priority - cfg.repeat_penalty
            return story.priority

        stories = sorted(stories, key=lambda story: -adjusted(story))

    # 1. take as many storylines as allowed, counting each at its shortest wording
    chosen: List[Storyline] = []
    for story in stories:
        if len(chosen) >= cfg.max_storylines:
            break
        if any(story.topic == c.topic for c in chosen):
            continue
        trial = [c.short or c.text for c in chosen + [story]]
        if _render_post(ctx, trial, length_fn, keep_all_tags=True) is not None:
            chosen.append(story)
    # 2. give the full sentence back to each, best first, while the whole post still fits
    texts = [c.short or c.text for c in chosen]
    for i, story in enumerate(chosen):
        trial = texts[:i] + [story.text] + texts[i + 1 :]
        if _render_post(ctx, trial, length_fn, keep_all_tags=True) is not None:
            texts = trial
    return [dataclasses.replace(c, text=t) for c, t in zip(chosen, texts)]


def _render_post(
    ctx: WeekContext,
    lines: List[str],
    length_fn: Callable[[str], int] = weighted_length,
    keep_all_tags: bool = False,
) -> Optional[str]:
    """The finished text for these storyline sentences, or None if it can't be made to fit in
    cfg.max_length. Best version first; each step down gives up something optional: the scoring
    note, then inline hashtags from the least relevant, and last the closing hashtags. With
    `keep_all_tags` (used while choosing storylines) only the scoring note may be given up: the
    sentences are chosen to leave room for every hashtag, since hashtags are worth more than a
    fuller sentence."""
    cfg = ctx.cfg
    headline = build_headline(ctx)
    standings = build_standings_line(ctx)
    noted = f"{standings} {_phrase(ctx, 'scoring_note')}" if standings else standings

    picks: List[Tuple[str, str]] = []
    if cfg.responsive_hashtags:
        picks = rank_hashtags(ctx, "\n".join([headline] + lines))
        picks = picks[: max(cfg.max_hashtags - len(cfg.hashtags), 0)]

    def render(std: str, n_inline: int, closing: Tuple[str, ...]) -> str:
        parts = apply_inline_hashtags([headline] + lines, picks[:n_inline])
        head, *rest = abbreviate_names(parts, standings)
        return _assemble(head, std, rest, closing)

    options = [(noted, len(picks), cfg.hashtags)] if cfg.explain_scoring else []
    lowest = len(picks) if keep_all_tags else 0
    options += [(standings, n, cfg.hashtags) for n in range(len(picks), lowest - 1, -1)]
    if not keep_all_tags:
        options.append((standings, 0, ()))
    for std, n_inline, closing in options:
        text = render(std, n_inline, closing)
        if length_fn(text) <= cfg.max_length:
            return text
    return None


def compose_text(
    ctx: WeekContext, length_fn: Callable[[str], int] = weighted_length
) -> str:
    """The post text for one week: headline, standings line, then as many of the top storylines as
    fit in cfg.max_length (never two on the same topic), then the always-on hashtags. The
    conferences and teams the post talks about most get their hashtag inline, where they are
    named (see rank_hashtags()). If space runs short, extras go before any storyline does."""
    lines = [story.text for story in choose_storylines(ctx, length_fn)]
    while True:
        text = _render_post(ctx, lines, length_fn)
        if text is not None or not lines:
            break
        lines = lines[:-1]  # should not happen: choose_storylines only picks what fits
    return text or build_headline(ctx)


def _alt_text_graph(ctx: WeekContext) -> str:
    listing = ", ".join(f"{conf} {_num(score)}" for conf, score in ctx.standings)
    return (
        "Line graph of each conference's AP Poll cross-country score by week of the "
        f"{ctx.week.year} season; lower is better. {ctx.label}: "
        f"{listing or 'no conference scored'}."
    )


def _alt_text_table(ctx: WeekContext) -> str:
    n = ctx.cfg.num_scoring_teams
    teams = ctx.week.teams_by_conference()
    rows = [
        f"{conf} {_num(score)}: "
        + ", ".join(f"{team} ({_num(rank)})" for team, rank in teams[conf][:n])
        for conf, score in ctx.standings
    ]
    return (
        f"{ctx.label} {ctx.week.year} standings table, scoring teams with AP rank. "
        + "; ".join(rows)
    )


def compose_post(
    year: Optional[int] = None,
    week_token: Optional[str] = None,
    cfg: PostConfig = PostConfig(),
    data_dir: str = rt.DATA_DIR,
    length_fn: Callable[[str], int] = weighted_length,
) -> SocialPost:
    """Build the post for a stored week (default: the newest one). Platform-independent: returns
    the text plus the images to attach. Images are only attached when the post is for the newest
    stored week, since `images/current_week_*` always shows that week. The standings-table image is
    attached if a file exists at images/current_week_<N>team_table.png."""
    ctx = build_week_context(year, week_token, cfg, data_dir)
    n = cfg.num_scoring_teams
    images, alts = [], []
    newest_year, newest_token, _ = rt.latest_recorded_week(n, data_dir)
    if (ctx.week.year, ctx.week.token) == (newest_year, newest_token):
        candidates = (
            (os.path.join(IMAGES_DIR, f"current_week_{n}team.png"), _alt_text_graph(ctx)),
            (
                os.path.join(IMAGES_DIR, f"current_week_{n}team_table.png"),
                _alt_text_table(ctx),
            ),
        )
        for path, alt in candidates:
            if os.path.exists(path):
                images.append(path)
                alts.append(alt[:1000])
    return SocialPost(
        year=ctx.week.year,
        token=ctx.week.token,
        text=compose_text(ctx, length_fn),
        images=tuple(images),
        alt_texts=tuple(alts),
        storylines=tuple(find_storylines(ctx)),
    )


def preview_post(post: SocialPost, show_candidates: bool = True) -> None:
    """Print a post the way it would go out, with its length, images, and the storylines that were
    considered (so thresholds and priorities can be tuned)."""
    print("-" * 60)
    print(post.text)
    print("-" * 60)
    print(
        f"[{post.key}] {weighted_length(post.text)} weighted characters; images: "
        f"{[os.path.basename(p) for p in post.images] or 'none'}"
    )
    if show_candidates:
        for story in post.storylines:
            in_post = story.text in post.text or (story.short and story.short in post.text)
            used = "*" if in_post else " "
            print(f"  {used} {story.priority:5.1f}  {story.kind:<16} {story.text}")


# ==============================================================================================
# Posting to X
# ==============================================================================================


def _read_post_log() -> dict:
    if not os.path.exists(POST_LOG_PATH):
        return {}
    with open(POST_LOG_PATH, "r", encoding="utf-8") as file:
        return json.load(file)


def already_posted(post: SocialPost, platform: str = "x") -> bool:
    return post.key in _read_post_log().get(platform, {})


def _record_post(post: SocialPost, platform: str, post_id: str) -> None:
    log = _read_post_log()
    log.setdefault(platform, {})[post.key] = {
        "id": post_id,
        "posted_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "text": post.text,
    }
    with open(POST_LOG_PATH, "w", encoding="utf-8") as file:
        json.dump(log, file, indent=2, ensure_ascii=False)


X_MEDIA_UPLOAD_URL = "https://api.x.com/2/media/upload"
X_MEDIA_METADATA_URL = "https://api.x.com/2/media/metadata"


def _upload_image_to_x(creds: Dict[str, str], path: str, alt_text: str) -> str:
    """Upload one image and return its media id. Tries X's current (v2) upload endpoint first and
    falls back to the older v1.1 one through tweepy. Alt text is best-effort: a failure to set it
    is reported but does not stop the post. Raises if neither upload route works."""
    auth = OAuth1(
        creds["consumer_key"],
        creds["secret_key"],
        creds["access_token"],
        creds["access_token_secret"],
    )
    with open(path, "rb") as image:
        resp = requests.post(
            X_MEDIA_UPLOAD_URL,
            auth=auth,
            files={"media": image},
            data={"media_category": "tweet_image"},
            timeout=60,
        )
    if resp.ok:
        body = resp.json()
        data = body.get("data", body)
        media_id = str(data.get("id") or data.get("media_id_string"))
    else:
        print(
            f"Image upload (v2) returned HTTP {resp.status_code}: {resp.text[:300]}\n"
            "Trying the older upload endpoint."
        )
        handler = tweepy.OAuth1UserHandler(
            creds["consumer_key"],
            creds["secret_key"],
            creds["access_token"],
            creds["access_token_secret"],
        )
        media_id = str(tweepy.API(handler).media_upload(filename=path).media_id)
    try:
        meta = requests.post(
            X_MEDIA_METADATA_URL,
            auth=auth,
            json={"id": media_id, "metadata": {"alt_text": {"text": alt_text}}},
            timeout=30,
        )
        if not meta.ok:
            print(f"Alt text not set for {os.path.basename(path)} (HTTP {meta.status_code}).")
    except requests.RequestException as err:
        print(f"Alt text not set for {os.path.basename(path)}: {err}")
    return media_id


def post_to_x(
    post: SocialPost,
    dry_run: bool = True,
    force: bool = False,
    attach_images: bool = True,
) -> Optional[str]:
    """Publish `post` to X as the account on file, with its images attached. Returns the new post's
    id, or None if nothing was published.

    Safe by default: with dry_run=True (the default) it only prints what would be sent. A week that
    was already posted (per social_post_log.json) is refused unless force=True. If an image cannot
    be uploaded nothing is posted (pass attach_images=False for a text-only post). Every failure
    is reported and swallowed, so a posting problem can never break the weekly data/graph run."""
    preview_post(post, show_candidates=False)
    if not attach_images:
        print("Text only: images will not be attached.")
    if weighted_length(post.text) > 280:
        print("Not posted: the text is over X's 280-character limit.")
        return None
    if already_posted(post, "x") and not force:
        print(f"Not posted: {post.key} is already in {os.path.basename(POST_LOG_PATH)}.")
        return None
    if dry_run:
        print("Dry run: nothing was sent to X.")
        return None
    try:
        creds = load_twitter_credentials()
        for key in ("access_token", "access_token_secret"):
            if key not in creds:
                raise MissingCredentialsError(
                    f"[{TWITTER_SECTION}] {key} is needed to post."
                )
        media_ids = []
        if attach_images:
            for path, alt in zip(post.images, post.alt_texts):
                media_ids.append(_upload_image_to_x(creds, path, alt))
        response = get_twitter_client(creds).create_tweet(
            text=post.text, media_ids=media_ids or None, user_auth=True
        )
    except MissingCredentialsError as err:
        print(f"Credentials problem: {err}")
        return None
    except tweepy.errors.HTTPException as err:
        _explain_http_error(err)
        return None
    except (tweepy.errors.TweepyException, requests.RequestException, OSError) as err:
        print(f"Could not post to X: {err}")
        return None
    post_id = str(response.data["id"])
    _record_post(post, "x", post_id)
    print(f"Posted: https://x.com/{EXPECTED_USERNAME}/status/{post_id}")
    return post_id


def delete_from_x(post_id: str) -> bool:
    """Delete one of the account's posts by id (e.g. a test post) and drop it from the post log."""
    try:
        get_twitter_client().delete_tweet(post_id, user_auth=True)
    except MissingCredentialsError as err:
        print(f"Credentials problem: {err}")
        return False
    except tweepy.errors.HTTPException as err:
        _explain_http_error(err)
        return False
    except (tweepy.errors.TweepyException, requests.RequestException) as err:
        print(f"Could not delete the post: {err}")
        return False
    log = _read_post_log()
    for key, entry in list(log.get("x", {}).items()):
        if entry.get("id") == str(post_id):
            del log["x"][key]
    if os.path.exists(POST_LOG_PATH):
        with open(POST_LOG_PATH, "w", encoding="utf-8") as file:
            json.dump(log, file, indent=2, ensure_ascii=False)
    print(f"Deleted post {post_id}.")
    return True


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Draft, check, or publish the weekly AP XC post."
    )
    commands = parser.add_subparsers(dest="command")
    preview = commands.add_parser(
        "preview", help="print the drafted post (default; sends nothing)"
    )
    preview.add_argument("--year", type=int)
    preview.add_argument("--week", help="week number, or 'final' (1 is the Preseason)")
    preview.add_argument(
        "--season", type=int, help="print the post for every week of a season"
    )
    commands.add_parser("check", help="test the X credentials with read-only requests")
    publish = commands.add_parser("post", help="publish the newest week's post to X")
    publish.add_argument(
        "--yes", action="store_true", help="actually send it (else a dry run)"
    )
    publish.add_argument(
        "--force", action="store_true", help="post even if already logged"
    )
    publish.add_argument(
        "--text-only", action="store_true", help="do not attach the images"
    )
    remove = commands.add_parser("delete", help="delete one of the account's posts by id")
    remove.add_argument("post_id")
    args = parser.parse_args(argv)
    # the movement triangles and the "·" separator need UTF-8 on a Windows console
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    if args.command == "check":
        return 0 if check_twitter_connection() else 1
    if args.command == "post":
        sent = post_to_x(
            compose_post(),
            dry_run=not args.yes,
            force=args.force,
            attach_images=not args.text_only,
        )
        return 0 if sent or not args.yes else 1
    if args.command == "delete":
        return 0 if delete_from_x(args.post_id) else 1
    if getattr(args, "season", None):
        tokens = rt.stored_week_tokens(args.season)
        for token in sorted(tokens, key=_token_order):
            preview_post(compose_post(args.season, token), show_candidates=False)
        return 0
    preview_post(compose_post(getattr(args, "year", None), getattr(args, "week", None)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

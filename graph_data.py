import itertools
import os
import re

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator

import store_data as sd

"""
Note: This is incomplete. Issue #19 needs to be implemented here.
https://github.com/cooperjaXC/ap-cfb-xc/issues/19
"""

# Conference shortName -> line color, matching the "halogen glow on charcoal"
# look used in past @SECGeographer / @ap_cfb_xc posts. Conferences not listed
# here (CUSA, Sun Belt, MAC, Patriot, FBS Indep., etc.) fall back to
# FALLBACK_COLORS below — they rarely field enough ranked teams to score, so
# no fixed color was ever established for them.
CONFERENCE_COLORS = {
    "SEC": "#1E90FF",  # blue
    "Big Ten": "#FFD500",  # yellow
    "ACC": "#FF3B3B",  # red
    "Big 12": "#3DDC84",  # green - swapped with Big East/American's old purple; Big 12 shows up
    # far more often than Big East/American, and green reads better than purple against SEC's blue
    "American": "#B266FF",  # purple (AAC) - swapped from Big 12, see above; reserved, rarely scores
    "Pac-12": "#87CEFA",  # light blue - defunct as of 2024, but present in historical seasons
    "Mountain West": "#D9D9D9",  # light silver, brightened for dark-theme contrast - free to
    # claim now that Pac-10 (which used to land here via fallback) is merged into Pac-12 for
    # cross-season graphs, see _merge_pac10_into_pac12() below
    "Big East": "#B266FF",  # purple - swapped from Big 12, see above
    "Big East/American": "#B266FF",  # same purple - the merged cross-season identity used by
    # _merge_realigned_conferences() below (Big East football became the American in 2013)
}
FALLBACK_COLORS = ["#FF6EC7", "#00E5FF", "#C0FF00"]

# Used to color a champion's x-axis tick label when its conference didn't score that period (see
# the "off-chart champion" handling in generate_graph()) and, as a last resort, isn't in
# CONFERENCE_COLORS either - practically shouldn't happen since every conference that has ever
# produced an AP #1 team already has a fixed color above.
OFF_CHART_CHAMPION_FALLBACK_COLOR = "#FFC72C"

BACKGROUND_COLOR = "#2B2B2B"
GRID_COLOR = "#555555"
TEXT_COLOR = "#E8E8E8"


def _glow_plot(ax, x, y, color, label):
    """Draw a line with a soft halogen-style glow by layering translucent strokes."""
    for linewidth, alpha in ((8, 0.05), (5, 0.10), (3, 0.18)):
        ax.plot(
            x, y, color=color, linewidth=linewidth, alpha=alpha, solid_capstyle="round"
        )
    ax.plot(
        x,
        y,
        color=color,
        linewidth=2,
        marker="o",
        markersize=6,
        markerfacecolor=color,
        markeredgecolor=color,
        label=label,
    )


def _color_for_conference(name, fallback_cycle):
    return CONFERENCE_COLORS.get(name) or next(fallback_cycle)


def _draw_dns_gap_bridges(ax, df_cleaned, column_colors):
    """For each conference, draw a thin dotted line straight across any DNS gap - connecting its
    two closest surrounding scored points - instead of just leaving a blank stretch. Experimental
    (per user request): meant to help the eye track a conference's trend through a season or two
    where it briefly didn't score, without implying it actually had a score in between.

    Only bridges a genuine DNS gap (at least one *other* conference has data somewhere in that
    stretch, proving those weeks/years actually happened); never bridges into the trailing
    not-yet-reached weeks of an in-progress season, where nothing has data yet and there's nothing
    real to connect.
    """
    any_data_mask = df_cleaned.notna().any(axis=1)
    for column in df_cleaned.columns:
        series = df_cleaned[column]
        valid_positions = [i for i, v in enumerate(series.values) if pd.notna(v)]
        for start, end in zip(valid_positions, valid_positions[1:]):
            if end - start <= 1:
                continue  # adjacent already - the normal solid line connects these
            if not any_data_mask.iloc[start + 1 : end].any():
                continue  # nothing scored anywhere in the gap - not-yet-reached weeks, not a DNS
            ax.plot(
                [df_cleaned.index[start], df_cleaned.index[end]],
                [series.iloc[start], series.iloc[end]],
                color=column_colors[column],
                linestyle=(0, (2, 2)),
                linewidth=1.6,
                alpha=0.55,
                zorder=2,
            )


_CONFERENCE_NAME_RE = re.compile(r"^\('(?P<name>.*?)',")
_RANK_NUMBER_RE = re.compile(r"-?\d+\.?\d*")


def _cell_conference_name(cell) -> str:
    """Pull the conference/team name out of a "('Name', value)" cell from a week CSV - value may
    be a bare number, 'DNS', or wrapped like 'np.int64(9)'/'np.float64(9.0)', but the name is
    always the first quoted string, so this doesn't need to understand the value at all.
    """
    if pd.isna(cell):
        return None
    match = _CONFERENCE_NAME_RE.match(str(cell).strip())
    return match.group("name") if match else None


def _cell_rank(cell) -> float:
    """Pull the numeric rank out of a "('Team', rank)" cell from a week CSV, or None if the cell
    is blank."""
    if pd.isna(cell):
        return None
    number_match = _RANK_NUMBER_RE.search(str(cell))
    return float(number_match.group()) if number_match else None


def _champion_conference(year: int, team_dir: str) -> str:
    """Return the conference shortName of the AP poll's #1 team in `year`'s Final week, read
    straight from that week's own stored per-week CSV - or None if that file doesn't exist yet
    (i.e. the season hasn't reached its Final poll).

    Reads the raw per-week file (not the summary_statistics rollup) because it lists each
    conference's scoring teams ranked best-to-worst, so the #1 overall team is always the top
    entry under whichever conference column it belongs to - independent of 4-team/5-team scoring
    mode, since that only changes how many teams count toward the conference's score, not who
    ranked #1 nationally.
    """
    week_file = os.path.join(
        os.path.abspath(os.curdir),
        "data",
        str(year),
        team_dir,
        f"{year}_week_final.csv",
    )
    if not os.path.exists(week_file):
        return None
    raw = pd.read_csv(week_file, header=None)
    if raw.empty:
        return None
    conference_names = [_cell_conference_name(cell) for cell in raw.iloc[0]]
    for col_idx, top_team_cell in enumerate(raw.iloc[1]):
        rank = _cell_rank(top_team_cell)
        if rank == 1:
            return conference_names[col_idx]
    return None


def generate_graph(
    summary_stats_df,
    title: str = "Weekly Results",
    show: bool = True,
    drop_empty_weeks: bool = True,
    year: int = None,
    champion_highlight: dict = None,
) -> plt.plot:
    """
    :param drop_empty_weeks: if True (default), weeks/rows with no data at all across every
        conference are dropped before plotting - appropriate for the cross-season Final-rankings
        chart, where an in-progress season shouldn't appear as an empty x-axis category. Pass False
        to keep every not-yet-reached week visible as a blank stretch of x-axis instead (used for the
        current season's weekly chart, so the plot visually shows how far into the season we are).
    :param year: season year, used (if we've cached it - see store_data.record_regular_season_week_
        count()) to definitively suppress an unused "Week 16" even mid-season, rather than waiting
        until Week 15 and Final are both recorded to infer it from the data.
    :param champion_highlight: optional {x_label: conference_name} map built by the caller (see
        graph_year() / graph_final_rankings_by_year(), which know how to look up each season's AP
        #1 team via _champion_conference()). Where that conference actually has a plotted point at
        x_label, it's redrawn larger with a white outline - the same fill color, just marking it as
        that period's national champion's conference. Where the conference has no point there (it
        didn't score enough teams that period - DNS), the point can't be ringed, so instead that
        x-axis tick label itself is colored to match the conference and gets a trailing "†", with a
        footnote explaining the symbol - this is the only indication in that case, so it still
        surfaces the champion without fabricating a data point that would compromise the scoring.
    """
    # Set Week column as index
    summary_stats_df.set_index("Week", inplace=True)
    # Drop the unused "Week 16" placeholder for seasons that only ran 15 weeks (Issue #22)
    summary_stats_df = sd.suppress_unused_week_16(summary_stats_df, year=year)

    # Drop columns (conferences) with no data all season; optionally also drop empty week rows
    df_cleaned = summary_stats_df
    if drop_empty_weeks:
        df_cleaned = df_cleaned.dropna(axis=0, how="all")
    df_cleaned = df_cleaned.dropna(axis=1, how="all")

    fig, ax = plt.subplots(figsize=(12, 8))
    fig.patch.set_facecolor(BACKGROUND_COLOR)
    ax.set_facecolor(BACKGROUND_COLOR)

    # Plot the data, one glowing line per conference
    fallback_cycle = itertools.cycle(FALLBACK_COLORS)
    column_colors = {}
    for column in df_cleaned.columns:
        color = _color_for_conference(column, fallback_cycle)
        column_colors[column] = color
        _glow_plot(ax, df_cleaned.index, df_cleaned[column], color, column)

    # Bridge DNS gaps with a thin dotted line so a conference's trend still reads across a
    # stretch where it briefly didn't score (see _draw_dns_gap_bridges() docstring for scope)
    _draw_dns_gap_bridges(ax, df_cleaned, column_colors)

    # Mark each period's national-champion conference at its point: same dot and fill color, just
    # larger with a bright white outline (keeps working regardless of which conference color it
    # lands on, including yellow). If that conference has no point there at all - it didn't score
    # enough teams that period (DNS) - there's nothing to ring, so its x-axis tick label is colored
    # and marked instead (see the tick-styling section below); off_chart_champions collects those.
    off_chart_champions = {}
    if champion_highlight:
        for x_label, champ_conf in champion_highlight.items():
            has_point = (
                champ_conf in df_cleaned.columns
                and x_label in df_cleaned.index
                and pd.notna(df_cleaned.loc[x_label, champ_conf])
            )
            if has_point:
                ax.plot(
                    [x_label],
                    [df_cleaned.loc[x_label, champ_conf]],
                    marker="o",
                    markersize=11,
                    markerfacecolor=column_colors[champ_conf],
                    markeredgecolor="#FFFFFF",
                    markeredgewidth=2.2,
                    linestyle="none",
                    zorder=6,
                )
            elif x_label in df_cleaned.index:
                off_chart_champions[x_label] = champ_conf

    # Force the full category range into view - matplotlib's autoscale only considers the finite
    # (non-NaN) data range, which would otherwise crop out any not-yet-reached, still-blank weeks
    ax.set_xlim(-0.5, len(df_cleaned.index) - 0.5)

    # Customize the plot
    ax.set_title(title, color=TEXT_COLOR, fontsize=16, fontweight="bold", pad=20)
    ax.grid(True, color=GRID_COLOR, linewidth=0.5, alpha=0.6)

    # X-axis ticks along the top, angled, left-to-right chronological order
    ax.xaxis.set_ticks_position("top")
    ax.xaxis.set_label_position("top")
    ax.tick_params(axis="x", colors=TEXT_COLOR, rotation=45)
    ax.tick_params(axis="y", colors=TEXT_COLOR)

    # Pin the current (categorical) tick positions down with a FixedLocator/FixedFormatter before
    # appending "†" to any label - matplotlib's categorical unit converter otherwise regenerates
    # each tick's text from its own position->category mapping at draw time, silently reverting a
    # plain Text.set_text() call (color/bold stick fine since those are separate properties, which
    # is why this bug is easy to miss - only the appended character disappears)
    original_labels = [tick_label.get_text() for tick_label in ax.get_xticklabels()]
    ax.set_xticks(ax.get_xticks())
    ax.set_xticklabels(
        [
            f"{label}†" if label in off_chart_champions else label
            for label in original_labels
        ]
    )

    for tick_label, original in zip(ax.get_xticklabels(), original_labels):
        tick_label.set_ha("left")
        champ_conf = off_chart_champions.get(original)
        if champ_conf is not None:
            color = (
                column_colors.get(champ_conf)
                or CONFERENCE_COLORS.get(champ_conf)
                or OFF_CHART_CHAMPION_FALLBACK_COLOR
            )
            tick_label.set_color(color)
            tick_label.set_fontweight("bold")

    if off_chart_champions:
        fig.text(
            0.01,
            0.005,
            "† national champion's conference didn't score enough teams to appear that season",
            color=TEXT_COLOR,
            alpha=0.8,
            fontsize=8,
            style="italic",
            ha="left",
            va="bottom",
        )

    # Y-axis: best (lowest) score at the top, gridlines every 5 points
    ax.yaxis.set_major_locator(MultipleLocator(5))
    ax.invert_yaxis()

    for spine in ax.spines.values():
        spine.set_color(GRID_COLOR)

    # Legend along the bottom, one column per conference, no border
    legend = ax.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, -0.05),
        ncol=len(df_cleaned.columns),
        frameon=False,
    )
    for text in legend.get_texts():
        text.set_color(TEXT_COLOR)

    fig.tight_layout()

    # Watermark, bottom-right corner, below the legend
    fig.text(
        0.99,
        0.01,
        "@ap_cfb_xc",
        color=TEXT_COLOR,
        alpha=0.6,
        fontsize=9,
        style="italic",
        ha="right",
        va="bottom",
    )

    # Show the plot
    if show:
        plt.show()

    return plt


def get_graph_from_file(csv_path: str, show: bool = True) -> plt.plot:
    """Shortcut wrapper to get the summary statistics graph from a file"""
    print(f"Reading summary statistics from {csv_path}")
    df = pd.read_csv(csv_path)
    graph = generate_graph(df, show=show)
    return graph


def save_graph(plot: plt.plot, file_name: str = None) -> str:
    """Save the current figure held by `plot` (the return value of generate_graph()/graph_year())
    as a PNG under <repo root>/images/, creating that directory if it doesn't exist.

    :param plot: the matplotlib.pyplot module returned by generate_graph()/graph_year()
    :param file_name: output filename; defaults to the graph's title if not given
    """
    fig = plot.gcf()

    if file_name is None:
        file_name = fig.axes[0].get_title()

    for invalid_char in '<>:"/\\|?*':
        file_name = file_name.replace(invalid_char, "_")
    file_name = file_name.strip()
    if not file_name.lower().endswith(".png"):
        file_name += ".png"

    image_dir = os.path.join(os.path.abspath(os.curdir), "images")
    os.makedirs(image_dir, exist_ok=True)

    out_path = os.path.join(image_dir, file_name)
    fig.savefig(out_path, facecolor=fig.get_facecolor())
    print("Graph has been successfully saved to", out_path, "\n")
    return out_path


def most_recent_year(data_dir: str = None) -> int:
    """Return the highest year (as int) present as a subdirectory of `data/`."""
    data_dir = data_dir or os.path.join(os.path.abspath(os.curdir), "data")
    years = [int(entry) for entry in os.listdir(data_dir) if entry.isdigit()]
    return max(years)


def graph_year(year: int, num_scoring_teams: int = 5, show: bool = True) -> plt.plot:
    """Graph a single season's summary statistics.

    :param year: season year, e.g. 2024
    :param num_scoring_teams: 4 or 5 (top-N teams summed per conference); defaults to 5
    :param show: whether to display the plot window; defaults to True
    """
    if num_scoring_teams not in (4, 5):
        raise ValueError("num_scoring_teams must be 4 or 5")

    print(f"Graphing {year} season ({num_scoring_teams}-team scoring)...")
    team_dir = sd.quad if num_scoring_teams == 4 else sd.pent
    summary_file = os.path.join(
        os.path.abspath(os.curdir),
        "data",
        str(year),
        team_dir,
        f"{year}_{team_dir}_summary_statistics.csv",
    )
    df = pd.read_csv(summary_file)
    # summary CSVs index their rows under "AP_XC_{N}_Team_Race" rather than "Week"
    idx_header = f"AP_XC_{team_dir.title()}_Race"
    df.rename(columns={idx_header: "Week"}, inplace=True)

    # Only set if the Final poll has actually been recorded for this season - _champion_conference()
    # returns None while the season is still in progress, mid-season, since week_final.csv won't
    # exist yet
    champ_conf = _champion_conference(year, team_dir)
    champion_highlight = {"Final": champ_conf} if champ_conf else None

    title = f"CFB AP {year} XC — {num_scoring_teams} Teams"
    # Keep every not-yet-reached week visible (blank) so the chart shows how far into the season we are
    return generate_graph(
        df,
        title=title,
        show=show,
        drop_empty_weeks=False,
        year=year,
        champion_highlight=champion_highlight,
    )


# Conferences that are the same underlying entity across a rename/membership change, folded into
# one continuous line in the cross-season "Final rankings by year" view (see
# graph_final_rankings_by_year() / _merge_realigned_conferences() below) instead of splitting into
# two disconnected series. Single-season graphs (graph_year()) call generate_graph() directly and
# never go through this merge, so they still show whichever name was actually in effect that year.
CROSS_SEASON_CONFERENCE_MERGES = {
    "Pac-10": "Pac-12",  # Colorado & Utah joined, 2011 - keeps the "12" label per Pac-12 convention
    "Big East": "Big East/American",  # Big East football became the American Athletic Conference
    "American": "Big East/American",  # in 2013 - https://en.wikipedia.org/wiki/American_Conference_(NCAA)
}


def _merge_realigned_conferences(final_row: pd.Series) -> pd.Series:
    """Relabel a season's Final row per CROSS_SEASON_CONFERENCE_MERGES so cross-season graphs
    treat each renamed/realigned conference as one continuous entity."""
    rename_map = {
        old: new
        for old, new in CROSS_SEASON_CONFERENCE_MERGES.items()
        if old in final_row.index
    }
    return final_row.rename(rename_map) if rename_map else final_row


def graph_final_rankings_by_year(
    num_scoring_teams: int = 5, show: bool = True
) -> plt.plot:
    """Graph each conference's Final-week score across every season on record (one point per year),
    using the same styling as graph_year().

    :param num_scoring_teams: 4 or 5 (top-N teams summed per conference); defaults to 5
    :param show: whether to display the plot window; defaults to True
    """
    if num_scoring_teams not in (4, 5):
        raise ValueError("num_scoring_teams must be 4 or 5")

    team_dir = sd.quad if num_scoring_teams == 4 else sd.pent
    idx_header = f"AP_XC_{team_dir.title()}_Race"
    data_dir = os.path.join(os.path.abspath(os.curdir), "data")

    years = sorted(int(entry) for entry in os.listdir(data_dir) if entry.isdigit())
    print(
        f"Graphing Final rankings across {years[0]}-{years[-1]} ({num_scoring_teams}-team scoring)..."
    )
    final_rows = {}
    for year in years:
        summary_file = os.path.join(
            data_dir, str(year), team_dir, f"{year}_{team_dir}_summary_statistics.csv"
        )
        if not os.path.exists(summary_file):
            continue
        season_df = pd.read_csv(summary_file).set_index(idx_header)
        if "Final" in season_df.index:
            final_rows[str(year)] = _merge_realigned_conferences(season_df.loc["Final"])

    print(
        f"Collected Final-week rows for {len(final_rows)} of {len(years)} seasons "
        "(a season still in progress may have a blank Final row)."
    )

    # Only count years with an actual (non-blank) Final score toward the title's displayed range -
    # an in-progress season with no Final data yet shouldn't stretch the range shown to the reader
    years_with_data = [int(y) for y, row in final_rows.items() if row.notna().any()]
    title_start, title_end = (
        (min(years_with_data), max(years_with_data))
        if years_with_data
        else (years[0], years[-1])
    )

    final_by_year_df = pd.DataFrame.from_dict(final_rows, orient="index")
    final_by_year_df.index.name = "Week"
    final_by_year_df.reset_index(inplace=True)

    # For each year with a recorded Final poll, look up its AP #1 team's conference and relabel it
    # through the same realignment merges as the data itself, so the highlighted point lands on
    # whichever merged column (e.g. "Pac-12", "Big East/American") that year's line actually uses
    champion_highlight = {}
    for year in years_with_data:
        champ_conf = _champion_conference(year, team_dir)
        if champ_conf:
            champion_highlight[str(year)] = CROSS_SEASON_CONFERENCE_MERGES.get(
                champ_conf, champ_conf
            )

    title = f"CFB AP Final XC — {num_scoring_teams} Teams ({title_start}-{title_end})"
    return generate_graph(
        final_by_year_df, title=title, show=show, champion_highlight=champion_highlight
    )


def update_final_rankings_graph(num_scoring_teams: int = 5) -> str:
    """Regenerate and save the all-time Final-rankings-by-year graph for one scoring mode, headless,
    to its fixed filename under `images/`."""
    plot = graph_final_rankings_by_year(num_scoring_teams=num_scoring_teams, show=False)
    out_path = save_graph(plot, f"final_rankings_by_year_{num_scoring_teams}team.png")
    plot.close("all")
    return out_path


def run_final_rankings_graphs():
    """Regenerate the all-time Final-rankings-by-year graphs for both 4-team and 5-team scoring and
    save them to `images/` under fixed filenames. Runs headless (no plot windows) since this is meant
    for unattended/weekly execution."""
    print("-----------------------")
    print("Regenerating all-time Final-rankings-by-year graphs (4-team and 5-team)")
    for num_scoring_teams in (4, 5):
        update_final_rankings_graph(num_scoring_teams)
    print("Final-rankings-by-year graphs are up to date.")
    print("-----------------------")


def run_all_weekly_graphs():
    """Regenerate the current-week 4-team and 5-team graphs for the most recent year and save them
    to `images/`, overwriting whatever was there before. Meant to run on a weekly schedule so the
    images referenced from the README stay current under fixed filenames; runs headless (no plot
    windows) since this is meant for unattended execution."""
    year = most_recent_year()
    print("-----------------------")
    print(f"Regenerating current-week graphs for {year} (4-team and 5-team)")
    for num_scoring_teams in (4, 5):
        plot = graph_year(year, num_scoring_teams=num_scoring_teams, show=False)
        save_graph(plot, f"current_week_{num_scoring_teams}team.png")
        plot.close("all")
    print("Current-week graphs are up to date.")
    print("-----------------------")


def graph_all_data():
    """Graph all the data in the repo."""
    tss = "_team_summary_statistics.csv"
    data_dir = os.path.join(os.path.abspath(os.curdir), "data")

    for it in os.listdir(data_dir):
        fp = os.path.join(data_dir, it)
        print(it, os.path.isdir(fp))
        for subdir in os.listdir(fp):
            fps = os.path.join(fp, subdir)
            for item in os.listdir(fps):
                if item.endswith(tss):
                    new_name = item.replace(tss, "_team_graph.csv")
                    new_path = os.path.join(fps, new_name)
                    # TODO: Insert execution + image saving here.


if __name__ == "__main__":
    graph_year(most_recent_year(), num_scoring_teams=5)

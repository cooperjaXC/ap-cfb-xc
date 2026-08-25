import itertools
import os

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
# here (Mountain West, CUSA, Sun Belt, MAC, Pac-12, Patriot, FBS Indep., etc.)
# fall back to FALLBACK_COLORS below — they rarely field enough ranked teams
# to score, so no fixed color was ever established for them.
CONFERENCE_COLORS = {
    "SEC": "#1E90FF",  # blue
    "Big Ten": "#FFD500",  # yellow
    "ACC": "#FF3B3B",  # red
    "Big 12": "#B266FF",  # purple
    "American": "#FF9500",  # orange (AAC) - reserved, rarely scores
    "Pac-12": "#87CEFA",  # light blue - defunct as of 2024, but present in historical seasons
}
FALLBACK_COLORS = ["#B0B0B0", "#3DDC84", "#FF6EC7", "#00E5FF", "#C0FF00"]

BACKGROUND_COLOR = "#2B2B2B"
GRID_COLOR = "#555555"
TEXT_COLOR = "#E8E8E8"


def _glow_plot(ax, x, y, color, label):
    """Draw a line with a soft halogen-style glow by layering translucent strokes."""
    for linewidth, alpha in ((8, 0.05), (5, 0.10), (3, 0.18)):
        ax.plot(x, y, color=color, linewidth=linewidth, alpha=alpha, solid_capstyle="round")
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


def generate_graph(summary_stats_df, title: str = "Weekly Results", show: bool = True) -> plt.plot:
    """ """
    # Set Week column as index
    summary_stats_df.set_index("Week", inplace=True)

    # Drop rows and columns with all NaN values
    df_cleaned = summary_stats_df.dropna(axis=0, how="all").dropna(axis=1, how="all")

    fig, ax = plt.subplots(figsize=(12, 8))
    fig.patch.set_facecolor(BACKGROUND_COLOR)
    ax.set_facecolor(BACKGROUND_COLOR)

    # Plot the data, one glowing line per conference
    fallback_cycle = itertools.cycle(FALLBACK_COLORS)
    for column in df_cleaned.columns:
        color = _color_for_conference(column, fallback_cycle)
        _glow_plot(ax, df_cleaned.index, df_cleaned[column], color, column)

    # Customize the plot
    ax.set_title(title, color=TEXT_COLOR, fontsize=16, fontweight="bold", pad=20)
    ax.grid(True, color=GRID_COLOR, linewidth=0.5, alpha=0.6)

    # X-axis ticks along the top, angled, left-to-right chronological order
    ax.xaxis.set_ticks_position("top")
    ax.xaxis.set_label_position("top")
    ax.tick_params(axis="x", colors=TEXT_COLOR, rotation=45)
    ax.tick_params(axis="y", colors=TEXT_COLOR)
    for tick_label in ax.get_xticklabels():
        tick_label.set_ha("left")

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

    team_dir = sd.quad if num_scoring_teams == 4 else sd.pent
    summary_file = os.path.join(
        os.path.abspath(os.curdir), "data", str(year), team_dir, f"{year}_{team_dir}_summary_statistics.csv"
    )
    df = pd.read_csv(summary_file)
    # summary CSVs index their rows under "AP_XC_{N}_Team_Race" rather than "Week"
    idx_header = f"AP_XC_{team_dir.title()}_Race"
    df.rename(columns={idx_header: "Week"}, inplace=True)

    title = f"CFP AP {year} XC — {num_scoring_teams} Teams"
    return generate_graph(df, title=title, show=show)


def graph_final_rankings_by_year(num_scoring_teams: int = 5, show: bool = True) -> plt.plot:
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
    final_rows = {}
    for year in years:
        summary_file = os.path.join(data_dir, str(year), team_dir, f"{year}_{team_dir}_summary_statistics.csv")
        if not os.path.exists(summary_file):
            continue
        season_df = pd.read_csv(summary_file).set_index(idx_header)
        if "Final" in season_df.index:
            final_rows[str(year)] = season_df.loc["Final"]

    final_by_year_df = pd.DataFrame.from_dict(final_rows, orient="index")
    final_by_year_df.index.name = "Week"
    final_by_year_df.reset_index(inplace=True)

    title = f"CFP AP Final XC — {num_scoring_teams} Teams ({years[0]}-{years[-1]})"
    return generate_graph(final_by_year_df, title=title, show=show)


def run_final_rankings_graphs():
    """Regenerate the all-time Final-rankings-by-year graphs for both 4-team and 5-team scoring and
    save them to `images/` under fixed filenames. Runs headless (no plot windows) since this is meant
    for unattended/weekly execution."""
    for num_scoring_teams in (4, 5):
        plot = graph_final_rankings_by_year(num_scoring_teams=num_scoring_teams, show=False)
        save_graph(plot, f"final_rankings_by_year_{num_scoring_teams}team.png")
        plot.close("all")


def run_all_weekly_graphs():
    """Regenerate the current-week 4-team and 5-team graphs for the most recent year and save them
    to `images/`, overwriting whatever was there before. Meant to run on a weekly schedule so the
    images referenced from the README stay current under fixed filenames; runs headless (no plot
    windows) since this is meant for unattended execution."""
    year = most_recent_year()
    for num_scoring_teams in (4, 5):
        plot = graph_year(year, num_scoring_teams=num_scoring_teams, show=False)
        save_graph(plot, f"current_week_{num_scoring_teams}team.png")
        plot.close("all")


def graph_all_data():
    """ Graph all the data in the repo."""
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

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


def generate_graph(summary_stats_df, title: str = "Weekly Results") -> plt.plot:
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
    plt.show()

    return plt


def get_graph_from_file(csv_path: str) -> plt.plot:
    """Shortcut wrapper to get the summary statistics graph from a file"""
    df = pd.read_csv(csv_path)
    graph = generate_graph(df)
    return graph


def save_graph(plot: plt.plot, out_path: str):
    return out_path


def most_recent_year(data_dir: str = None) -> int:
    """Return the highest year (as int) present as a subdirectory of `data/`."""
    data_dir = data_dir or os.path.join(os.path.abspath(os.curdir), "data")
    years = [int(entry) for entry in os.listdir(data_dir) if entry.isdigit()]
    return max(years)


def graph_year(year: int, num_scoring_teams: int = 5) -> plt.plot:
    """Graph a single season's summary statistics.

    :param year: season year, e.g. 2024
    :param num_scoring_teams: 4 or 5 (top-N teams summed per conference); defaults to 5
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
    return generate_graph(df, title=title)


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

"""
Full weekly pipeline run: pull the latest AP rankings from ESPN, store them in `data/`, and
regenerate the current-week graphs and 5-team standings table referenced by the README. If this
week's data turns out to be a season's actual Final AP poll, also regenerate that scoring mode's
all-time Final-rankings-by-year graph - otherwise that graph is left untouched, since it should
only move once a season truly ends.

Intended to be run on a recurring (weekly) schedule during the season so `data/`, the
`images/current_week_{4,5}team.png` files, and the README table stay current without manual
intervention.
"""

import store_data as sd
import graph_data as gd
import readme_table as rt


def weekly_update():
    """Fetch and store this week's AP rankings for both scoring modes, then regenerate the
    current-week graphs (images/current_week_{4,5}team.png) referenced from the README. Only
    regenerates the all-time Final-rankings-by-year graph for a scoring mode whose Final AP poll was
    just recorded - a normal in-season or preseason week leaves that graph alone. Refreshes the
    README's 5-team standings table last, so a problem there can't hold up the graphs.
    """
    four_team_results = sd.store_weekly_results(four_team_score=True)
    five_team_results = sd.store_weekly_results(four_team_score=False)

    gd.run_all_weekly_graphs()

    for num_scoring_teams, weekly_results in (
        (4, four_team_results),
        (5, five_team_results),
    ):
        if sd.is_final_week_recorded(weekly_results):
            print(
                f"Final AP rankings recorded for {num_scoring_teams}-team scoring - "
                "updating the all-time Final-rankings graph."
            )
            gd.update_final_rankings_graph(num_scoring_teams=num_scoring_teams)
        else:
            print(
                f"{num_scoring_teams}-team scoring: season not yet finalized - "
                "skipping the all-time Final-rankings graph."
            )

    rt.update_readme_table(num_scoring_teams=5)


if __name__ == "__main__":
    weekly_update()

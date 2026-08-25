"""
Full weekly pipeline run: pull the latest AP rankings from ESPN, store them in `data/`, and
regenerate the current-week graphs referenced by the README.

Intended to be run on a recurring (weekly) schedule during the season so `data/` and the
`images/current_week_{4,5}team.png` files stay current without manual intervention.
"""
import store_data as sd
import graph_data as gd


def weekly_update():
    """Fetch and store this week's AP rankings for both scoring modes, then regenerate the
    current-week graphs (images/current_week_{4,5}team.png) referenced from the README."""
    sd.store_weekly_results(four_team_score=True)
    sd.store_weekly_results(four_team_score=False)

    gd.run_all_weekly_graphs()


if __name__ == "__main__":
    weekly_update()

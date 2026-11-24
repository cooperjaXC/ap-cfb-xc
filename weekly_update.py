"""
Full weekly pipeline run: pull the latest AP rankings from ESPN, store them in `data/`, and
regenerate the current-week graphs and 5-team standings table referenced by the README. If this
week's data turns out to be a season's actual Final AP poll, also regenerate that scoring mode's
all-time Final-rankings-by-year graph - otherwise that graph is left untouched, since it should
only move once a season truly ends.

Last, it publishes the week's post (socials.py) to X and to Bluesky, each with the 5-team graph and
the standings-table image attached. That step can never break the rest: it runs after everything
else, and each platform is attempted on its own, so one failing (or being skipped) has no effect on
the other. Any failure is reported and swallowed, and a week already posted to a platform
(data/social_post_log.json) is not posted there again. Set the environment variable
AP_XC_SKIP_SOCIAL=1 to run the update without posting anywhere.

Intended to be run on a recurring (weekly) schedule during the season so `data/`, the
`images/current_week_{4,5}team.png` files, and the README table stay current without manual
intervention.
"""

import os

import store_data as sd
import graph_data as gd
import readme_table as rt
from espn_api import APPollNotPublishedError


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

    post_to_socials()


def post_to_socials():
    """Draw the standings-table image and publish the week's post to X and to Bluesky. Everything
    here is best-effort: whatever goes wrong is printed, never raised, so the stored data, graphs
    and README from the steps above are unaffected. Each platform is tried independently of the
    other: an exception (or a refusal) on X does not stop the Bluesky post, and vice versa."""
    print("-----------------------")
    try:
        gd.generate_week_table_image(num_scoring_teams=5)
    except Exception as err:  # the post can still go out with the graph alone
        print(f"Could not draw the standings table image: {err!r}")
    if os.environ.get("AP_XC_SKIP_SOCIAL"):
        print("AP_XC_SKIP_SOCIAL is set - not posting to X or Bluesky.")
        return
    try:
        # Imported here so a missing posting dependency can't stop the update itself
        import socials

        post = socials.compose_post()
    except Exception as err:
        print(f"Social posts skipped (could not build the post): {err!r}")
        return
    for platform, publish in (
        ("X", socials.post_to_x),
        ("Bluesky", socials.post_to_bluesky),
    ):
        print(f"--- {platform} ---")
        try:
            publish(post, dry_run=False)
        except Exception as err:  # never let one platform stop the other
            print(f"{platform} post skipped: {err!r}")
    print("-----------------------")


if __name__ == "__main__":
    try:
        weekly_update()
    except APPollNotPublishedError as not_yet_published:
        # Nothing was stored or regenerated; safe to simply re-run later.
        raise SystemExit(f"No update made. {not_yet_published}")

""" College Football API data from https://api.collegefootballdata.com/api/docs/?url=/api-docs.json#/ """
from __future__ import print_function
import requests as req, pandas as pd, os, sys

base_url = "api.collegefootballdata.com/"


def swagger_ui_api_path_generator(
    req_type="rankings", year=2020, week=1, reg_v_post="regular"
):
    """ Return a URL based upon input vars.
    Original function that was in this file when updates started being applied."""
    year = str(year)
    teamurl = (r"https://api.collegefootballdata.com/teams/fbs?year=" + year,)
    confurl = (r"https://api.collegefootballdata.com/conferences",)
    rankurl = (
        r"https://api.collegefootballdata.com/rankings?year="
        + year
        + "&week="
        + str(week)
        + "&seasonType="
        + reg_v_post
    )
    print(rankurl)
    req_urlz = {"teams": teamurl, "conferences": confurl, "rankings": rankurl}
    if req_type not in req_urlz:
        print(
            req_type,
            "is not a valid input. Will return the Rankings API. Re-call function to set another option.",
        )
        req_type = "rankings"

    the_url = req_urlz[req_type]

    return the_url


def swagger_first_test():
    """The first test of swagger API, chunked into a function for storage."""
    rankings = req.get(swagger_ui_api_path_generator())  # week=2), timeout=10)
    rankings_json = rankings.json()
    # import json
    # json_data = json.loads(firstreq.text)

    the_polls = rankings_json[0]["polls"]
    print(the_polls)
    for poll in the_polls:
        if poll["poll"] == "AP Top 25":
            # print(poll)
            rankings = poll["ranks"]
            # print(rankings)
            [
                print(rank["rank"], rank["school"], "-", rank["conference"])
                for rank in rankings
            ]


def cfbd_github_example():
    """ The example set by the package's GitHub Repo.
    https://github.com/CFBD/cfbd-python#getting-started.
    Use and improve off of this code. """
    # from __future__ import print_function  # SyntaxError: from __future__ imports must occur at the beginning of the file
    import time
    import cfbd
    from cfbd.rest import ApiException
    from pprint import pprint

    # Configure API key authorization: ApiKeyAuth
    configuration = cfbd.Configuration()
    configuration.api_key['Authorization'] = 'YOUR_API_KEY'
    configuration.api_key_prefix['Authorization'] = 'Bearer'

    # create an instance of the API class
    api_instance = cfbd.BettingApi(cfbd.ApiClient(configuration))
    game_id = 56  # int | Game id filter (optional)
    year = 56  # int | Year/season filter for games (optional)
    week = 56  # int | Week filter (optional)
    season_type = 'regular'  # str | Season type filter (regular or postseason) (optional) (default to regular)
    team = 'team_example'  # str | Team (optional)
    home = 'home_example'  # str | Home team filter (optional)
    away = 'away_example'  # str | Away team filter (optional)
    conference = 'conference_example'  # str | Conference abbreviation filter (optional)

    try:
        # Betting lines
        api_response = api_instance.get_lines(game_id=game_id, year=year, week=week, season_type=season_type, team=team,
                                              home=home, away=away, conference=conference)
        pprint(api_response)
    except ApiException as e:
        print("Exception when calling BettingApi->get_lines: %s\n" % e)

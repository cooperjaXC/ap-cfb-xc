""" College Football API data from https://api.collegefootballdata.com/api/docs/?url=/api-docs.json#/ """

import requests as req, pandas as pd, os, sys

base_url = "api.collegefootballdata.com/"


def swagger_ui_api_path_generator(
    req_type="rankings", year=2020, week=1, reg_v_post="regular"
):
    """ Return a URL based upon input vars. """
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

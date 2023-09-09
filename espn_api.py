"""
ESPN API data from http://site.api.espn.com/apis/site/v2/sports/football/college-football/rankings

BIG PROBLEM: The `cfbd` API does not have "others receiving votes."
However, [a doc on GitHub](https://gist.github.com/akeaswaran/b48b02f1c94f873c6655e7129910fc3b?permalink_comment_id=4376177)
leads to the rankings API endpoint for ESPN that *does* have others receiving votes data.
But, does it have historical rankings data?...

GitHub user @akeaswaran contributed the following re. historical data: (see https://github.com/cooperjaXC/ap-cfb-xc/issues/7#issuecomment-1709418119)
> http://sports.core.api.espn.com/v2/sports/football/leagues/college-football/seasons/2023/types/2/weeks/1/rankings/1?lang=en&region=us.
You can change the seasons and weeks values appropriately to get historical data,
and...you can get data on bowl/playoff games with a types value of 3 and weeks value of 1.

A few notes:
* Looks like a rankings value 1 in the URL is the AP poll -- you can manipulate this value for different polls if you want them.
* You won't need to use BeautifulSoup for this either -- just a requests.get() to grab the JSON and the json package to parse it.
* You'll have to make GET requests to the URLs provided in the $ref key of each record in the ranks array to get detailed team information.
* It does seem like there is receiving-votes data in there for your needs under the others array.
"""

import requests
from datetime import datetime as dt

import PollGrabber as pg

espn_api = "http://site.api.espn.com/apis/site/v2/sports/football/college-football/rankings"
historical_espn_api_pth = "http://sports.core.api.espn.com/v2/sports/football/leagues/college-football/seasons/2023/types/2/weeks/1/rankings/1"


def espn_api_url_generator(year=dt.now().year, week='current'):
    """ Take a week and year request from the user and generate & return the correct ESPN API URL from it.
    Very similar to the PollGrabber.apweeklyurlgenerator() function from v1"""

    # Properly format the date based on user input using a helper function
    year, week = pg.dateprocessing(year=year, week=week)

    # Prepare substrings to create the URL
    aponlylinkespn2 = r"http://www.espn.com/college-football/rankings/_/poll/1/week/"
    base_espn_api_pth = "http://sports.core.api.espn.com/v2/sports/football/leagues/college-football/seasons/"
                              # "2023/types/2/weeks/1/rankings/1"
    # defaultlink = historical_espn_api_pth

    # Determine what type of poll you want
    ap_poll_path_code = "1"
    coaches_poll_path_code = str(2)
    cfp_poll_path_code = str(21)
    # In the future, you can conduct this analysis with more poll types.
    chosen_poll_path = "/rankings/" + str(ap_poll_path_code)

    # # So the poll URL will look like:
    # base_espn_api_pth + year + season_type + week + chosen_poll_path

    # Is the week entered indicating the final week?
    if week.lower() == "final":
        week = "/weeks/1"
        season_type = "/types/3"
        url = base_espn_api_pth + year + season_type + week + chosen_poll_path
    # Check for entries wanting the most up-to-date rankings
    elif week.lower() == "current":  # in currentlist:
        # The default link here returns a JSON in a slightly different format than the week-by-week JSON response.
        # So, we can't just use the default link, eg `espn_api`  # default link
        default_url = espn_api  # default link
        # Instead, the default URL contains within its JSON response the correct, expected URL.
        # # It just needs some slight tweaks.
        # So, we need to
        # 1) get the response from the default,
        # 2) grab the correct URL,
        # 3) transform it,
        # and 4) set it as the URL for this function.
        #
        # 1) get the response from the default
        default_response = requests.get(default_url)
        # # Extract the JSON
        resp_json = default_response.json()
        # 2) grab the correct URL
        all_rankings_resp = resp_json['rankings']
        ap_top_tf_resp = [rnk for rnk in all_rankings_resp if 'aptop25' in rnk['name'].lower().replace(" ","")][0]
        target_url = ap_top_tf_resp['$ref']
        # 3) transform the URL
        # # Remove all the crud after the "?"
        # # Keep the part before the "?" character
        after_remove_char = "?"
        target_url = target_url.split(after_remove_char, 1)[0]
        # # Replace the '.pvt' with '.com'
        target_url = target_url.replace('.pvt', '.com')
        # 4) set it as the URL for this function.
        url = target_url
        # Get rid of useless variables
        del target_url, default_response, resp_json, all_rankings_resp,ap_top_tf_resp
    else:
        week = "/weeks/"+ str(week)
        season_type = "/types/2"
        url = base_espn_api_pth + year + season_type + week + chosen_poll_path

    print("Week", week.replace("/weeks/", "")+',', year, "season")
    return url


# TODO Hit the API for the JSON response
# TODO Parse the requests result for teams. The historical APIs return team URLs, not the team name.
# Looks like (for UGA): http://sports.core.api.espn.com/v2/sports/football/leagues/college-football/seasons/2021/teams/61?lang=en&region=us

if __name__ == '__main__':
    the_url = espn_api_url_generator(2021, 'final')
    print(the_url)

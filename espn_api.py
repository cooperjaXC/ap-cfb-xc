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
reference_key = '$ref'


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
        ap_top_tf_resp = [rnk for rnk in all_rankings_resp if str(ap_poll_path_code) == rnk['id']][0]
        target_url = ap_top_tf_resp[reference_key]
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


def get_team_info(team_api_url):
    """ ESPN API Rankings embed a team API URL to identify who is in what ranking.
     We need to parse that API's JSON to figure out what team it's referencing. """
    teamjson = requests.get(team_api_url).json()

    # TODO Parse the requests result for teams. The historical APIs return team URLs, not the team name.
    # Looks like this (example for UGA, 2023 week 3):
    # http://sports.core.api.espn.com/v2/sports/football/leagues/college-football/seasons/2021/teams/61?lang=en&region=us
    # RESULT JSON KEYS:
    # dict_keys(['$ref', 'id', 'guid', 'uid', 'alternateIds', 'slug', 'location', 'name', 'nickname', 'abbreviation',
    # 'displayName', 'shortDisplayName', 'color', 'alternateColor', 'isActive', 'isAllStar', 'logos', 'record',
    # 'oddsRecords', 'athletes', 'venue', 'groups', 'ranks', 'statistics', 'leaders', 'links', 'injuries', 'notes',
    # 'againstTheSpreadRecords', 'awards', 'franchise', 'projection', 'events', 'coaches', 'college'])
    #


def get_top_tfive(top_twentyfive_json: dict):
    """ Process the ESPN AP API response to pull a dictionary of the top 25 teams.
    Returns dictionary of the teams. """
# len(top_tfive_json) = 25, 1 for each team.
    # Establish a dictionary that will hold the results.
    # # To account for ties, the dicts will have keys of rankings and values of *lists* of teams.
    # # # Even though most rankings will only have on team's data in the list (in dict format), still keep list format.
    top_tfive_teams = {}
    for team in top_twentyfive_json:
        # Each team's keys: dict_keys(['current', 'previous', 'points', 'firstPlaceVotes', 'trend', 'record', 'team', 'date', 'lastUpdated'])
        team_api_url = team['team'][reference_key]
        # Using the embedded team API, get all the info you need on that team.
        team_info_dict = get_team_info(team_api_url)
        # Add the team info to the dictionary storing all this data.
        ranking = team['current']
        if ranking not in top_tfive_teams:
            # This is the first team at this ranking; add it to the dictionary.
            top_tfive_teams[ranking] = [team_info_dict]
        else:
            # There is a tie, so append to the list rather than creating it.
            top_tfive_teams[ranking].append(team_info_dict)

    return top_tfive_teams


def others_receiving_votes(others_json: dict):
    """ Process the ESPN AP API response to pull a dictionary of the other teams receiving votes.
    Returns dictionary of the teams. """
    # Get Others Receiving Votes as a continuation of the rankings, 26 to X where X is max n(Teams receiving votes).
    # Similar to the 'top_tfive_teams' variable, establish a dictionary that will hold the results.
    # # To account for ties, the dicts will have keys of rankings and values of *lists* of teams.
    # # # Even though most rankings will only have on team's data in the list (in dict format), still keep list format.
    other_teams = {}

    # TODO Parse the JSON of 'others' to get the rankings and teams in the same format as get_top_tfive() returns.

    return other_teams


def poll_grabber(espn_ap_link):
    """ Use requests to grab the AP Poll from ESPN's website,
    the link to which is generated by apweeklyurlgenerator() """
    print(espn_ap_link)
    # Get the ESPN AP Top 25 rankings
    r = requests.get(espn_ap_link)
    # Parse the JSON response
    rjson = r.json()
    # dict_keys(['$ref', 'id', 'name', 'shortName', 'type', 'occurrence', 'date', 'headline', 'shortHeadline', 'season',
    # # 'lastUpdated', 'ranks', 'others', 'droppedOut', 'availability'])
    # Get the Top 25 Teams
    top_tfive_json = rjson['ranks']
    top_twenty_five_teams = get_top_tfive(top_tfive_json)
    print("- - - - - - - -")
    # Get Others Receiving Votes as a continuation of the rankings, 26 to X where X is max n(Teams receiving votes).
    others = 'others'
    if others in rjson.keys():
        # Others received votes.
        ojson = rjson[others]
        other_teams = others_receiving_votes(ojson)
    else:
        # Either no 26th team received votes (unlikely unless passing the CFP Top 25 poll) or there was an error.
        print("No other teams receiving votes this week.")
        other_teams = {}

    # Merge the results of the top 25 and the Others
    all_receiving_votes = top_twenty_five_teams.copy()
    all_receiving_votes.update(other_teams)

    return all_receiving_votes


if __name__ == '__main__':
    the_url = espn_api_url_generator(2021, 'final')
    print(the_url)

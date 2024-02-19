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

import requests, numpy as np, pandas as pd
from datetime import datetime as dt
from distutils.util import strtobool


# import PollGrabber as pg

espn_api = "http://site.api.espn.com/apis/site/v2/sports/football/college-football/rankings"
historical_espn_api_pth = "http://sports.core.api.espn.com/v2/sports/football/leagues/college-football/seasons/2023/types/2/weeks/1/rankings/1"
reference_key = '$ref'
conference_key = 'conference'
key_shortName = 'shortName'
did_not_score = "DNS"

def string_to_bool(string_to_become_bool, suppress_prints=False):
    """Converts true/false strings into boolean items for downstream python use."""
    # https://stackoverflow.com/questions/715417/converting-from-a-string-to-boolean-in-python
    tf_input = str(string_to_become_bool)
    if str(tf_input).lower() in [
        "tru",
        "tr",
        "truth",
        "y",
        "yes",
        "1",
        "yep",
        "oui",
        "si",
        "vrai",
        "cierto",
        "please",
        "ye",
    ]:
        tf_input = "true"
    if str(tf_input).lower() in [
        "fal",
        "fa",
        "fals",
        "no",
        "n",
        "na",
        "0",
        "nope",
        "non",
        "faux",
        "falsa",
        "falso",
    ]:
        tf_input = "false"
    try:
        the_bool_trueorfalse = bool(strtobool(tf_input))
    except ValueError:  # Exception: # as exc:
        if suppress_prints is False:
            print(tf_input, "is an invalid bool. Pass a valid value.")
            # print(exc)
        the_bool_trueorfalse = None

    return the_bool_trueorfalse


def api_json_response(api_url):
    """ Shortcut function for requests.get()ting APIs that return JSON results.
    Functionized in case Requests ever changes how one accesses API responses
    or all-encompassing changes to all instances of executing this process for this project are necessary. """
    json_response = requests.get(api_url).json()
    return json_response


def date_processing(year, week):
    """ Processes raw inputs of week and year for downstream use in multiple functions """
    prelist = ["preseason", "initial", "first", "init", "pre", str(0)]
    currentlist = ["current", "present", "default", None, str(None)]
    finallist = ["final", "f", "complete", "total", "last", "fin"]

    # YEAR FORMATTING
    year = str(year)
    # Format abbreviated dates for the 2000s
    if len(year) != 4:
        if len(year) == 2 and (year[0] == "1" or year[0] == "0"):
            # Assume the entry was an abreviation of a year. Add the 20__ before it.
            year = "20" + str(year)

    # WEEK FORMATTING
    # Preseason?
    week = str(week)
    if week.lower() in prelist:
        week = "1"

    # Current week?
    elif week.lower() in currentlist:
        week = "current"

    # Final?
    elif week.lower() in finallist:
        week = "final"
    # If the week entered is higher than 16, assume user wants final rankings.
    try:
        # 16 is the max # of regular season weeks allowed, tho usually 15. "CFB Leap Year." See 2014 & 2019
        if int(week) > 16:
            week = "final"
    except:
        pass

    if int(year) < int(2014):
        print(
            "Warning: Others Receiving Votes not stored by ESPN before the 2014 season."
        )

    # Compile into a list for returning
    #    Must return a list of strings
    datelist = [week, year]
    return year, week



def espn_api_url_generator(year=dt.now().year, week='current') -> str:
    """ Take a week and year request from the user and generate & return the correct ESPN API URL from it.
    Very similar to the PollGrabber.apweeklyurlgenerator() function from v1"""

    # Properly format the date based on user input using a helper function
    year, week = date_processing(year=year, week=week)

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
        # 1) get the response from the default & extract the JSON
        resp_json = api_json_response(default_url)
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
        del target_url, resp_json, all_rankings_resp,ap_top_tf_resp
    else:
        week = "/weeks/"+ str(week)
        season_type = "/types/2"
        url = base_espn_api_pth + year + season_type + week + chosen_poll_path

    print("Week", week.replace("/weeks/", "")+',', year, "season")
    return url


def parse_conference_info(conference_api_url: str) -> dict:
    """
    ESPN team APIs lead to 'group' URLs to identify who is in what conference.
     We need to parse that API's JSON to figure out what conference it's referencing.

     From https://gist.github.com/akeaswaran/b48b02f1c94f873c6655e7129910fc3b?permalink_comment_id=4343861#gistcomment-4343861
     And a list of NCAA Conference ids if anyone needs it:

    Id = 80, Conf = FBS (I-A)
    Id = 1, Conf = ACC
    Id = 151, Conf = American
    Id = 4, Conf = Big 12
    Id = 5, Conf = Big Ten
    Id = 12, Conf = C-USA
    Id = 18, Conf = FBS Indep
    Id = 15, Conf = MAC
    Id = 17, Conf = Mountain West
    Id = 9, Conf = Pac-12
    Id = 8, Conf = SEC
    Id = 37, Conf = Sun Belt
    Id = 81, Conf = FCS (I-AA)
    Id = 176, Conf = ASUN
    Id = 20, Conf = Big Sky
    Id = 40, Conf = Big South
    Id = 48, Conf = CAA
    """
    # Example API endpoint:
    # https://sports.core.api.espn.com/v2/sports/football/leagues/college-football/seasons/2023/types/2/groups/8?lang=en&region=us
    cjson = api_json_response(conference_api_url)
    # print(cjson)
    # Sometimes this will return a team's division within conference. We want the full conference. Link to that.
    parent_key = 'parent'
    parent_group_url = cjson[parent_key][reference_key]
    fbs_d1_url = r"http://sports.core.api.espn.com/v2/sports/football/leagues/college-football/seasons/2023/types/2/groups/80?lang=en&region=us"
    tries = 0 # Adding a counter to prevent infinate loops
    does_it_match = parent_group_url == fbs_d1_url
    # print(does_it_match)
    # Could also use isConference to work out the conference status. It leaves out divisions and FBS 1
    isConference = string_to_bool(str(cjson['isConference']).title())
    if isConference:
        return cjson
    # print(isConference)
    while (does_it_match is False) and (tries < 10):
        # print(f"Group #{tries+1} was not valid conference. Trying to access it.")
        # keep accessing the parent's URL's response till you get up to just under the NCAA FBS 1, ID = 80.
        # print(parent_group_url == fbs_d1_url)
        cjson = api_json_response(parent_group_url)
        # print(cjson)
        # Could also use isConference to work out the conference status. It leaves out divisions and FBS 1
        isConference = string_to_bool(str(cjson['isConference']).title())
        if isConference:
            return cjson
        parent_group_url = cjson[parent_key][reference_key]
        does_it_match = parent_group_url == fbs_d1_url
        if does_it_match:
            # Breaking manually because the while loop isn't working as it should.
            break
        tries += 1
        # print(tries, str(does_it_match), '\n--------')
    if tries >= 10:
        print("Your request to access conference API data has timed out; there was an error.")

    return cjson


def get_team_info(team_api_url: str) -> dict:
    """ ESPN API Rankings embed a team API URL to identify who is in what ranking.
     We need to parse that API's JSON to figure out what team it's referencing. """
    teamjson = api_json_response(team_api_url)
    # print(teamjson['nickname'])

    # Looks like this (example for UGA, 2023 week 3):
    # http://sports.core.api.espn.com/v2/sports/football/leagues/college-football/seasons/2021/teams/61?lang=en&region=us
    # RESULT JSON KEYS:
    # dict_keys(['$ref', 'id', 'guid', 'uid', 'alternateIds', 'slug', 'location', 'name', 'nickname', 'abbreviation',
    # 'displayName', 'shortDisplayName', 'color', 'alternateColor', 'isActive', 'isAllStar', 'logos', 'record',
    # 'oddsRecords', 'athletes', 'venue', 'groups', 'ranks', 'statistics', 'leaders', 'links', 'injuries', 'notes',
    # 'againstTheSpreadRecords', 'awards', 'franchise', 'projection', 'events', 'coaches', 'college'])
    #
    # Key keys (lol): "location" = team name; "name" = mascot; "nickname" = team name abbrev.;
    # # "displayName" = location + name; "color" & "alternateColor" (use for graphs)
    #
    # EX for FSU:
    # {
    # $ref http://sports.core.api.espn.com/v2/sports/football/leagues/college-football/seasons/2023/teams/52?lang=en&region=us
    # id 52
    # guid fa181128-4809-a209-1add-d5a3b0cefd3c
    # uid s:20~l:23~t:52
    # alternateIds {'sdr': '5995'}
    # slug florida-state-seminoles
    # location Florida State
    # name Seminoles
    # nickname Florida St
    # abbreviation FSU
    # displayName Florida State Seminoles
    # shortDisplayName Seminoles
    # color 782f40
    # alternateColor ceb888
    # isActive True
    # isAllStar False
    # logos [{'href': 'https://a.espncdn.com/i/teamlogos/ncaa/500/52.png', 'width': 500, 'height': 500, 'alt': '', 'rel': ['full', 'default'], 'lastUpdated': '2018-06-05T12:08Z'}, {'href': 'https://a.espncdn.com/i/teamlogos/ncaa/500-dark/52.png', 'width': 500, 'height': 500, 'alt': '', 'rel': ['full', 'dark'], 'lastUpdated': '2018-06-05T12:08Z'}]
    # record {'$ref': 'http://sports.core.api.espn.com/v2/sports/football/leagues/college-football/seasons/2023/types/2/teams/52/record?lang=en&region=us'}
    # oddsRecords {'$ref': 'http://sports.core.api.espn.com/v2/sports/football/leagues/college-football/seasons/2023/types/0/teams/52/odds-records?lang=en&region=us'}
    # athletes {'$ref': 'http://sports.core.api.espn.com/v2/sports/football/leagues/college-football/seasons/2023/teams/52/athletes?lang=en&region=us'}
    # venue {'$ref': 'http://sports.core.api.espn.com/v2/sports/football/leagues/college-football/venues/3697?lang=en&region=us', 'id': '3697', 'fullName': 'Doak Campbell Stadium', 'address': {'city': 'Tallahassee', 'state': 'FL', 'zipCode': '32304'}, 'capacity': 79560, 'grass': True, 'indoor': False, 'images': [{'href': 'https://a.espncdn.com/i/venues/college-football/day/interior/3697.jpg', 'width': 2000, 'height': 1125, 'alt': '', 'rel': ['full', 'day', 'interior']}]}
    # groups {'$ref': 'http://sports.core.api.espn.com/v2/sports/football/leagues/college-football/seasons/2023/types/2/groups/1?lang=en&region=us'}
    # ranks {'$ref': 'http://sports.core.api.espn.com/v2/sports/football/leagues/college-football/seasons/2023/teams/52/ranks?lang=en&region=us'}
    # statistics {'$ref': 'http://sports.core.api.espn.com/v2/sports/football/leagues/college-football/seasons/2023/types/2/teams/52/statistics?lang=en&region=us'}
    # leaders {'$ref': 'http://sports.core.api.espn.com/v2/sports/football/leagues/college-football/seasons/2023/types/2/teams/52/leaders?lang=en&region=us'}
    # links [{'language': 'en-US', 'rel': ['clubhouse', 'desktop', 'team'], 'href': 'https://www.espn.com/college-football/team/_/id/52/florida-state-seminoles', 'text': 'Clubhouse', 'shortText': 'Clubhouse', 'isExternal': False, 'isPremium': False}, {'language': 'en-US', 'rel': ['clubhouse', 'mobile', 'team'], 'href': 'http://www.espn.com/college-football/team/_/id/52/florida-state-seminoles', 'text': 'Clubhouse', 'shortText': 'Clubhouse', 'isExternal': False, 'isPremium': False}, {'language': 'en-US', 'rel': ['roster', 'desktop', 'team'], 'href': 'http://www.espn.com/college-football/team/roster/_/id/52', 'text': 'Roster', 'shortText': 'Roster', 'isExternal': False, 'isPremium': False}, {'language': 'en-US', 'rel': ['stats', 'desktop', 'team'], 'href': 'http://www.espn.com/college-football/team/stats/_/id/52', 'text': 'Statistics', 'shortText': 'Statistics', 'isExternal': False, 'isPremium': False}, {'language': 'en-US', 'rel': ['schedule', 'desktop', 'team'], 'href': 'http://www.espn.com/college-football/team/schedule/_/id/52', 'text': 'Schedule', 'shortText': 'Schedule', 'isExternal': False, 'isPremium': False}, {'language': 'en-US', 'rel': ['awards', 'desktop', 'team'], 'href': 'http://www.espn.com/college-football/awards/_/team/52', 'text': 'Awards', 'shortText': 'Awards', 'isExternal': False, 'isPremium': False}]
    # injuries {'$ref': 'http://sports.core.api.espn.com/v2/sports/football/leagues/college-football/teams/52/injuries?lang=en&region=us'}
    # notes {'$ref': 'http://sports.core.api.espn.com/v2/sports/football/leagues/college-football/teams/52/notes?lang=en&region=us'}
    # againstTheSpreadRecords {'$ref': 'http://sports.core.api.espn.com/v2/sports/football/leagues/college-football/seasons/2023/types/2/teams/52/ats?lang=en&region=us'}
    # awards {'$ref': 'http://sports.core.api.espn.com/v2/sports/football/leagues/college-football/seasons/2023/teams/52/awards?lang=en&region=us'}
    # franchise {'$ref': 'http://sports.core.api.espn.com/v2/sports/football/leagues/college-football/franchises/52?lang=en&region=us'}
    # projection {'$ref': 'http://sports.core.api.espn.com/v2/sports/football/leagues/college-football/seasons/2023/teams/52/projection?lang=en&region=us'}
    # events {'$ref': 'http://sports.core.api.espn.com/v2/sports/football/leagues/college-football/seasons/2023/teams/52/events?lang=en&region=us'}
    # coaches {'$ref': 'http://sports.core.api.espn.com/v2/sports/football/leagues/college-football/seasons/2023/teams/52/coaches?lang=en&region=us'}
    # college {'$ref': 'http://sports.core.api.espn.com/v2/colleges/52?lang=en&region=us'}
    # }

    # Maybe we just keep this big record and just add sensical conference info to it. We may need some data downstream.
    # # Can always come back and whittle the big dict down.

    # Get the conference data from its API endpoint
    conference_URL = teamjson['groups'][reference_key]
    the_conference_json = parse_conference_info(conference_URL)
    # Add the conference's dict to the team dict
    teamjson[conference_key] = the_conference_json

    return teamjson


def get_top_tfive(top_twentyfive_json: list) -> dict:
    """ Process the ESPN AP API response to pull a dictionary of the top 25 teams.
    Returns dictionary of the teams. """
    #  #Try accepting the whole rankings json dict and parsing down from that.
    # top_twentyfive_json = rankings_JSON['ranks']

    # len(top_tfive_json) = 25, 1 for each team.
    # Establish a dictionary that will hold the results.
    # # To account for ties, the dicts will have keys of rankings and values of *lists* of teams.
    # # # Even though most rankings will only have on team's data in the list (in dict format), still keep list format.
    top_tfive_teams = {}
    for team in top_twentyfive_json:
        # Each team's keys: dict_keys(['current', 'previous', 'points', 'firstPlaceVotes', 'trend', 'record', 'team', 'date', 'lastUpdated'])
        team_api_url = team['team'][reference_key]
        # Add the team info to the dictionary storing all this data.
        ranking = team['current']
        # Using the embedded team API, get all the info you need on that team.
        team_info_dict = get_team_info(team_api_url)

        # Parse that data to get what you need like this below
        # # Do this again later to work with the dict data you got.
        team_name = team_info_dict['nickname']
        teams_conference = team_info_dict[conference_key]["shortName"]
        print(f"{ranking}: {team_name} ({teams_conference})")

        if ranking not in top_tfive_teams:
            # This is the first team at this ranking; add it to the dictionary.
            top_tfive_teams[ranking] = [team_info_dict]
        else:
            # There is a tie, so append to the list rather than creating it.
            top_tfive_teams[ranking].append(team_info_dict)

    return top_tfive_teams


def others_receiving_votes(others_json: list, ranked_teams: int = 25) -> dict:
    """ Process the ESPN AP API response to pull a dictionary of the other teams receiving votes.
    Returns dictionary of the teams. """
    # Get Others Receiving Votes as a continuation of the rankings, 26 to X where X is max n(Teams receiving votes).
    # Similar to the 'top_tfive_teams' variable, establish a dictionary that will hold the results.
    # # To account for ties, the dicts will have keys of rankings and values of *lists* of teams.
    # # # Even though most rankings will only have on team's data in the list (in dict format), still keep list format.

    # len(others_json) = X, 1 for each team, where x = Total - 25.
    # Establish a dictionary that will hold the results.
    # # To account for ties, the dicts will have keys of rankings and values of *lists* of teams.
    other_teams = {}
    sorting_points_dict = {}
    for team in others_json:
        # Each team's keys: dict_keys(['current', 'previous', 'points', 'firstPlaceVotes', 'trend', 'record', 'team', 'date', 'lastUpdated'])
        team_api_url = team['team'][reference_key]
        # Add the team info to the dictionary storing all this data.
        points = float(team['points'])
        # Using the embedded team API, get all the info you need on that team.
        team_info_dict = get_team_info(team_api_url)

        # Parse that data to get what you need like this below
        # # Do this again later to work with the dict data you got.
        team_name = team_info_dict['nickname']
        teams_conference = team_info_dict[conference_key][key_shortName]
        print(f"{points} points: {team_name} ({teams_conference})")

        # Add the points and the team to the dict
        if points not in sorting_points_dict:
            # This is the first team at this ranking; add it to the dictionary.
            sorting_points_dict[points] = [team_info_dict]
        else:
            # There is a tie, so append to the list rather than creating it.
            sorting_points_dict[points].append(team_info_dict)
    # print(sorting_points_dict)

    # Sort the points from votes into >25 rankings.
    next_ranking = ranked_teams +0
    while sorting_points_dict:
        # While the sorting points dict is not empty
        max_remain_pts = max(sorting_points_dict)
        # next_up_target_points = sorting_points_dict[max_remain_pts]
        teams_to_add = sorting_points_dict[max_remain_pts]
        num_teams_to_add = len(teams_to_add)
        # Add teams to the dict based on their rankings
        next_ranking = next_ranking + 1
        other_teams[next_ranking] = teams_to_add
        # Based on how many teams were added for each value &
        # knowing that there will be a single stepper to the next ranking,
        # properly define the next ranking that should be used.
        next_ranking = next_ranking + (num_teams_to_add - 1)

        # Remove the points from the sorting dict so the while loop can function
        del sorting_points_dict[max_remain_pts]
        # print(other_teams)

    return other_teams


def handle_ties(all_teams_receiving_votes_dict: dict) -> dict:
    """ Sometimes teams receive the same number of points.
    In these scenarios, find the middle number for an XC score."""
    broken_ties_dict = {}
    # Find average of ties
    for rank, teams in all_teams_receiving_votes_dict.items():
        # teamlist = tsixplus[score]
        teamspervote = len(teams)
        if teamspervote == 1:
            # rankingdict[tsixcounter] = teamlist[0]
            # inverserankingdict[teamlist[0]] = tsixcounter
            # tsixcounter += 1
            broken_ties_dict[rank] = teams
        else:  # If there is a tie in votes:
            # Calculate the average rank for tied teams
            calc_range = [rank + i for i in range(teamspervote)]
            # average_rank = (rank * teamspervote) / teamspervote
            average_rank = sum(calc_range) / len(calc_range)
            broken_ties_dict[average_rank] = teams
    print(broken_ties_dict)

    return broken_ties_dict


def poll_grabber(espn_ap_link):
    """ Use requests to grab the AP Poll from ESPN's website,
    the link to which is generated by apweeklyurlgenerator() """
    print(espn_ap_link)
    # Get the ESPN AP Top 25 rankings & Parse the JSON response
    rjson = api_json_response(espn_ap_link)
    # dict_keys(['$ref', 'id', 'name', 'shortName', 'type', 'occurrence', 'date', 'headline', 'shortHeadline', 'season',
    # # 'lastUpdated', 'ranks', 'others', 'droppedOut', 'availability'])
    # Get the Top 25 Teams
    top_tfive_json = rjson['ranks']
    top_twenty_five_teams = get_top_tfive(top_tfive_json)
    # Figure out how many teams are ranked, including ties.
    n_ranked_teams = sum([len(top_twenty_five_teams[t]) for t in list(range(1, 26)) if t in top_twenty_five_teams])
    # n_ranked_teams = len(top_twenty_five_teams) + (len(top_twenty_five_teams[25])-1)
    print("- - - - - - - -")
    # Get Others Receiving Votes as a continuation of the rankings, 26 to X where X is max n(Teams receiving votes).
    others = 'others'
    if others in rjson.keys():
        # Others received votes.
        ojson = rjson[others]
        other_teams = others_receiving_votes(ojson, n_ranked_teams)
    else:
        # Either no 26th team received votes (unlikely unless passing the CFP Top 25 poll) or there was an error.
        print("No other teams receiving votes this week.")
        other_teams = {}

    # Merge the results of the top 25 and the Others
    all_receiving_votes = top_twenty_five_teams.copy()
    all_receiving_votes.update(other_teams)

    xc_formatted_rankings = handle_ties(all_receiving_votes)

    return xc_formatted_rankings


def all_conferences_in_rankings(formatted_rankings: dict) -> list:
    """ Get the conferences that are included in the rankings for the given week."""
    all_conferences = []
    for rank in formatted_rankings:
        for team_dict in formatted_rankings[rank]:
            shortName = team_dict[conference_key][key_shortName]
            if shortName not in all_conferences:
                all_conferences.append(shortName)
    return all_conferences


def teams_points_by_conference(formatted_rankings: dict) -> pd.DataFrame:
    """ Set up the conferences' dict to create the XC scores downstream. """
    present_conferences = all_conferences_in_rankings(formatted_rankings)
    conferences_df = pd.DataFrame(columns=present_conferences)

    conference_pts_dict = {}

    for rank in formatted_rankings:
        for team_dict in formatted_rankings[rank]:
            conferenceShortName = team_dict[conference_key][key_shortName]
            team_name = team_dict['nickname']
            print(f"{str(rank)} points: {team_name} ({conferenceShortName})")
            if conferenceShortName not in conference_pts_dict:
                conference_pts_dict[conferenceShortName] = [(team_name, rank)]
            else:
                conference_pts_dict[conferenceShortName].append((team_name, rank))
    print(conference_pts_dict)

    # Find the max number of teams any conference had.
    max_n_ranked_teams = max([len(conference_pts_dict[c]) for c in  conference_pts_dict])
    # Set up the dataframe
    # # Add null items to the end of conferences w/o the max number of teams.
    for cnfrnc in conference_pts_dict:
        scoring_teams = conference_pts_dict[cnfrnc]
        n_teams_scoring = len(scoring_teams)
        nulls_to_fill = max_n_ranked_teams - n_teams_scoring
        while nulls_to_fill > 0:
            scoring_teams.append(np.nan)
            nulls_to_fill -= 1
        # Add teams to the dataframe
        conferences_df[cnfrnc] = scoring_teams
    print(conferences_df)
    return conferences_df


def calc_conference_scores(conferences_init_df: pd.DataFrame, four_team_race: bool = False) -> dict:
    """ Get the scores for the conferences that appear in the rankings. """
    if bool(four_team_race):
        scoring_teams = 4
    else:
        scoring_teams = 5

    scoring_dict = {}
    for cnfcol in conferences_init_df.columns:
        # teams_scoring = conferences_init_df[cnfcol].count
        teams_scoring = conferences_init_df.count()[cnfcol]
        if teams_scoring >= scoring_teams:
            cutoff_teams_df = conferences_init_df[cnfcol][:scoring_teams]
            if any(cutoff_teams_df.isna()):
                # Shouldn't get here b/c of existing conditional. But just in case.
                scoring_dict[cnfcol] = did_not_score
            else:
                scores_only_df = cutoff_teams_df.apply(lambda x: x[1] if ((not x[1] in [np.nan, None,'']) and (type(x[1]) in [float,int])) else np.nan)
                scoring_dict[cnfcol] = scores_only_df.sum()
        else:
            scoring_dict[cnfcol] = did_not_score
    print(scoring_dict)

    return scoring_dict


def conference_scoring_order(scoring_dict: dict):
    """ Once you have generated conference XC scores with calc_conference_scores(), we need to see who won!
    Do that here. """
    only_scoring_conferences = {}
    for sc in scoring_dict:
        if scoring_dict[sc] != did_not_score:
            only_scoring_conferences[sc] = scoring_dict[sc]
    print(only_scoring_conferences)
    # Move that data back to a pandas DF for easy working.
    # # Note: conference name is in the index.
    onlyScoresDF=pd.DataFrame(only_scoring_conferences.values(), index=only_scoring_conferences.keys())
    # Name the score column
    xcsc = 'xc_score'
    onlyScoresDF.columns = [xcsc]
    # TODO get xcsc to integer format if possible, ie if all scores are floats with 0 in tenths space.
    # Move conference name index to its own column, and eventually make that the first column.
    onlyScoresDF['conference'] = onlyScoresDF.index
    onlyScoresDF.reset_index(drop=True, inplace=True)
    # Sort by scores in decending order. Lowest score wins!
    onlyScoresDF = onlyScoresDF.sort_values(xcsc)
    # TODO Turns out PD rank ranks like I did manually upstream. Apply the 5th/6th runner tiebreaker upstream and have it apply here.
    onlyScoresDF['place'] = onlyScoresDF[xcsc].rank()
    # Order the columns
    onlyScoresDF= onlyScoresDF[['conference', 'place', xcsc]]
    onlyScoresDF.reset_index(inplace=True, drop=True)

    print(onlyScoresDF)


def full_ap_xc_run(year, week):
    """ From the year and week you want, return a full report of conferences' scores. """
    the_url = espn_api_url_generator(year, week)
    print(the_url)
    main_custom_format_rankings = poll_grabber(the_url)
    conference_points = teams_points_by_conference(main_custom_format_rankings)
    calc_xc_scores = calc_conference_scores(conference_points)
    xc_scoring = conference_scoring_order(calc_xc_scores)
    # TODO figure out what exactly to return.
    # Maybe make that conditional too.
    # # Make an argument in this function to let user determine what type of result they want.
    return xc_scoring


if __name__ == '__main__':
    # full_ap_xc_run = espn_api_url_generator(2021, 'final')
    full_ap_xc_run = espn_api_url_generator(2023, 'current')  # Good choice; has tie at #21.

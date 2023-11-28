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
conference_key = 'conference'


def api_json_response(api_url):
    """ Shortcut function for requests.get()ting APIs that return JSON results.
    Functionized in case Requests ever changes how one accesses API responses
    or all-encompassing changes to all instances of executing this process for this project are necessary. """
    json_response = requests.get(api_url).json()
    return json_response


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


def parse_conference_info(conference_api_url: str):
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
    isConference = bool(str(cjson['isConference']).title())
    # print(isConference)
    while (does_it_match is False) and (tries < 10):
        # print(f"Group #{tries+1} was not valid conference. Trying to access it.")
        # keep accessing the parent's URL's response till you get up to just under the NCAA FBS 1, ID = 80.
        # print(parent_group_url == fbs_d1_url)
        cjson = api_json_response(parent_group_url)
        # print(cjson)
        isConference = bool(str(cjson['isConference']).title())
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


def get_team_info(team_api_url: str):
    """ ESPN API Rankings embed a team API URL to identify who is in what ranking.
     We need to parse that API's JSON to figure out what team it's referencing. """
    teamjson = api_json_response(team_api_url)
    # print(teamjson['nickname'])

    # TODO Parse the requests result for teams. The historical APIs return team URLs, not the team name.
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


def get_top_tfive(top_twentyfive_json: list):
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


def others_receiving_votes(others_json: list, ranked_teams: int = 25):
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
        teams_conference = team_info_dict[conference_key]["shortName"]
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


def handle_ties(all_teams_receiving_votes_dict: dict):
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


if __name__ == '__main__':
    # the_url = espn_api_url_generator(2021, 'final')
    the_url = espn_api_url_generator(2023, 'current')  # Good choice; has tie at #21.
    print(the_url)
    main_custom_format_rankings = poll_grabber(the_url)

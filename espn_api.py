"""
ESPN API data from http://site.api.espn.com/apis/site/v2/sports/football/college-football/rankings

GitHub user @akeaswaran contributed the following re. historical data: (see https://github.com/cooperjaXC/ap-cfb-xc/issues/7#issuecomment-1709418119)
> http://sports.core.api.espn.com/v2/sports/football/leagues/college-football/seasons/2023/types/2/weeks/1/rankings/1?lang=en&region=us.
You can change the seasons and weeks values appropriately to get historical data,
and...you can get data on bowl/playoff games with a types value of 3 and weeks value of 1.
There is also receiving-votes data in there under the others array.
"""

import requests, numpy as np, pandas as pd
from datetime import datetime as dt
from distutils.util import strtobool

# Define multi-function variables
espn_api = (
    "http://site.api.espn.com/apis/site/v2/sports/football/college-football/rankings"
)
reference_key = "$ref"
conference_key = "conference"
key_shortName = "shortName"
did_not_score = "DNS"
tiebreak_posit_col = "tiebreaker_posit"
final = "final"
current = "current"
preseason = "preseason"


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


def what_week_is_it():
    """What CFB week is it?"""
    # Get current date
    current_date = dt.now()

    # Extract day, month, and year
    day = current_date.day
    month = current_date.month
    year = current_date.year

    # Determine week based on current date.
    #  The AP keeps releasing the preseason rankings earlier and earlier, so default August runs to the upcoming season.
    if month < 8:  # or (month == 8 and day <= 20):
        # It is the off-season, so default to last season.
        year -= 1
        week = final
    else:
        week = current

    return year, week


def date_processing(year=None, week=None) -> tuple:
    """ Processes raw inputs of week and year for downstream use in multiple functions """
    prelist = [preseason, "initial", "first", "init", "pre", str(0)]
    currentlist = [current, "present", "default", None, str(None), "now"]
    finallist = [final, "f", "complete", "total", "last", "fin"]

    # WEEK FORMATTING
    if week is None:
        week = current
    # Preseason?
    week = str(week)
    if week.lower() in prelist:
        week = "1"
    # Current week?
    elif week.lower() in currentlist:
        week = current
    # Final?
    elif week.lower() in finallist:
        week = final
    # If the week entered is higher than 16, assume user wants final rankings.
    try:
        # 16 is the max # of regular season weeks allowed, tho usually 15. "CFB Leap Year." See 2014 & 2019
        if int(week) > 16:
            week = final
    except:
        pass

    # YEAR FORMATTING
    this_year = dt.now().year
    if year is None:
        year = this_year
    year = str(year)
    # Format abbreviated dates for the 2000s
    if len(year) != 4:
        if len(year) == 2 and (year[0] == "1" or year[0] == "0"):
            # Assume the entry was an abreviation of a year. Add the 20__ before it.
            year = "20" + str(year)
    # Check if this is being run in the offseason.
    if year == str(this_year):
        if week == current:
            year, week = what_week_is_it()
        else:
            year, _ = what_week_is_it()
        year = str(year)
    if int(year) < int(2014):
        print(
            "Warning: Others Receiving Votes not stored by ESPN before the 2014 season."
        )

    # Compile for returning a tuple of strings
    return str(year), str(week)


def espn_api_url_generator(year=None, week=None) -> str:
    """ Take a week and year request from the user and generate & return the correct ESPN API URL from it.
    Very similar to the PollGrabber.apweeklyurlgenerator() function from v1"""

    # Properly format the date based on user input using a helper function
    # # Will handle Null/None inputs by the user.
    year, week = date_processing(year=year, week=week)

    # Prepare substrings to create the URL
    aponlylinkespn2 = r"http://www.espn.com/college-football/rankings/_/poll/1/week/"
    base_espn_api_pth = "http://sports.core.api.espn.com/v2/sports/football/leagues/college-football/seasons/"
    # "2023/types/2/weeks/1/rankings/1"
    # defaultlink = "http://sports.core.api.espn.com/v2/sports/football/leagues/college-football/seasons/2023/types/2/weeks/1/rankings/1"

    # Determine what type of poll you want
    ap_poll_path_code = "1"
    coaches_poll_path_code = str(2)
    cfp_poll_path_code = str(21)
    # In the future, you can conduct this analysis with more poll types.
    chosen_poll_path = "/rankings/" + str(ap_poll_path_code)

    # # So the poll URL will look like:
    # base_espn_api_pth + year + season_type + week + chosen_poll_path

    # Is the week entered indicating the final week?
    def final_week_vars():
        fweek = "/weeks/1"
        fseason_type = "/types/3"
        return (
            fweek,
            fseason_type,
            base_espn_api_pth + year + fseason_type + fweek + chosen_poll_path,
        )

    if week.lower() == final:
        week, season_type, url = final_week_vars()
    # Check for entries wanting the most up-to-date rankings
    elif week.lower() == current:
        if str(year) == str(what_week_is_it()[0]):
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
            all_rankings_resp = resp_json["rankings"]
            ap_top_tf_resp = [
                rnk for rnk in all_rankings_resp if str(ap_poll_path_code) == rnk["id"]
            ][0]
            target_url = ap_top_tf_resp[reference_key]
            # 3) transform the URL
            # # Remove all the crud after the "?"
            # # Keep the part before the "?" character
            after_remove_char = "?"
            target_url = target_url.split(after_remove_char, 1)[0]
            # # Replace the '.pvt' with '.com'
            target_url = target_url.replace(".pvt", ".com")
            # 4) set it as the URL for this function.
            url = target_url
            # Get rid of useless variables
            del target_url, resp_json, all_rankings_resp, ap_top_tf_resp
        else:
            # The user likely means an older year's final rankings.
            week, season_type, url = final_week_vars()
    else:
        week = "/weeks/" + str(week)
        season_type = "/types/2"
        url = base_espn_api_pth + year + season_type + week + chosen_poll_path

    print("Week", week.replace("/weeks/", "") + ",", year, "season")
    return url


def extract_week_from_url(url: str) -> str:
    """ From the ESPN API URL, figure out what week it is.
    Use result of espn_api_url_generator() function as string input."""
    # defaultlink = "http://sports.core.api.espn.com/v2/sports/football/leagues/college-football/seasons/2023/types/2/weeks/1/rankings/1"
    # Find the index of "weeks/"
    index = url.find("weeks/") + len("weeks/")
    # Extract the numeral after "weeks/"
    week_num = url[index:].split("/")[0]
    # print(week_num)
    return week_num


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
    parent_key = "parent"
    parent_group_url = cjson[parent_key][reference_key]
    fbs_d1_url = r"http://sports.core.api.espn.com/v2/sports/football/leagues/college-football/seasons/2023/types/2/groups/80?lang=en&region=us"
    tries = 0  # Adding a counter to prevent infinate loops
    does_it_match = parent_group_url == fbs_d1_url
    # print(does_it_match)
    # Could also use isConference to work out the conference status. It leaves out divisions and FBS 1
    isConference = string_to_bool(str(cjson["isConference"]).title())
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
        isConference = string_to_bool(str(cjson["isConference"]).title())
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
        print(
            "Your request to access conference API data has timed out; there was an error."
        )

    return cjson


def get_team_info(team_api_url: str) -> dict:
    """ ESPN API Rankings embed a team API URL to identify who is in what ranking.
     We need to parse that API's JSON to figure out what team it's referencing. """
    teamjson = api_json_response(team_api_url)
    # print(teamjson['nickname'])
    # # Looks like this (example for UGA, 2023 week 3):
    # http://sports.core.api.espn.com/v2/sports/football/leagues/college-football/seasons/2021/teams/61?lang=en&region=us

    # Get the conference data from its API endpoint
    conference_URL = teamjson["groups"][reference_key]
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
        team_api_url = team["team"][reference_key]
        # Add the team info to the dictionary storing all this data.
        ranking = team[current]
        # Using the embedded team API, get all the info you need on that team.
        team_info_dict = get_team_info(team_api_url)

        # Parse that data to get what you need like this below
        # # Do this again later to work with the dict data you got.
        team_name = team_info_dict["nickname"]
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
        team_api_url = team["team"][reference_key]
        # Add the team info to the dictionary storing all this data.
        points = float(team["points"])
        # Using the embedded team API, get all the info you need on that team.
        team_info_dict = get_team_info(team_api_url)

        # Parse that data to get what you need like this below
        # # Do this again later to work with the dict data you got.
        team_name = team_info_dict["nickname"]
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
    next_ranking = ranked_teams + 0
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
    # print(broken_ties_dict)

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
    top_tfive_json = rjson["ranks"]
    top_twenty_five_teams = get_top_tfive(top_tfive_json)
    # Figure out how many teams are ranked, including ties.
    n_ranked_teams = sum(
        [
            len(top_twenty_five_teams[t])
            for t in list(range(1, 26))
            if t in top_twenty_five_teams
        ]
    )
    # n_ranked_teams = len(top_twenty_five_teams) + (len(top_twenty_five_teams[25])-1)
    print("- - - - - - - -")
    # Get Others Receiving Votes as a continuation of the rankings, 26 to X where X is max n(Teams receiving votes).
    others = "others"
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
            team_name = team_dict["nickname"]
            print(f"{str(rank)} points: {team_name} ({conferenceShortName})")
            if conferenceShortName not in conference_pts_dict:
                conference_pts_dict[conferenceShortName] = [(team_name, rank)]
            else:
                conference_pts_dict[conferenceShortName].append((team_name, rank))
    print(conference_pts_dict)

    # Find the max number of teams any conference had.
    max_n_ranked_teams = max([len(conference_pts_dict[c]) for c in conference_pts_dict])
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


def calc_conference_scores(
    conferences_init_df: pd.DataFrame, four_team_race: bool = False
) -> dict:
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
                scores_only_df = cutoff_teams_df.apply(
                    lambda x: x[1]
                    if (
                        (not x[1] in [np.nan, None, ""])
                        and (type(x[1]) in [float, int])
                    )
                    else np.nan
                )
                scoring_dict[cnfcol] = scores_only_df.sum()
        else:
            scoring_dict[cnfcol] = did_not_score
    print(scoring_dict)

    return scoring_dict


def team_tiebreaker(
    conference_points: pd.DataFrame,
    onlyScoresDF: pd.DataFrame,
    xcsc: str,
    scoring_teams: int = 5,
):
    # Find the tied conferences
    tied_scores = (
        onlyScoresDF[xcsc].loc[onlyScoresDF[xcsc].duplicated(keep=False)].unique()
    )

    def create_breaking_dict(max_tied_teams):
        movements = {}
        num_teams = max_tied_teams
        for posit in range(1, num_teams + 1):
            movement = posit - (num_teams + 1) / 2
            movements[posit] = movement
        return movements
        # # Example of the types of dicts able to be returned
        # breaking_dict = {2: {1:-.5, 2:+.5},
        #                  3: {1:-1,2:0,3:+1},
        #                  4:{1:-1.5,2:-.5,3:+.5,4:+1.5},
        #                  5: {1: -2, 2: -1, 3: 0, 4: +1,5: +2}}

    # Iterate over each tied conference
    for tscore in tied_scores:
        # Get the rows corresponding to the tied conference and reset the index
        tied_conferences = onlyScoresDF[onlyScoresDF[xcsc] == tscore].reset_index(
            drop=True
        )

        # Find the teams' scores in the conference_points dataframe
        # # Subset the tied conferences
        tied_conf_points = conference_points[tied_conferences["conference"].to_list()]
        conference_df_columns = tied_conf_points.columns.to_list()
        scores = []
        for conf in conference_df_columns:
            # Access the score for the first non-scoring team from each tied conference.
            try:
                team_score = tied_conf_points[conf].iloc[scoring_teams][1]
            except (KeyError, TypeError):
                team_score = np.nan
            scores.append((conf, team_score))

        # Sort teams by their 6th runner's score
        # scores.sort(key=lambda x: x[1])
        # Separate scores with NaN values and sort the rest
        sorted_scores = sorted(
            [s for s in scores if not pd.isna(s[1])], key=lambda x: x[1]
        )
        # Handle NaN values
        nan_scores = [
            (conf, team_score) for conf, team_score in scores if pd.isna(team_score)
        ]
        # Combine sorted scores and NaN scores
        sorted_scores.extend(nan_scores)

        # # Update the xc_score in the onlyScoresDF dataframe
        # onlyScoresDF.loc[tied_conferences.index, xcsc] = sum(score for _, score in scores[:5]) + scores[5][1]

        # Assign tiebreaker positions to the conferences
        tiebreaker_posit = 1
        previous_score = np.nan
        for conf, team_score in sorted_scores:
            if pd.isna(team_score):
                # If the score is NaN, assign the tiebreaker position as 1
                onlyScoresDF.loc[
                    onlyScoresDF["conference"] == conf, tiebreak_posit_col
                ] = tiebreaker_posit
            elif team_score != previous_score:
                # If the score is different from the previous one, update the tiebreaker position
                onlyScoresDF.loc[
                    onlyScoresDF["conference"] == conf, tiebreak_posit_col
                ] = tiebreaker_posit
                previous_score = team_score
                # Only advance if the tiebraker position if there is a non-null scoring.
                tiebreaker_posit += 1

        # # Formula for determining the multiple of the place based on n(teams) tied:
        # # # y= 1/2x+0.5
        # y = ((1/2)*len(sorted_scores)) + 0.5

        # Update the 'place' column based on the 'tiebreaker_posit' column
        tb_place_dict = create_breaking_dict(len(sorted_scores))
        # Conditionally execute the code only for records in conference_df_columns
        # by creating a boolean mask where True values indicate records where conference is in `conference_df_columns`.
        # # Helps manage multiple ties at different scores in the same week (ex: tie at #2 and #4
        mask = onlyScoresDF["conference"].isin(conference_df_columns)
        # onlyScoresDF['place'] = onlyScoresDF['place'] + onlyScoresDF[tiebreak_posit_col].map(tb_place_dict).fillna(0)
        onlyScoresDF.loc[mask, "place"] += (
            onlyScoresDF[mask][tiebreak_posit_col].map(tb_place_dict).fillna(0)
        )

        # # Convert 'place' column to integer type
        # Aborted; done downstream.
        # onlyScoresDF['place'] = onlyScoresDF['place'].astype(int)

    return onlyScoresDF


def conference_scoring_order(
    scoring_dict: dict,
    conference_teams_scoring_df: pd.DataFrame,
    scoring_teams: int = 5,
) -> pd.DataFrame:
    """ Once you have generated conference XC scores with calc_conference_scores(), we need to see who won!
    Do that here. """
    # Subset those conferences that are scoring.
    only_scoring_conferences = {}
    for sc in scoring_dict:
        if scoring_dict[sc] != did_not_score:
            only_scoring_conferences[sc] = scoring_dict[sc]
    print(only_scoring_conferences)

    # Get conferences scores.
    # Move that data back to a pandas DF for easy working.
    # # Note: conference name is in the index.
    onlyScoresDF = pd.DataFrame(
        only_scoring_conferences.values(), index=only_scoring_conferences.keys()
    )
    # Name the score column
    xcsc = "xc_score"
    onlyScoresDF.columns = [xcsc]
    # Get xcsc to integer format if possible, ie if all scores are floats with 0 in tenths space.
    # # Step 1: Check if all values in xcsc can be converted to integers without losing information
    can_convert_to_int = np.all(onlyScoresDF[xcsc] == onlyScoresDF[xcsc].astype(int))
    if can_convert_to_int:
        # # Step 2: Convert to integer
        onlyScoresDF[xcsc] = onlyScoresDF[xcsc].astype(int)
    # Move conference name index to its own column, and eventually make that the first column.
    onlyScoresDF["conference"] = onlyScoresDF.index
    onlyScoresDF.reset_index(drop=True, inplace=True)
    # Sort by scores in decending order. Lowest score wins!
    onlyScoresDF = onlyScoresDF.sort_values(xcsc)

    # Apply the place to each scoring conference.
    place = "place"
    onlyScoresDF[place] = onlyScoresDF[xcsc].rank()
    # Apply the 5th/6th runner tiebreaker upstream and have it apply here.
    there_are_ties = onlyScoresDF[xcsc].duplicated(keep=False).any()
    onlyScoresDF[tiebreak_posit_col] = None
    if there_are_ties:
        # Break those ties!
        onlyScoresDF = team_tiebreaker(
            conference_points=conference_teams_scoring_df,
            onlyScoresDF=onlyScoresDF,
            xcsc=xcsc,
            scoring_teams=scoring_teams,
        )

    # Get `place` to integer format if possible, ie if all places are floats with 0 in tenths space.
    # # Step 1: Check if all values in xcsc can be converted to integers without losing information
    can_convert_to_int = np.all(onlyScoresDF[place] == onlyScoresDF[place].astype(int))
    if can_convert_to_int:
        # # Step 2: Convert to integer
        onlyScoresDF[place] = onlyScoresDF[place].astype(int)

    # Prepare the output
    # Order the columns
    onlyScoresDF = onlyScoresDF[["conference", "place", xcsc, tiebreak_posit_col]]
    # Order the rows
    onlyScoresDF = onlyScoresDF.sort_values(
        by=[xcsc, tiebreak_posit_col], ascending=[True, True]
    )
    onlyScoresDF.reset_index(inplace=True, drop=True)

    print(onlyScoresDF)

    return onlyScoresDF


def full_ap_xc_run(year: int = None, week=None, four_team_score: bool = False):
    """
    From the year and week you want, return a full report of conferences' scores.

    Returns:
    - dict: A dictionary containing the following keys:
        - "url": String of the ESPN API URL.
        - "json_teams": JSON dictionary detailing each team in the rankings for [week].
        - "conference_teams_df": pd.DataFrame of each conference's teams receiving votes for [week] in (team, ranking) format.
        - "conference_scores_dict": Dictionary of {conference: cross-country 4 or 5 team total}.
        - "conference_scores_df": pd.DataFrame of the conference XC race results with ties broken.
        - "scoring_teams": integer of the number of teams required to generate a score for a conference.
    """
    four_team_score = string_to_bool(four_team_score)
    the_url = espn_api_url_generator(year, week)
    # print(the_url)
    main_custom_format_rankings = poll_grabber(the_url)
    print()
    conference_points = teams_points_by_conference(main_custom_format_rankings)
    calc_xc_scores = calc_conference_scores(
        conference_points, four_team_race=four_team_score
    )
    steams = 4 if four_team_score else 5
    xc_scoring = conference_scoring_order(
        calc_xc_scores, conference_points, scoring_teams=steams
    )

    # Package all the data together in a big dict that includes each item defined here;
    # # each has a possible downstream use.
    # # Loosely structured custom JSON API response for a full data pull.
    results_dict = {
        "url": the_url,
        "json_teams": main_custom_format_rankings,
        "conference_teams_df": conference_points,
        "conference_scores_dict": calc_xc_scores,
        "conference_scores_df": xc_scoring,
        "scoring_teams": steams,
    }
    return results_dict


def pretty_print(the_results_dict: dict):
    """ Prints the results of a weekly run in a downstream-usable manner. """
    team_conf_df = the_results_dict["conference_teams_df"]
    confscoresdict = the_results_dict["conference_scores_dict"]
    core_four = ['SEC', 'Big Ten', 'ACC', 'Big 12']
    include_confs = core_four + [c for c, s in confscoresdict.items() if c not in core_four and s != "DNS"]
    retain_df = team_conf_df[include_confs]

    # Function to format tuples as "Team: Score" and replace NaNs with empty strings
    def format_tuple(cell):
        if pd.isna(cell):  # Check if it's NaN
            return ""
        if isinstance(cell, tuple):  # Check if it's a tuple
            team, score = cell
            return f"{team}: {score}"
        return cell

    # Apply the formatting to the entire DataFrame
    formatted_df = retain_df.applymap(format_tuple)

    # Create the new first row with the conference names and scores
    first_row = {
        col: f"({the_results_dict['conference_scores_df'].loc[the_results_dict['conference_scores_df']['conference'] == col, 'place'].values[0] if len(the_results_dict['conference_scores_df'].loc[the_results_dict['conference_scores_df']['conference'] == col, 'place'].values) > 0 else 'N/A'}) {col}: {confscoresdict.get(col, 'N/A')}" for col in formatted_df.columns
    }

    # Create the second row with six dashes
    second_row = {col: "------" for col in formatted_df.columns}
    # Convert both rows into DataFrames
    first_row_df = pd.DataFrame([first_row])
    second_row_df = pd.DataFrame([second_row])
    # Concatenate the new rows with the existing DataFrame
    formatted_df = pd.concat([first_row_df, second_row_df, formatted_df], ignore_index=True)

    # Insert the line of dashes between the 5th and 6th records (after index 6, which is index 7 after the headers)
    line_of_dashes = {col: "------" for col in formatted_df.columns}
    # Insert this row in the correct position (index 8, after 5 data rows and 2 header rows)
    n_scoring_teams = the_results_dict["scoring_teams"]
    eyeloc = 6 if n_scoring_teams == 4 else 7
    formatted_df = pd.concat([formatted_df.iloc[:eyeloc], pd.DataFrame([line_of_dashes]), formatted_df.iloc[eyeloc:]],ignore_index=True)

    # Create a positional numbering column
    # Skip first two rows and the eyeloc row
    positions = [''] * 2 + [str(i) for i in range(1, n_scoring_teams+1)] + [''] + [str(i) for i in range(eyeloc - 1, len(formatted_df)-2)]
    # Add the positions as the first column
    formatted_df.insert(0, 'Position', positions)

    # Temporarily set the display options only for this print
    with pd.option_context('display.max_columns', None, 'display.max_colwidth', None):
        print(formatted_df.to_string(index=False, header=False))
    print("\n@ap_cfb_xc | @SECGeographer")


if __name__ == "__main__":
    # Example usage:
    # result = full_ap_xc_run(2021, 'final')
    # result = full_ap_xc_run(2021, 2)  # Team Tie
    # result = full_ap_xc_run(2023, 14)  # Good choice; has tie at #21.
    # result = full_ap_xc_run(2021, 2, four_team_score=True)  # Test 4 team run.
    # print(espn_api_url_generator(year=2016,week=3))
    # print(espn_api_url_generator(week=3))
    # print(espn_api_url_generator())
    #
    # Run the most recent week's race.
    result = full_ap_xc_run()

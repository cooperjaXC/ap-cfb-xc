import os, re
import numpy as np
import pandas as pd


def resort_columns(dataframe: pd.DataFrame):
    def sort_key(item):
        """ Function to sort tuples by the second item in the tuple """
        if isinstance(item, str):
            try:
                return float(item.split(',')[1].strip(") '"))
            except:
                return float('inf')
        return float('inf')
    # Sort the second row by the second items of the tuples in ascending order
    dataframe.iloc[1] = dataframe.iloc[1].sort_values(key=lambda col: col.map(sort_key))
    return dataframe


def clean_dataframe(df):
    """ Clean the DataFrame by stripping whitespace and replacing empty strings with NaN """
    df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)
    df.replace("", pd.NA, inplace=True)
    return df

def find_conference_column(df, conference):
    """ Returns the index of the column for the target conference. """
    for col in df.columns:
        if conference in str(col):
            return col
    return None

def realign_teams(df: pd.DataFrame, n_teams_score: int = 5):
    """ Function to realign teams """
    # Ensure that the dataframe doesn't have any superfluous `'` characters in it.
    def clean_quotes(s):
        """ Function to clean single quotes from a string """
        if isinstance(s, str):
            return s.replace("'", "")
        return s

    # Apply the clean_quotes function to all elements in the DataFrame
    df = df.applymap(clean_quotes)

    # Establish the existing conferences & their scores in a dictionary.
    def parse_tuple_string(s):
        """ Function to parse tuples from strings """
        match = re.match(r"\(([^,]+),\s*([^)]+)\)", s)
        if match:
            return (match.group(1).strip(), match.group(2).strip())
        return None

    # Create the dictionary
    existing_conference_dict = {}

    # Use the first row as keys
    keys = [parse_tuple_string(x) for x in df.iloc[0].dropna()]

    # Initialize empty lists for each key
    for key in keys:
        existing_conference_dict[key] = []

    # Iterate over the rest of the DataFrame to populate the dictionary
    for row in df.iloc[1:].itertuples(index=False):
        for i, value in enumerate(row):
            if pd.notna(value):
                parsed_value = parse_tuple_string(value)
                if parsed_value:
                    existing_conference_dict[keys[i]].append(parsed_value)

    # Print the result dictionary
    for key, values in existing_conference_dict.items():
        print(f"{key}: {values}")

    # Working dict for use downstream
    working_conf_dict = existing_conference_dict.copy()

    # Define the team movements
    team_movements = {
        'SEC': ['Oklahoma', 'Texas'],
        'Big Ten': ['Washington', 'Oregon', 'UCLA', 'Southern Cal', 'USC'],
        'Big 12': ['Arizona', 'Arizona St.', 'Utah', 'Colorado', 'BYU', 'Cincinnati', 'Houston', 'UCF'],
        'ACC': ['California', 'Stanford', 'SMU'],
        'American': ['Charlotte', 'Florida Atlantic', 'North Texas', 'Rice', 'UAB', 'UTSA']
    }

    # Create a map of old to new conferences
    new_conference_map = {}
    for new_conference, teams in team_movements.items():
        for team in teams:
            new_conference_map[team] = new_conference
    def find_team_conference(result_dict: dict, team_to_find: str) -> tuple:
        """Function to find the team and print its details"""
        for conference, teamsss in result_dict.items():
            for teammm in teamsss:
                if teammm[0] == team_to_find:
                    print(f"Team: {team_to_find}")
                    print(f"Previous Conference: {conference[0]}")
                    print(f"Score: {teammm[1]}")
                    return (teammm, conference)

    def move_team_to_new_conf(work_conf_d, team_to_move, move_to_conf):
        team_tuple = None
        old_conference_tuple = None

        # Find the team and its current conference
        for conference, teams in work_conf_d.items():
            for team in teams:
                if team[0] == team_to_move:
                    team_tuple = team
                    old_conference_tuple = conference
                    break
            if team_tuple:
                break

        # Remove the team from its old conference
        if old_conference_tuple and team_tuple:
            work_conf_d[old_conference_tuple].remove(team_tuple)
            print(f"Removed {team_to_move} from {old_conference_tuple}")

        # Find the new conference key
        new_conference_tuple = None
        for conference in work_conf_d.keys():
            if conference[0] == move_to_conf:
                new_conference_tuple = conference
                break

        # Add the team to the new conference
        if new_conference_tuple:
            work_conf_d[new_conference_tuple].append(team_tuple)
            print(f"Added {team_to_move} to {new_conference_tuple}")

        return work_conf_d

    problem_teams = ("Washington", "Texas")
    # Iterate over each cell and update the conference
    for move_to_conf, realigned_teams_list in team_movements.items():
        if realigned_teams_list and (isinstance(realigned_teams_list, list) or isinstance(realigned_teams_list, tuple)):
            # If the list exists:
            for team_being_realigned in realigned_teams_list:
                # Find the team in question in its existing spot in the standings with its original, old conference.
                # # Format: Team_tuple, conf_tuple
                exist_spot_tuple = find_team_conference(existing_conference_dict, team_being_realigned)
                # if isinstance(cell_value, str):
                # print(exist_spot_tuple)
                if exist_spot_tuple:
                    # The team being realigned received votes in the polls. Realign them in this model.
                    team_teamscore_tuple = exist_spot_tuple[0]
                    team_name = team_teamscore_tuple[0]  # Should duplicate team_being_realigned
                    old_conference_tuple = exist_spot_tuple[1]
                    old_conference_name = old_conference_tuple[0]
                    # print(team_name)
                    pyes = False
                    if team_name in problem_teams:
                        pyes = True
                        print(team_name)
                        print(move_to_conf)

                    # Now move the teams to their new conferences.
                    working_conf_dict = move_team_to_new_conf(work_conf_d=working_conf_dict,team_to_move=team_being_realigned, move_to_conf=move_to_conf)
                    print("- - - - - - - - - - - - - - - -")

    # Now re-sort the teams and  re-calculate team scores
    print(working_conf_dict,'\n')

    def sort_conference_tuples(working_conf_dict):
        """ Function to sort the tuples in each conference"""
        sorted_dict = {}
        for conference, teams in working_conf_dict.items():
            # Sort the list of teams by the second item in the tuple (score), then by the first item (team name) if scores are equal
            sorted_teams = sorted(teams, key=lambda x: (float(x[1]), x[0]) if x[1].replace('.', '', 1).isdigit() else (
            float('inf'), x[0]))
            sorted_dict[conference] = sorted_teams
        return sorted_dict

    # Sort the conference tuples
    sorted_conf_dict = sort_conference_tuples(working_conf_dict)
    # Remove conferences with no teams
    sorted_conf_dict = {conf: teams for conf, teams in sorted_conf_dict.items() if teams}

    # Re-Score the conferences
    def rescore_conferences(sort_conf_dict, X=5):
        """Function to score each conference based on the sum of the lowest X scores"""
        scored_dict = {}
        for conference, teams in sort_conf_dict.items():
            # Calculate the sum of the lowest X scores or set to 'DNS' if not enough teams
            if len(teams) >= X:
                lowest_scores_sum = sum(float(team[1]) for team in teams[:X])
                new_conference_tuple = (conference[0], str(lowest_scores_sum))
            else:
                new_conference_tuple = (conference[0], 'DNS')

            scored_dict[new_conference_tuple] = teams
        return scored_dict

    n_teams_score = int(n_teams_score)
    sorted_conf_dict = rescore_conferences(sorted_conf_dict, n_teams_score)

    # Print the sorted dictionary
    for key, values in sorted_conf_dict.items():
        print(f"{key}: {values}")

    return df


if __name__ == '__main__':
    # Load the CSV files
    path_to_your_file = os.path.abspath(os.path.curdir)
    df_4team = pd.read_csv(os.path.join(path_to_your_file, 'data/2023/4_team/2023_week_final.csv'), header=None)
    df_5team = pd.read_csv(os.path.join(path_to_your_file, 'data/2023/5_team/2023_week_final.csv'), header=None)

    # Realign teams in both DataFrames
    df_4team_realigned = realign_teams(df_4team)
    df_5team_realigned = realign_teams(df_5team)

    # Save the updated DataFrames to CSV
    df_4team_realigned.to_csv(os.path.join(path_to_your_file,'data/2023/4_team/2023_week_final_4team_realigned.csv'), index=False)
    df_5team_realigned.to_csv(os.path.join(path_to_your_file,'data/2023/5_team/2023_week_final_5team_realigned.csv'), index=False)

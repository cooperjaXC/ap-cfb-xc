import os
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

def realign_teams(df):
    """ Function to realign teams """
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

    problem_teams = ("Washington", "Texas")
    # Iterate over each cell and update the conference
    for col in range(len(df.columns)):
        for row in range(1, len(df)):
        # for col in range(len(df.columns)):
            cell_value = df.iat[row, col]
            if isinstance(cell_value, str):
                team_name = cell_value.strip("()").split(",")[0].strip("'")
                print(team_name)
                pyes = False
                if team_name in problem_teams:
                    pyes = True
                    print(team_name)
                if team_name in new_conference_map:
                    move_to_conf = new_conference_map[team_name]
                    if pyes:
                        print(move_to_conf)
                    target_col = find_conference_column(df, move_to_conf)
                    if target_col is None:
                        print(f"Conference {move_to_conf} not found for team {team_name}.")
                        continue
                    targ_column_position = df.columns.get_loc(target_col)

                    # Find the first unoccupied row in the target column

                    # Find the first NaN index in column 'A'
                    first_nan_index = df[target_col].isna().idxmax() if df[target_col].isna().any() else len(df)
                    # If there is no NaN value in the column, extend the DataFrame
                    if first_nan_index == len(df):
                        df = df.append({col: np.nan for col in df.columns}, ignore_index=True)

                    # target_row = None
                    # for roww in range(len(df)):
                    #     if pd.isna(df.iat[roww, targ_column_position]) or df.iat[roww, targ_column_position] == '':
                    #         target_row = roww
                    #         break

                    # Move the data
                    # if target_row is not None:
                    df.iat[first_nan_index, targ_column_position] = cell_value
                    df.iat[row, col] = ""
                    # else:
                    #     print(f"{team_name} is unable to be moved to {move_to_conf} because of a target-row definition issue.")

    return df


if __name__ == '__main__':
    # Load the CSV files
    path_to_your_file = os.path.abspath(os.path.curdir)
    df_4team = pd.read_csv(os.path.join(path_to_your_file, 'data/2023/4_team/2023_week_final.csv'))
    df_5team = pd.read_csv(os.path.join(path_to_your_file, 'data/2023/5_team/2023_week_final.csv'))

    # Realign teams in both DataFrames
    df_4team_realigned = realign_teams(df_4team)
    df_5team_realigned = realign_teams(df_5team)

    # Save the updated DataFrames to CSV
    df_4team_realigned.to_csv(os.path.join(path_to_your_file,'data/2023/4_team/2023_week_final_4team_realigned.csv'), index=False)
    df_5team_realigned.to_csv(os.path.join(path_to_your_file,'data/2023/5_team/2023_week_final_5team_realigned.csv'), index=False)

import os
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


def realign_teams(df) -> pd.DataFrame:
    """Function to realign teams"""
    # Define the team movements
    team_movements = {
        'SEC': ['Oklahoma', 'Texas'],
        'Big Ten': ['Washington', 'Oregon', 'UCLA', 'Southern Cal', 'USC'],
        'Big 12': ['Arizona', 'Arizona St.', 'Utah', 'Colorado', 'BYU', 'Cincinnati', 'Houston', 'UCF'],
        'ACC': ['California', 'Stanford', 'SMU'],
        'American': ['Charlotte', 'Florida Atlantic', 'North Texas', 'Rice', 'UAB', 'UTSA']
    }

    # Function to find the column containing the specified conference
    def find_conference_column(d_f, conference) -> int:
        """ Returns the index of the column for the target conference. """
        # print(d_f)
        # print(conference)
        for col in d_f.columns:
            # print(str(col))
            # cell_value = d_f.at[0, col]
            # print(cell_value)
            # if isinstance(col, str) and conference in col:
            if conference in str(col):
                # print("!!!!!!!!!!!!!!!!!!!!")
                return col
        # print("------------")
        return None

    # Create a map of old to new conferences
    new_conference_map = {}
    for new_conference, teams in team_movements.items():
        for team in teams:
            new_conference_map[team] = new_conference

    # Iterate over each cell and update the conference
    for row in range(1, len(df)):
        for col in range(len(df.columns)):
            cell_value = df.iat[row, col]
            if isinstance(cell_value, str):
                team_name = cell_value.strip("()").split(",")[0].strip("'")
                # score = cell_value.strip("()").split(",")[1].strip("'")
                if team_name in new_conference_map:
                    # df.iat[row, col] = f"('{team_name}', '{score})"
                    move_to_conf = new_conference_map[team_name]
                    print(move_to_conf,'\n"- - - - - - - - - -')
                    target_col = find_conference_column(df, move_to_conf)
                    # Get the position of the column
                    targ_column_position = df.columns.get_loc(target_col)
                    # Find the first unoccupied row in the target column
                    target_row = None
                    for roww in range(len(df)):
                        # print(roww, target_col, targ_column_position)
                        if pd.isna(df.iat[roww, targ_column_position]) or df.iat[roww, targ_column_position] == '':
                            target_row = roww
                            break
                    # Move the data
                    if target_row is not None:
                        # Set the target cell value in the new conference
                        df.iat[target_row, targ_column_position] = cell_value

                        # Clear the source cell value in the old conference.
                        df.iat[row, col] = ""
                    else:
                        print(f"{team_name} is unable to be moved to {move_to_conf} because of a target-row definition issue.")

    # Re-sort each column


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

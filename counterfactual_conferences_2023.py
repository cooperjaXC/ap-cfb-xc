import os
import pandas as pd

# Load the CSV files
path_to_your_file = os.path.abspath(os.path.curdir)
df_4team = pd.read_csv(os.path.join(path_to_your_file,'data/2023/4_team/2023_week_final.csv'))
df_5team = pd.read_csv(os.path.join(path_to_your_file,'data/2023/5_team/2023_week_final.csv'))

# Define the team movements
team_movements = {
    'SEC': ['Oklahoma', 'Texas'],
    'Big 10': ['Washington', 'Oregon', 'UCLA', 'USC'],
    'Big 12': ['Arizona', 'Arizona St.', 'Utah', 'Colorado', 'BYU', 'Cincinnati', 'Houston', 'UCF'],
    'ACC': ['California', 'Stanford', 'SMU'],
    'AAC': ['Charlotte', 'Florida Atlantic', 'North Texas', 'Rice', 'UAB', 'UTSA']
}

def realign_teams(df, team_movements):
    """Function to realign teams"""
    # Create a map of old to new conferences
    new_conference_map = {}
    for new_conference, teams in team_movements.items():
        for team in teams:
            new_conference_map[team] = new_conference

    # Iterate over each cell and update the conference
    for row in range(1, len(df)):
        for col in range(len(df.columns)):
            cell = df.iat[row, col]
            if isinstance(cell, str):
                team_name = cell.strip("()").split(",")[0].strip("'")
                if team_name in new_conference_map:
                    df.iat[row, col] = f"('{team_name}', '{new_conference_map[team_name]}')"

    return df

# Realign teams in both DataFrames
df_4team_realigned = realign_teams(df_4team, team_movements)
df_5team_realigned = realign_teams(df_5team, team_movements)

# Save the updated DataFrames to CSV
df_4team_realigned.to_csv(os.path.join(path_to_your_file,'data/2023/4_team/2023_week_final_4team_realigned.csv'), index=False)
df_5team_realigned.to_csv(os.path.join(path_to_your_file,'data/2023/5_team/2023_week_final_5team_realigned.csv'), index=False)

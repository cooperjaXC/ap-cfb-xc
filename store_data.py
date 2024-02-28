import os
import pandas as pd

import espn_api as epi


def prep_weekly_results(weekly_result_dict: dict) -> pd.DataFrame:
    """Rely on the 'espn_api.full_ap_xc_run()' function as input.
    This will have 'conference_teams_df', 'conference_scores_dict' as keys to the dict. """
    base_df = weekly_result_dict['conference_teams_df']
    conf_scores_dict = weekly_result_dict['conference_scores_dict']

    # Taking the column name and inserting it as the column name the tuple included
    base_df.columns = [(col, conf_scores_dict[col]) for col in base_df.columns]

    return base_df


def write_weekly_results(year, week, prepped_result_df: pd.DataFrame, four_team_race: bool = False):
    # Define base directory and subdirectories
    base_dir = os.path.join(os.getcwd(), "data", str(year))
    team_dir = "4_team" if four_team_race else "5_team"
    year_dir = os.path.join(base_dir, team_dir)

    # Create directories if they don't exist
    os.makedirs(year_dir, exist_ok=True)

    # Write weekly results to CSV
    if prepped_result_df is not None:
        # Write weekly results to CSV
        week_file = os.path.join(year_dir, f"{year}_week_{week}.csv")
        prepped_result_df.to_csv(week_file, index=False)

    # Update summary statistics CSV
    # TODO this needs to change to reflect the actual sumstats structure; incomplete as of now
    summary_file = os.path.join(base_dir, f"{year}_summary_statistics.csv")
    if os.path.exists(summary_file):
        # Load existing summary statistics
        summary_stats = pd.read_csv(summary_file)
        # Update summary statistics
        # For demonstration, let's assume we are just appending the week number
        summary_stats = summary_stats.append({"Week": week}, ignore_index=True)
    else:
        # Create new summary statistics DataFrame
        summary_stats = pd.DataFrame({"Week": [week]})

    # Write updated summary statistics to CSV
    summary_stats.to_csv(summary_file, index=False)


def store_weekly_results(year: int, week, four_team_score: bool = False):
    """Full process to store weekly results. """
    four_team_score = epi.string_to_bool(four_team_score)
    results_dict = epi.full_ap_xc_run(year, week, four_team_score=four_team_score)
    base_rez_df = prep_weekly_results(results_dict)
    written_results = write_weekly_results(year=year,week=week,four_team_race=four_team_score, prepped_result_df=base_rez_df)
    return written_results


# Example usage:
# Create a DataFrame with example data
prepped_result = pd.DataFrame({
    "Team": ["Team A", "Team B", "Team C"],
    "Score": [10, 15, 20]
})

# Call the function to write weekly results
write_weekly_results(year=2023, week=1, four_team_race=True, prepped_result_df=prepped_result)

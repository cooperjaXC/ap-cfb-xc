import os, warnings
import numpy as np
import pandas as pd

import espn_api as epi

quad = "4_team"
pent = "5_team"


def prep_weekly_results(weekly_result_dict: dict) -> pd.DataFrame:
    """Rely on the 'espn_api.full_ap_xc_run()' function as input.
    This will have 'conference_teams_df', 'conference_scores_dict' as keys to the dict. """
    base_df = weekly_result_dict['conference_teams_df']
    conf_scores_dict = weekly_result_dict['conference_scores_dict']

    # Taking the column name and inserting it as the column name the tuple included
    base_df.columns = [(col, conf_scores_dict[col]) for col in base_df.columns]

    return base_df


def summarize_data(week, conference_score_tuple: list, n_teams_str: str = pent, existing_summary_df: pd.DataFrame = None):
    # Define the potential weeks
    potential_weeks = ["Preseason", "Week 2", "Week 3", "Week 4", "Week 5", "Week 6",
                       "Week 7", "Week 8", "Week 9", "Week 10", "Week 11", "Week 12",
                       "Week 13", "Week 14", "Week 15", "Week 16", "Final"]

    # Check if the week is in the potential weeks
    week_str = epi.date_processing(2014,week)[1]
    if week_str=='1':
        week_str = "Preseason"
    elif str(week) =='1':
        week_str = "Preseason"
    week_str = week_str.title()
    if week_str not in ["Preseason", "Final"]:
        week_str = f"Week {week_str}"
    if week_str not in potential_weeks:
        print("Week not found in potential weeks. Cannot insert data.")
        return

    # Define the summary dataset
    idx_header = f'AP_XC_{n_teams_str.title()}_Race'
    if existing_summary_df is None:
        summary_data = {idx_header: potential_weeks}
        # Convert the summary data to a DataFrame
        summary_df = pd.DataFrame(summary_data)
    else:
        summary_df = existing_summary_df

    # Extract conference names from the headers
    conf_names = [header[0] for header in conference_score_tuple]
    # Initialize conference score lists with None only if the conference doesn't exist yet
    for conf in conf_names:
        if conf not in summary_df.columns:
            summary_df[conf] = np.nan

    # Insert the headers data into the corresponding column for the given week
    for header in conference_score_tuple:
        conf_name = header[0]
        conf_score = header[1]
        if conf_score == "'DNS'" or conf_score == "DNS":
            conf_score = None
        summary_df.loc[summary_df[idx_header] == week_str, conf_name] = conf_score

    # # Reorder the columns based on potential weeks
    # summary_df = summary_df[potential_weeks + [idx_header, 'SEC', 'ACC', 'B1G', 'Big 12', 'Pac-12']]

    return summary_df


def write_weekly_results(year, week, prepped_result_df: pd.DataFrame, four_team_race: bool = False):
    # Define base directory and subdirectories
    base_dir = os.path.join(os.getcwd(), "data", str(year))
    team_dir = quad if four_team_race else pent
    year_dir = os.path.join(base_dir, team_dir)

    # Create directories if they don't exist
    os.makedirs(year_dir, exist_ok=True)

    # Write weekly results to CSV
    if prepped_result_df is not None:
        # Write weekly results to CSV
        week_file = os.path.join(year_dir, f"{year}_week_{week}.csv")
        prepped_result_df.to_csv(week_file, index=False)

    # Update summary statistics CSV
    summary_file = os.path.join(base_dir, team_dir, f"{year}_{team_dir}_summary_statistics.csv")
    if os.path.exists(summary_file):
        # Load existing summary statistics
        e_summary_stats = pd.read_csv(summary_file)
    else:
        # No existing SumStats; create it downstream.
        e_summary_stats = None
    # Generate the updated summary data
    the_summary_data = summarize_data(week,conference_score_tuple=prepped_result_df.columns.to_list(),n_teams_str=team_dir, existing_summary_df=e_summary_stats)

    # Write updated summary statistics to CSV
    try:
        the_summary_data.to_csv(summary_file, index=False)
        print("Summary data has been successfully written to", summary_file)
    except Exception as e:
        warnings.warn("Unable to write summary data to {}. Error: {}".format(summary_file, str(e)))

    return the_summary_data


def store_weekly_results(year: int, week, four_team_score: bool = False):
    """Full process to store weekly results. """
    four_team_score = epi.string_to_bool(four_team_score)
    results_dict = epi.full_ap_xc_run(year, week, four_team_score=four_team_score)
    base_rez_df = prep_weekly_results(results_dict)
    written_results = write_weekly_results(year=year,week=week,four_team_race=four_team_score, prepped_result_df=base_rez_df)
    return written_results


if __name__ == '__main__':
    # Example usage:
    # stored = store_weekly_results(2021, 1, four_team_score = False)
    stored = store_weekly_results(2021, 2, four_team_score = False)

    print(stored)


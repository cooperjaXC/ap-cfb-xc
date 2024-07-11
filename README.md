# AP College Football Cross-Country Scoring

This repository implements a novel method for evaluating the best college football conferences
using a cross-country scoring mechanism.
This method ranks conferences based on the positions of their top teams in the final season polls,
providing an objective comparison of conference strengths.

## Background

Inspired by the team scoring in cross-country racing,
this method sums the "finishing positions," or the ranking, of the top five teams within each conference.
The conference with the lowest total score is deemed the best,
emphasizing overall depth and strength rather than just top-tier performance
(i.e., whichever conference produced the most recent national champion).

This approach was first introduced in 2015 and updated in 2019. You can read more about the method and its evolution in the following blog posts:
- [2015: The Race for Supremacy](https://cooperconferencecolumn.wordpress.com/2015/08/25/the-race-for-supremacy-college-football-conferences-evaluated-by-a-cross-country-scoring-system/)
- [2019: AP XC - An Update](https://cooperconferencecolumn.wordpress.com/2019/08/19/ap-xc-an-update/)

## Repository Structure

- `.gitignore`: Specifies files and directories to be ignored by Git.
- `data/`: Directory containing input data files.
- `espn_api.py`: Script for fetching data from the ESPN API.
- `LICENSE`: License file for the repository.
- `requirements.in`: File listing the Python dependencies for the project.
- `store_data.py`: Script for storing data fetched from external sources.
- `Team_Conf_Organization.py`: Script for organizing teams and conferences based on the cross-country scoring method.
- `ToDo.txt`: Text file containing a list of tasks and future improvements for the project.

## Installation

To run the scripts in this repository, you need to install the required Python packages. You can install them using `pip`:

```bash
pip install -r requirements.in
```

## Usage

1. **Fetch Data**:
   - Use `espn_api.py` to fetch the latest college football data from ESPN.

2. **Store Data**:
   - Use `store_data.py` to store the fetched data into a suitable format for analysis.

3. **Organize Teams and Conferences**:
   - Use `Team_Conf_Organization.py` to organize teams into their respective conferences and apply the cross-country scoring mechanism to evaluate conference strengths.

## Contributing

Contributions are welcome!
Please fork the repository and create a pull request with your changes.

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

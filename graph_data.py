import os
import pandas as pd
import matplotlib.pyplot as plt


def generate_graph(summary_stats_df) -> plt.plot:
    """ """
    # Set Week column as index
    summary_stats_df.set_index('Week', inplace=True)

    # Drop rows and columns with all NaN values
    df_cleaned = summary_stats_df.dropna(axis=0, how='all').dropna(axis=1, how='all')

    # Plot the data
    plt.figure(figsize=(10, 6))
    for column in df_cleaned.columns:
        plt.plot(df_cleaned.index, df_cleaned[column], marker='o', label=column)

    # Customize the plot
    plt.title('Weekly Results')
    plt.xlabel('Week')
    plt.ylabel('Scores')
    plt.grid(True, linestyle='--', alpha=0.5)
    plt.gca().set_facecolor('black')

    # Customize the color of lines and markers
    colors = ['cyan', 'yellow', 'lime', 'magenta']
    for i, line in enumerate(plt.gca().get_lines()):
        line.set_color(colors[i])
        line.set_markersize(8)
        line.set_markerfacecolor('white')
    # Invert y-axis
    plt.gca().invert_yaxis()
    # Invert x-axis tick labels
    plt.gca().invert_xaxis()

    # Make a legend
    plt.legend()
    # plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    # plt.legend(bbox_to_anchor=(1.05, 1), loc='middle right')

    # Add a border around the graph
    plt.gca().spines['top'].set_visible(True)
    plt.gca().spines['right'].set_visible(True)
    plt.gca().spines['bottom'].set_visible(True)
    plt.gca().spines['left'].set_visible(True)

    # Show the plot
    plt.show()

    return plt


def get_graph_from_file(csv_path: str) -> plt.plot:
    """Shortcut wrapper to get the summary statistics graph from a file"""
    df = pd.read_csv(csv_path)
    graph = generate_graph(df)
    return graph


def save_graph(plot: plt.plot, out_path: str):
    return out_path


def graph_all_data():
    """ Graph all the data in the repo."""
    tss = "_team_summary_statistics.csv"
    data_dir = os.path.join(os.path.abspath(os.curdir), 'data')

    for it in os.listdir(data_dir):
        fp = os.path.join(data_dir, it)
        print(it, os.path.isdir(fp))
        for sd in os.listdir(fp):
            fps = os.path.join(fp, sd)
            for item in os.listdir(fps):
                if item.endswith(tss):
                    new_name = item.replace(tss, "_team_graph.csv")
                    new_path = os.path.join(fps, new_name)
                    # TODO: Insert execution + image saving here.


if __name__ == '__main__':
    # Example DataFrame
    data = {
        'Week': ['Preseason', 'Week 2', 'Week 3', 'Week 4', 'Week 5', 'Week 6', 'Week 7', 'Week 8', 'Week 9',
                 'Week 10'],
        'SEC': [49, 37, 37, 32, 32, 33, 35, 36, 43, 35.5],
        'ACC': [72, 78, 76, 87, 84, 84, 77, 77, 76.5, 85],
        'B1G': [71, 67, 74, 80, None, 83, 74, 66, 66, 63.5],
        'Big 12': [95.5, 89, 81, 88, 94, 90, 79.5, 86, None, 96]
    }

    df = pd.DataFrame(data)
    generate_graph(df)
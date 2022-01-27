from numpy import *
import math


def plot_dataset(dataset, column_name_pairs, x_range=None, y_range=None, figure_size_x=20, figure_size_y=4, legend_loc="upper left", add_line = []):
    import matplotlib.pyplot as plt
    color_schemes = ["red", "blue", "green", "black", "orange", "grey", "cyan", "magenta", "brown", "olive", "pink"]

    plt.figure(figsize=(figure_size_x, figure_size_y))
    for i in range(len(column_name_pairs)):
        plt.plot(dataset[column_name_pairs[i][0]],
                 dataset[column_name_pairs[i][1]],
                 color=color_schemes[i],
                 label=column_name_pairs[i][1])
        plt.legend(loc=legend_loc)
    if len(add_line) > 0:
        for line in add_line:
            plt.axhline(y=line, color='green', linestyle='--')
    if x_range is not None and y_range is not None:
        plt.axis([x_range[0], x_range[1], y_range[0], y_range[1]])
    ax = plt.gca()
    if x_range is not None:
        ax.set_xlim(x_range)
    if y_range is not None:
        ax.set_ylim(y_range)
    plt.axis('off')
    plt.show()
    return

from numpy import *
import math


def plot_dataset(dataset, column_name_pairs, figure_size_x=20, figure_size_y=4, legend_loc="upper left"):
    import matplotlib.pyplot as plt
    color_schemes = ["red", "blue", "green", "black", "orange", "grey", "cyan", "magenta", "brown", "olive", "pink"]

    plt.figure(figsize=(figure_size_x, figure_size_y))
    for i in range(len(column_name_pairs)):
        plt.plot(dataset[column_name_pairs[i][0]],
                 dataset[column_name_pairs[i][1]],
                 color=color_schemes[i],
                 label=column_name_pairs[i][1])
        plt.legend(loc=legend_loc)
    plt.show()
    return


# -*- coding: utf-8 -*-
"""EMS graph repository

This module contains functions to create specific types of graphs ready to use.
The functions accept processed data in a particular format and deliver graphs
than can be saved to file or integrated in others workflows.

Attributes:
    Module level variables storing the default values that control several
    figure options.

    Module default values to display figures:
        FigureParameter.SHOW
        FigureParameter.RATIO
        FigureParameter.WIDTH
        FigureParameter.SPACE_RATIO

    Module default values to save figures:
        FigureParameter.SAVE
        FigureParameter.NAME
        FigureParameter.PATH
        FigureParameter.FORMAT
        FigureParameter.TIMESTAMP
    
    Time constants:
        START_HOUR (int): First hour of the graph.
        END_HOUR (int): Last hour of the graph.
        DAY_HOURS (int): (hours) Span between START_HOUR and END_HOUR.

Common figure function parameters:
    The name of these parameters follow the form fig_<name>. These parameters
    are found in all figure functions and its default values are retrieved from
    the module attributes.

    Parameters to control display options:
        fig_show (bool): Display file option.
        fig_ratio (float): Width / height ratio.
        fig_width (float): (inches) Width of the image.
        fig_space_ratio (float): Proportional white space around data in the 
                                 graph.
        
    Parameters to control save options:
        fig_save (bool): Save to file option.
        fig_name (str): File name. 
        fig_path (str): Path to save file.
        fig_format (str): File format without dot, i.e. png, jpeg, etc.
        
Examples:
    None.

Notes:
    None.

References:
    Matplotlib reference colors:
        https://matplotlib.org/gallery/color/named_colors.html
        https://matplotlib.org/tutorials/intermediate/tight_layout_guide.html
        
Author information:
    @author: Miguel Angel Munoz
    @role: JRC Trainee. Ph.D. student. University of Malaga.
    @email: miguelangeljmd@gmail.com
    @Linkdin: Search for miguelangeljmd

"""

import matplotlib.pyplot as plt

from pyems.config import FigureParameter, Constant


def plot_results(values, titles=None, fig_show=FigureParameter.SHOW, fig_ratio=FigureParameter.RATIO,
        fig_width=FigureParameter.WIDTH, fig_space_ratio=FigureParameter.SPACE_RATIO,
        fig_save=FigureParameter.SAVE, fig_name=FigureParameter.NAME,
        fig_path=FigureParameter.PATH, fig_format=FigureParameter.FORMAT,
        fig_timestamp=FigureParameter.TIMESTAMP
    ):
    
    x_values = range(1, Constant.DAY_HOURS + 1)
    y_values = values
    
    ## FIGURE PLOTING AND CONFIGURATION
    
    # Create figure an axis objects
    
    fig, axes = plt.subplots(2, 2, sharex=True)
    fig_high = fig_width / fig_ratio
    fig.set_size_inches(fig_width, fig_high)
    fig.subplots_adjust(bottom=0.2, top=0.8, left=0.15, right=0.85)    
    
    # Plot data and horizontal lines
    
    axes[0, 0].bar(x_values, y_values['power_supply_flow'])
    axes[0, 1].bar(x_values, -1 * y_values['building_load'])
    axes[0, 1].bar(x_values, y_values['stochastic_generation'])
    axes[1, 0].bar(x_values, y_values['battery_energy_flow'])
    axes[1, 1].bar(x_values, y_values['battery_soc'])
    
#    for xvl in x_vertical_lines:
#        ax.vlines(xvl, y_axis_min, y_axis_max,
#          color='lightgrey', linestyles='dashed', linewidth=1)
#        
#    for yhl in y_horizontal_lines:
#        ax.hlines(yhl, START_HOUR, END_HOUR,
#          color='lightgrey', linestyles='dashed', linewidth=1)
        
    # Configure axis options
    
    for ax in axes.flat:
        if titles is not None:
            ax.set_title(titles['suptitle'], pad=25)
            ax.set_xlabel(titles['xlabel'], labelpad=20)
            fig.text(0.08, 0.75, titles['ylabel'])
        
#        ax.yaxis.set_ticks_position('left')
#        ax.xaxis.set_ticks_position('bottom')
#        ax.tick_params(axis='both', which='major', pad=12, left=False)
    
#    ax.set_xlim(START_HOUR, END_HOUR)
#    ax.set_ylim(y_axis_min, y_axis_max)
#    ax.xaxis.set_ticks([2 * i for i in range(13)])
#    ax.yaxis.set_ticks(y_horizontal_lines)
    
    return fig, ax


if __name__ == '__main__':

    # =============================================================================
    #     TESTING
    # =============================================================================

    pass



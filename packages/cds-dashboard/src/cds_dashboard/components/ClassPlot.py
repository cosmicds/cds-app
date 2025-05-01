import solara
from solara.lab.components import use_dark_effective
import plotly.express as px
import plotly.graph_objects as go

from ..logger_setup import logger

from ..data.load_data import hubble_data, hst_data

@solara.component
def ClassPlot(dataframe, 
            x_col = "est_dist_value", 
            y_col = "velocity_value", 
            label_col = "student_id", 
            xy_label = {"x":{'label': 'Distance', 'units': 'Mpc'}, "y":{'label': 'Velocity', 'units': 'km/s'}},
            on_click = None,
            select_on = None,
            selected = solara.reactive(None),
            allow_click = True,
            subset = None,
            subset_label = None,
            main_label = None,
            subset_color='#0097A7',
            main_color='#BBBBBB',
            show_hubble = True,
            show_hst = True
              ):
    
    subset = None
    
    logger.debug('Generating Class Plot')
    
    if select_on is None:
        select_on = "student_id"
    
    if dataframe is None:
        solara.Markdown("No data")
        return 
    
    config = {
            'remove': [
                'zoom2d', 
                'pan2d', 
                'lasso2d', 
                'zoomIn2d', 
                'zoomOut2d',
                'autoscale'
            ]
        }
    
    if use_dark_effective():
        plotly_theme = 'plotly_dark'
        axes_color = "#efefef"
        border_color = "#ccc"
        bgcolor = "#333"
        plot_bgcolor = "#111111"
    else:
        plotly_theme = 'simple_white'
        axes_color = "black"
        border_color = "#444"
        bgcolor = "#efefef"
        plot_bgcolor = "white"
    
    if x_col not in dataframe.columns:
        logger.debug(f"ClassPlot: {x_col} not in dataframe")
        solara.Markdown(f"**{x_col}** not in dataframe")
        return
    
    labels =  {x_col: "{label} ({units})".format(**xy_label['x']),  
               y_col: "{label} ({units})".format(**xy_label['y'])}
    fig = px.scatter(dataframe, x=x_col, y=y_col, custom_data = label_col, labels = labels, template=plotly_theme)
    
    if subset is None and selected.value is None:
        main_color = subset_color
        main_marker_size = 7
        main_label = 'Full Class'
    else:
        main_marker_size = 5
        

    fig.update_traces(marker_color=main_color, marker_size = main_marker_size)
    fig.update_layout(modebar = config, title="Class Hubble<br>Diagram", xaxis_showgrid=False, yaxis_showgrid=False, plot_bgcolor=plot_bgcolor)
    fig.update_xaxes(linecolor=axes_color, showgrid=False, zeroline=False)
    fig.update_yaxes(linecolor=axes_color, showgrid=False, zeroline=False)
    # add empty trace to show on legend
    fig.add_trace(go.Scatter(x=[None], y=[None], mode = 'markers', name = main_label, marker_color = main_color, marker_size = main_marker_size))

    xlabel = xy_label["x"]['label']+': %{x:f} ' + xy_label["x"]['units']
    ylabel = xy_label["y"]['label']+': %{y:f} ' + xy_label["y"]['units']
    hovertemplate = xlabel + '<br>' + ylabel + '<br>Student: %{customdata}' 
    
    fig.update_traces(hovertemplate=hovertemplate) 
    
    def click_action(points):
        if not allow_click:
            return
        selected_index = points['points']['point_indexes'][0]
        selected.set(dataframe.iloc[selected_index][select_on])
        if on_click is not None:
            on_click(points)
    
    # show in background
    if show_hubble:
        logger.debug('Adding Hubble trace')
        fig.add_trace(go.Scatter(x= hubble_data[x_col], y= hubble_data[y_col], mode = 'markers',
                                            hovertemplate = "<b>Hubble</b><br>" + xlabel + '<br>' + ylabel,
                                            name = 'Hubble',
                                            marker_symbol = 'circle',   
                                            marker_size = 7,
                                            zorder=-1,
                                            marker_color = '#c676bd'))
    if show_hst:
        logger.debug('Adding HST trace')
        fig.add_trace(go.Scatter(x= hst_data[x_col], y= hst_data[y_col], mode = 'markers',
                                            hovertemplate = "<b>HSTble</b><br>" + xlabel + '<br>' + ylabel,
                                            name = 'HST',
                                            marker_symbol = 'circle',   
                                            marker_size = 7,
                                            zorder=-1,
                                            marker_color = '#80bc8d'))
    
    if subset is not None:
        logger.debug('Adding seen trace')
        sub_data = dataframe[subset]
        hovertemplate = '<b>%{customdata}</b><br>' + xlabel + '<br>' + ylabel
        fig.add_trace(go.Scatter(x= sub_data[x_col], y= sub_data[y_col], mode = 'markers',
                                            customdata = sub_data[label_col],
                                            hovertemplate = hovertemplate,
                                            name = subset_label,
                                            marker_symbol = 'circle',   
                                            marker_size = 7,
                                            marker_color = subset_color))
        
    if selected.value is not None:    
        logger.debug('Adding student trace')
        stud_data = dataframe[dataframe[select_on] == str(selected.value)]

        hovertemplate = '<b>%{customdata}</b><br>' + xlabel + '<br>' + ylabel
        fig.add_trace(go.Scatter(x= stud_data[x_col], y= stud_data[y_col], mode = 'markers',
                                            customdata = stud_data[label_col],
                                            hovertemplate = hovertemplate,
                                            name = str(selected.value),
                                            marker_symbol = 'circle',   
                                            marker_size = 10,
                                            marker_color = '#FF8A65'))
    
    fig.update_layout(
        legend = dict(
            orientation="v",
            yanchor="bottom",
            y=1,
            xanchor="right",
            x=1,
            bordercolor=border_color,
            borderwidth=0,
            bgcolor=bgcolor,
            itemclick = False,
            itemdoubleclick = False,
            font=dict(size=11),
        ),
        margin=dict(l=0, r=25, t=50, b=0),
        title = dict(
            xref='container',
            x=0.05,
            xanchor='left',
            yref='container',
            yanchor='top',
            y=.95,
        )
    )
    
    
    return solara.FigurePlotly(fig, on_click=click_action, )
        

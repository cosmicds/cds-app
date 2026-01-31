import solara
import plotly.express as px
import plotly.graph_objects as go
from solara.lab.components import use_dark_effective
from collections import Counter
import numpy as np

from numpy import nanmin, nanmax, isnan

def matching_cols(df, val, col, count = None):
    """
    Return a dictionary of columns and values for a given value of a column
    """
 
    out = {c:df[c][df[col]==val].to_list() for c in df.columns}
    out.update({'count':count or len(out[col])})
    out.update({col:val})
    return out

def aggregrate(dataframe, col):
    vals = Counter(dataframe[col])
    return {v:matching_cols(dataframe, v, col, count)  for v,count in vals.items()}


@solara.component
def AgeHoHistogram(data, selected = solara.Reactive(None), which = 'age', subset = None, subset_label = None, main_label = None, subset_color = '#0097A7', main_color = '#BBBBBB', title = None, merged_subset= None, merged_color = '#3e3e3e', show_merged = True, include_merged = True):
    # subset is boolean array which take subset of data
    
    # manual aggregation. instead use pandas groupby and agg
    # df_agg = DataFrame(aggregrate(data, which)).T
    # df_agg.sids = df_agg.sids.apply(lambda x:'<br>' + '<br>'.join(x))
    def sids_agg(sids):
        return '<br>'+ '<br>'.join(sids)
    def name_agg(names):
        return '<br>'+ '<br>'.join(names)
    
    # yeah, in this view we don't what they did or did not see
    subset = None
    

    def return_agged(data, which):
        return data.groupby(which, as_index=False).agg(count=(which,'size'), student_id = ('student_id', sids_agg), name = ('name', name_agg))

    if (merged_subset is not None) and (not include_merged):
        df_agg = return_agged(data[~np.array(merged_subset)], which)
    else:
        df_agg = return_agged(data, which)
        
    # add single valued column
    df_agg['group'] = 'Full Class'
    if len(df_agg) == 0:
        xmin, xmax = 0, 1
    else:
        xmin, xmax = nanmin(df_agg[which]), nanmax(df_agg[which])

    labels = {'age':'Age of Universe (Gyr)', 'student_id':'Student', 'name': 'Student', 'h0':'Hubble Constant (km/s/Mpc)'}
    

    
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
        
    if subset is None:
        main_label = "Your Class"
        main_color = subset_color
    
    # for students in the merged class, let's remove the student_id so doesn't show up in hover
    if (merged_subset is not None) and include_merged:
        merged_student_ids = set(data['student_id'][merged_subset].to_list())
        # id_string = df_agg['student_id'].to_list() # the result of sids_agg is a string with <br> separated student ids // we need to filter out those in the merged class
        # new_id_string = []
        for row in range(len(df_agg)):
            sids = df_agg.at[row, 'student_id'].split('<br>')
            names = df_agg.at[row, 'name'].split('<br>')
            filtered_sids = [sid for sid in sids if sid not in merged_student_ids]
            # want to filer names via index of sids
            filtered_names = [names[i] for i in range(len(sids)) if sids[i] not in merged_student_ids]
            if len(filtered_sids) == 0:
                df_agg.at[row, 'student_id'] = ''
                df_agg.at[row, 'name'] = ''
            else:
                df_agg.at[row, 'student_id'] = '<br>'.join(filtered_sids)
                df_agg.at[row, 'name'] = '<br>'.join(filtered_names)
        
    fig = px.bar(data_frame = df_agg, x = which, y='count', hover_data='name', labels = labels, barmode='overlay', opacity=1, template=plotly_theme)
    fig.update_traces(hovertemplate = labels[which] + ': %{x}<br>' + 'count=%{y}<br>' + labels['student_id'] + ': %{customdata}' + '<extra></extra>', width=0.8)

    if subset is None:
        main_color = subset_color
        main_label = "Your Class"

    fig.update_traces(marker_color=main_color)
    fig.add_trace(go.Bar(x=[None], y=[None], name = main_label, marker_color = main_color))
    title = f'Class {which.capitalize()}<br>Distribution' if title is None else title
    fig.update_layout(showlegend=True, title_text=title, xaxis_showgrid=False, yaxis_showgrid=False, plot_bgcolor=plot_bgcolor)
    # show only integers on y-axis
    fig.update_yaxes(tick0=0, dtick=1, linecolor=axes_color)
    # show ticks every 1
    fig.update_xaxes(range=[xmin-1.5, xmax+1.5], linecolor=axes_color)
    
    
    
    if include_merged and show_merged and merged_subset is not None:
        data_merged = data[merged_subset]
        df_agg_merged = return_agged(data_merged, which)
        bar = go.Bar(x=df_agg_merged[which], y=df_agg_merged['count'],
                     name=f'Ages from merged class', 
                     opacity=1, 
                     width=0.8,
                     marker_color=merged_color,
                     hoverinfo='skip', 
                     customdata=df_agg_merged['student_id'])
        bar.hovertemplate = labels[which] + ': %{x}<br>' + 'count=%{y}<br>' + labels['student_id'] + ': %{customdata}' + '<extra></extra>'
        fig.add_trace(bar)
    
    if subset is not None:
        data_subset = data[np.array(subset) & (~np.array(merged_subset) if merged_subset is not None else True)]
        # df_agg_subset = data_subset.groupby(which, as_index=False).agg(count=(which,'size'), student_id = ('student_id', sids_agg))
        df_agg_subset = return_agged(data_subset, which)
        bar = go.Bar(x=df_agg_subset[which], y=df_agg_subset['count'],
                     name=subset_label, 
                     opacity=1, 
                     width=0.8,
                     marker_color=subset_color,
                     hoverinfo='skip', 
                     customdata=df_agg_subset['student_id'])
        bar.hovertemplate = labels[which] + ': %{x}<br>' + 'count=%{y}<br>' + labels['student_id'] + ': %{customdata}' + '<extra></extra>'
        fig.add_trace(bar)

    if selected.value is not None:
        data_subset = data[data['student_id']==str(selected.value)]
        if len(data_subset) > 0:
            # df_agg_subset = data_subset.groupby(which, as_index=False).agg(count=(which,'size'), student_id = ('student_id', sids_agg))
            df_agg_subset = return_agged(data_subset, which)
            bar = go.Bar(x=df_agg_subset[which], y=df_agg_subset['count'],
                        name=str(selected.value), 
                        opacity=1, 
                        width=0.8,
                        marker_color='#FF8A65',
                        hoverinfo='skip', 
                        customdata=df_agg_subset['student_id'])
            bar.hovertemplate = labels[which] + ': %{x}<br>' + 'count=%{y}<br>' + labels['student_id'] + ': %{customdata}' + '<extra></extra>'
        
            fig.add_trace(bar)

        
        # show legend
    # fig.update_layout(showlegend=True)
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
    
    

    solara.FigurePlotly(fig)
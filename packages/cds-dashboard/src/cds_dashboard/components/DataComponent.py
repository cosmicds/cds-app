import solara

from .ClassPlot import ClassPlot

from pandas import DataFrame, to_datetime, Series


from numpy import around, asarray

from .TableComponents import DataTable
from .AgeHistogram import AgeHoHistogram

from ..logger_setup import logger
from ..class_report import Roster
from solara.reactive import Reactive
from typing import Optional, cast
from solara.alias import rv

def get_class_subset(data, sid, class_data_students = None, ungroup = True):
    if isinstance(sid, solara.Reactive):
        sid = sid.value
    if sid is None:
        return None
    sid = str(sid)
    
    if 'last_modified' not in data.columns:
        return [True for i in range(len(data))]
    
    use_class_data_students = class_data_students is not None
    
    # convert last_modified to datetime
    data['last_modified'] = to_datetime(data['last_modified'])
    data['student_id'] = data['student_id'].apply(str)
    if not use_class_data_students:
        class_data_students = data['student_id'].unique()
    class_data_students = asarray(class_data_students).astype(str)
    data['in_class'] = data['student_id'].isin(class_data_students)
    # group by student_id
    grouped = data.groupby('student_id')
    # get the groups
    groups = grouped.groups
    in_class = asarray([g in class_data_students for g in groups])
    
    # get people who completed and their times
    time = DataFrame(grouped['last_modified'].max())
    size = grouped.size()
    if all(size == 1):
        complete = (size == 1)
    else:
        complete = (size == 5)
    
    if use_class_data_students:
        subset = in_class | (time.index == sid)
    else:
        before = time['last_modified'] <= time[time.index == sid]['last_modified'].max()    
        ten_earlist_completed = time[complete].sort_values('last_modified').head(10)
        ten_earliest_mask = time.index.isin(ten_earlist_completed.index)
        subset = (before & complete) | ten_earliest_mask | (time.index == sid)
    
    logger.debug(f"The class subset is: {list(subset)}")
    
    if not ungroup:
        return list(subset)

    # put complete back into data
    subset = data['student_id'].isin(time[subset].index).to_list()
    
    # assert sum(subset) % 5 == 0
    
    
    return subset



@solara.component
def DataSummary(roster: Reactive[Roster] | Roster = None, student_id = None, on_student_id = None, allow_click = True):
    """
    Display a summary of the data
    """
    
    logger.debug('Displaying data summary')
    
    roster = solara.use_reactive(roster).value
    show_hubble = solara.use_reactive(False)
    show_hst = solara.use_reactive(False)
    
    data = cast(DataFrame, roster.get_class_data(df=True))
    # add names
    data['name'] = [roster.get_student_name(int(sid)) for sid in data['student_id']]
    
    student_id = solara.use_reactive(student_id)
    
    if data is None or roster is None:
        return
    
    if on_student_id is None:
        on_student_id = student_id.set
    
    def on_plot_click(points):
        logger.debug("DataSummary: ClassPlot clicked")
        if points is not None:
            selected_index = points['points']['point_indexes'][0]
            on_student_id(data.iloc[selected_index].student_id)
        else:
            on_student_id(None)
    
    subset = None
    main_name = None
    subset_name = None
    class_data_students = None
    if student_id.value is not None:
        
        idx = roster.student_ids.index(student_id.value)
        if (idx is not None) and ('class_data_students' in roster.roster[idx]['story_state']):
            class_data_students = roster.roster[idx]['story_state']['class_data_students']
            # if len(class_data_students) == 0:
            #     class_data_students = None
        # solara.Markdown(f"{class_data_students}")
        subset = get_class_subset(data, student_id, 
                                  class_data_students = class_data_students, 
                                  ungroup = True)
        main_name = f'Data not seen by {student_id.value}'
        subset_name = f'Data seen by {student_id.value}'
        
    
    if allow_click:
        ClassPlot(data, on_click=on_plot_click, label_col='name', select_on = 'student_id', selected = student_id, allow_click=True, subset = subset, subset_label=subset_name, main_label=main_name, subset_color='#0097A7', main_color='#BBBBBB', show_hubble = show_hubble.value, show_hst = show_hst.value)
    else:
        ClassPlot(data, select_on = 'student_id', label_col='name', selected = student_id, allow_click = False, subset = subset, subset_label=subset_name, main_label=main_name, subset_color='#0097A7', main_color='#BBBBBB', show_hubble = show_hubble.value, show_hst = show_hst.value)
    with rv.Row(justify='start'):
        solara.Button(
            label = f"{'Hide' if show_hubble.value else 'Show'} Edwin Hubble's Data", 
            color = "secondary", 
            on_click = lambda: show_hubble.set(not show_hubble.value), 
            style = {
                'margin': '5px',
                'text-transform': 'none', 
                'height': '1.8rem',
                }
            )
        solara.Button(
            label = f"{'Hide' if show_hst.value else 'Show'} HST Data", 
            color = "secondary", 
            on_click = lambda: show_hst.set(not show_hst.value), 
            style = {
                'margin': '5px',
                'text-transform': 'none', 
                'height': '1.8rem',
                }
            )

from numpy import nan, array
def get_slope(x, y):
    if (x is None) or (y is None):
        return nan
    # drop None values
    pairs = [(xi,yi) for xi,yi in zip(x,y) if (xi is not None) and (yi is not None)]
    if len(pairs) == 0:
        return nan
    x, y = array(pairs).T
    # slope through origin
    return nan if (sum(x**2) == 0) else (sum(x*y)/sum(x**2))
def slope2age(h0):
    return 977.79222 / h0 # age of universe in Gyr



    
@solara.component
def StudentMeasurementTable(roster: Reactive[Roster] | Roster = None, sid = None, headers = None, show_class = False, show_index = False):
    
    roster = solara.use_reactive(roster)
    roster = roster.value
    sid = solara.use_reactive(sid)
    sid = sid.value
    
    if roster is None:
        return
    
    if sid in roster.student_ids:
        dataframe = DataFrame(roster.get_student_data(sid))
    elif (sid is None) and show_class:
        dataframe = DataFrame(roster.get_class_data(df = True))
    else:
        solara.Markdown('Provided invalid student id')
        return
       

    if isinstance(headers, list):
        if isinstance(headers[0], dict) and {'text','value'}.issubset(headers[0].keys()):
            logger.debug('Good heaaders')
        elif isinstance(headers[0], str):
            headers = [{'text': h, 'value': h} for h in headers]
        else:
            logger.error('StudentMeasurementTable: headers is a list but not of the form [{"text": "header", "value": "col_name"}, ...]')
            logger.error('defaulting to displaying all columns  with their column names')
            headers = [{'text': h, 'value': h} for h in dataframe.columns]
    elif isinstance(headers, dict):
        headers = [{'text': v, 'value': k} for k,v in headers.items()]
    else:
        headers = [{'text': h, 'value': h} for h in dataframe.columns]
    
    
    DataTable(df = dataframe, headers = headers, class_ = "student-measurement-table", show_index=show_index)

@solara.component
def StudentData(roster: Reactive[Roster] | Roster = None, id_col = 'student_id',  sid = None, cols_to_display = None, on_sid = None, allow_id_set = True):
    """
    Display a single student's data
    """
    
    logger.debug('Displaying single students data')
    
    if isinstance(roster, solara.Reactive):
        roster = roster.value
    if roster is None:
        return
    
    dataframe = roster.get_class_data(df = True)
    if len(dataframe) == 0:
        solara.Markdown("There is no data for this class")
        return



    if sid is not None and sid.value is not None:        
        StudentMeasurementTable(roster, sid, headers = cols_to_display)
            
@solara.component
def StudentAgeHubble(roster: Reactive[Roster] | Roster = None, sid = None, allow_id_set = True):
    
    roster = solara.use_reactive(roster).value

    sid = solara.use_reactive(sid)
    
    if roster is None:
        return
    
    dataframe = roster.get_class_data(df = True)
    if len(dataframe) == 0:
        solara.Markdown("There is no data for this class")
        return

    if sid.value is not None and sid.value in roster.student_ids:        
        single_student_df = roster.get_student_data(sid.value, df = True)
        if len(single_student_df) == 0:
            solara.Warning("There is no data for this student")
            return
        
        h0 = get_slope(single_student_df['est_dist_value'].to_numpy(), single_student_df['velocity_value'].to_numpy())
        age = slope2age(h0)
        solara.Markdown(f"""
                        #### Student Age of Universe:
                        {age:.0f} Gyr
                        #### Student Hubble Constant:
                        {h0:.0f} km/s/Mpc
                        """)

@solara.component
def DataHistogram(roster: Reactive[Roster] | Roster = None, id_col = 'student_id',  sid = None):
    """
    Display a single student's data
    """
    
    logger.debug('Displaying single students data')
    
    if isinstance(roster, solara.Reactive):
        roster = roster.value
    if roster is None:
        return
    
    dataframe = cast(DataFrame,roster.get_class_data(df = True))
    if len(dataframe) == 0:
        solara.Markdown("There is no data for this class")
        return
    
    #group by student_id
    grouped = dataframe.groupby(id_col)
    h0 = grouped.apply(lambda x: get_slope(x['est_dist_value'].to_numpy(), x['velocity_value'].to_numpy()))
    # get the name associated with the student_id
    age = h0.apply(slope2age)
    time = grouped['last_modified'].max()
    data = DataFrame({'h0': h0, 'age': age, 'last_modified': time}).reset_index() # move student_id to column
    # student_id to str
    data['student_id'] = data['student_id'].apply(str)
    data['name'] = [roster.get_student_name(int(sid)) for sid in data['student_id']]
    data['h0'] = data['h0'].apply(lambda x: around(x,0))
    data['age'] = data['age'].apply(lambda x: around(x,0))
    
    class_data_students = None

    if sid is not None and sid.value is not None:
        
        idx = roster.student_ids.index(sid.value)
        if (idx is not None) and ('class_data_students' in roster.roster[idx]['story_state']):
            class_data_students = roster.roster[idx]['story_state']['class_data_students']
            # if len(class_data_students) == 0:
            #     class_data_students = None

        # solara.Markdown(f"{class_data_students}")
        subset = get_class_subset(data, sid, 
                                  class_data_students = class_data_students, 
                                  ungroup = False)

        AgeHoHistogram(data, 
                       subset = subset, 
                       selected = sid,
                       main_label = f'Data not seen by {sid.value}',
                       subset_label = f'Data seen by {sid.value}', 
                       subset_color = '#0097A7')
    else:
        AgeHoHistogram(data)

@solara.component
def StudentStats(roster: Reactive[Roster] | Roster):
    """
    Display statistics about the class
    """
    
    roster = solara.use_reactive(roster)
    roster = roster.value
    if roster is None:
        return
    
    stats = roster.class_measurement_status()
    summary = stats['summary']
    num_complete = summary['num_complete'] # number of students with complete measurements
    n_students = summary['num_total']
    num_incomplete = summary['num_incomplete']
    num_vel = summary['num_vel'] # number of students with velocity measurements
    num_dist = summary['num_dist'] # number of students with distance measurements
    num_good = summary['num_good']  # number of students with measurements

    # get students with bad measurements (-9999)
    status_df = stats['status'] # dataframe
    bad_vel = status_df[status_df['velocities'] == -9999].index.to_list()
    bad_dist = status_df[status_df['distances'] == -9999].index.to_list()
    # join
    bad = set(bad_vel + bad_dist) # ints
    
    
    
    line1 = f"**Number of students**: {n_students}"
    line2 = f"**Number of students with measurements**: {num_good}"
    line3 = f"**Number of students who finished measurements **: {num_complete}"
    
    solara.Markdown('**Measurements Status**')
    solara.Markdown('<br>'.join([line1,line2,line3]))
    bad_str = ', '.join([str(i) for i in bad])
    solara.Markdown(f'**Students with bad measurements**: {bad_str}')
    


@solara.component
def StudentDataSummary(roster: Reactive[Roster] | Roster = None, student_id = None, allow_sid_set = True):
    
    roster = solara.use_reactive(roster).value
    student_id = solara.use_reactive(student_id)
    
    if roster is None:
        return
        

    solara.Markdown(r'''
            * Click-and-drag to zoom in on a region within either plot.
            * Double-click within the plot to zoom back out. 
            * Hover over a point or bar to see the values and student ID(s).
        ''')

    with solara.ColumnsResponsive(small=12, medium = [6,6], wrap=True, gutters=False, style="justify-content: start;"):
        with solara.Column():
            with solara.Card(style='height: 95%'):
                DataSummary(roster, student_id, allow_click=allow_sid_set)
        with solara.Column():
            with solara.Card(style='height: 95%'):
                DataHistogram(roster, sid = student_id)

    if student_id is not None and student_id.value is not None:
       with solara.ColumnsResponsive(small=12, medium = [6,6], wrap=True, gutters=False, style="justify-content: start;"):
            with solara.Column():
                with solara.Card(style='height: 90%'):
                    solara.Markdown(f"#### Student Galaxy Measurements")
                    
                    headers = [
                        {'value': 'galaxy_id', 'text': 'Galaxy ID'},
                        {'value': 'obs_wave_value', 'text': 'Observed Wavelength <br/> (Angstrom)'},
                        {'value': 'velocity_value', 'text': 'Velocity <br/> (km/s)'},
                        {'value': 'ang_size_value', 'text': 'Angular Size <br/> (arcsecond)'},
                        {'value': 'est_dist_value', 'text': 'Distance <br/> (Mpc)'},
                    ]
                    
                    StudentData(roster, id_col="student_id", sid = student_id, cols_to_display = headers, allow_id_set = allow_sid_set)
            with solara.Column():
                with solara.Card(style='height: 90%'):
                    StudentAgeHubble(roster, sid = student_id)









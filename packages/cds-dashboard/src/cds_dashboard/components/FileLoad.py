import solara
from solara.components.file_drop import FileInfo
from io import BytesIO

import pandas as pd

import re

from ..logger_setup import logger


@solara.component
def TableLoad(file_info = None, load_complete = None, allow_excel = False):
    
    
    file_info = solara.use_reactive(file_info)
    load_complete = solara.use_reactive(load_complete)
    
    valid_file, set_valid_file = solara.use_state(True)
    msg, set_msg = solara.use_state("")
    
    def on_file(file: FileInfo):
        filename = file['name']
        
        isCSV = filename.endswith('.csv')
        isExcel = filename.endswith('.xlsx') or filename.endswith('.xls')

        if isCSV or (isExcel and allow_excel):
            file_info.set(file)
            set_valid_file(True)
        else:
            set_valid_file(False)
            set_msg(f"Failed to read {filename}. Please select a valid CSV file.")
        
        load_complete.set(True)
    
    def on_click():
        file_info.set(None)
        load_complete.set(False)
        set_msg("")
    
    with solara.Div():
        solara.Markdown(r'''
            Read in a local CSV (comma-separated value) file containing student IDs and names to display names in the dashboard.
                        
            * Include a header row with column names 'student_id' and 'name'. 
            * To protect student privacy, this information remains on your computer and will NOT be uploaded to CosmicDS servers.
        ''')
        if not load_complete.value:
            solara.FileDrop(
                on_file=on_file,
                lazy=False, # puts data in the [data] part of FileInfo
            )
        if load_complete.value and valid_file:
            solara.Button("Clear data", on_click=on_click)
        elif load_complete.value and not valid_file:
            solara.Error(msg, dense=True, outlined=True, icon='mdi-file-alert')
            solara.Button("Try another file", on_click=on_click)
            

def strip_non_alpha(string):
    return (''.join([c for c in str(string) if c.isalpha()])).lower()

def is_header_row(array):
    return all([strip_non_alpha(c).isalpha() for c in array])

def is_numeric_array(array):
    return all((str(val).isnumeric() for val in array))

def verify_table(df):
    # check that the columns are 'student_id' and 'name'
    cols = list(df.columns.to_numpy().astype(str))
    cols = [c.strip() for c in cols]
    return is_header_row(cols)
    
@solara.component
def CSVFileInfoToTable(file_info, on_table = None, display = True):
        
    if isinstance(file_info, solara.Reactive):
        file_info = file_info.value
    
    if isinstance(on_table, solara.Reactive):
        do_on_table = on_table.set
    else:
        do_on_table = on_table if on_table is not None else lambda x: None
    
    if file_info is None:
        return
    
    filename = file_info['name']
    bytes_data = file_info['data']
    # check for commas that are inbetween words enclosed in double quotes and remove that comma
    # using regex and string methods
    regex = r',(?!(?:[^"]*"[^"]*")*[^"]*$)'
    matches = re.findall(regex, bytes_data.decode('utf-8'))
    if len(matches) > 0:
        solara.Warning("Some cells in your csv file contain commas, possibly in the form 'last name, first name.' If student names do not look right, you may need to remove extra commas and reload the file.", icon='mdi-traffic-cone', dense=True)
    bytes_data = re.sub(regex, '', bytes_data.decode('utf-8')).encode('utf-8')
    
    if filename.endswith('.csv'):
        # read in the table assuming it has no header row
        table_no_header = pd.read_csv(BytesIO(bytes_data), header=None, skip_blank_lines=True, quotechar='"', encoding='utf-8')
        # if the first row is a valid header row, read in the table again
        if is_header_row(table_no_header.iloc[0].to_numpy()):
            table_with_header = pd.read_csv(BytesIO(bytes_data), header=0, skip_blank_lines=True, quotechar='"', encoding='utf-8')
            if not verify_table(table_with_header):
                logger.error('header row is not valid. revert to no_header version')
                table = table_no_header
            else:
                logger.info('has good header row')
                table = table_with_header
        else:
            logger.info('no header row')
            table = table_no_header
    else:
        ext = filename.split('.')[-1]
        logger.error(f"The dashboard cannot read ${ext} files.")
        solara.Error(f"The dashboard cannot read ${ext} files. Please convert your file to a CSV (comma-separate values file) and try again.")
        return
    
    do_on_table(table)
    logger.info("File successfully uploaded")
    
    if display:
        solara.DataFrame(table.head(5))


def validate_column_choices(table, id_col, name_col):
    if table is None:
        return False
    
    if id_col == name_col:
        logger.error("id_col == name_col")
        return False

    if id_col not in table.columns:
        logger.error("id_col not in table.columns")
        return False

    if name_col not in table.columns:
        logger.error("name_col not in table.columns")
        return False

    if is_numeric_array(table[id_col]):
        logger.error("is_numeric_array(table[id_col])")
        pass

    return True

def check_cols(table, cols, valid_id_cols):

    if not ('student_id' in valid_id_cols):
        return False
    if not ('name' in cols):
        return False
    if not (len(valid_id_cols) == 1):
        return False
    if not (len(cols) == 2):
        return False
    if not is_numeric_array(table[valid_id_cols[0]].to_numpy()):
        return False
    logger.debug("check cols passed")
    return True
    
    

@solara.component
def SetColumns(table, on_set = None):

    student_id_column = solara.use_reactive('student_id')
    name_column = solara.use_reactive('name')
    cols_set = solara.use_reactive(False)
    
    def on_table_change(new_table):
        logger.debug("table changed")
        # reset this component when the table changes
        cols_set.set(False)
        student_id_column.set('student_id')
        name_column.set('name')
    
    in_table = solara.use_reactive(table, on_change=on_table_change)
    table = in_table.value
    
    if table is None:
        return
    
    if on_set is None:
        on_set = lambda x: None
    
    skip_setting = False


    cols = list(table.columns.to_numpy().astype(str))
    cols = [str(c).strip() for c in cols]
    table.columns = cols

    valid_id_cols = [c for c in cols if is_numeric_array(table[c])]
    cols_are_valid = check_cols(table, cols, valid_id_cols)
    if cols_are_valid:
        skip_setting = True
    else:
        logger.error("cols check failed")
        solara.Warning('There is an issue with your column headers. Use these dropdown menus to specify the correct columns.', icon='mdi-traffic-cone', dense=True)
        skip_setting = False

    
    if not skip_setting and len(cols) > 0:
        solara.Markdown("Select column containing student IDs from dropdown list.")
        solara.Select(label = 'Student ID column', values = valid_id_cols, value = student_id_column, dense=True, style="width: 40ch")
        
        solara.Markdown("Select column containing names from dropdown list.")
        solara.Select(label = 'Student name column', values = [c for c in cols if c != student_id_column.value], value = name_column, dense=True, style="width: 40ch")
        
        def on_click():
            logger.debug('clicked')
            cols_set.set(True)
        solara.Button("Set columns", on_click = on_click)

    if (cols_are_valid or cols_set.value) and validate_column_choices(table, student_id_column.value, name_column.value):
        df = table[[student_id_column.value, name_column.value]]
        df.columns = ['student_id', 'name']
        on_set(df)
    elif cols_set.value:
        solara.Error('Please select valid columns.', dense=True, outlined=True)
            
import pandas as pd
from .database.nested_dataframe import flatten
from .database.State import State
from .database.Query import QueryCosmicDSApi
from .database_new.NewState import State as NewState
import time
HUBBLE_ROUTE_PATH = "hubbles_law"

import astropy.units as u
from math import nan

from .utils import l2d, convert_column_of_dates_to_datetime, get_or_none

from typing import List, Dict, cast, Optional, Any, Union, TypeVar, overload, TYPE_CHECKING, TypedDict
from .database.types import (
    StateInterface,
    OldRosterEntry,
    NewRosterEntry as ImportedNewRosterEntry,
    OldRoster,
    NewRoster as ImportedNewRoster,
    RosterAttributes,
    ProcessedState as ImportedProcessedState,
    OldStudentStoryState,
    StudentEntryList,
    MCScore,
    EmptyScoreOrResponse,
    FreeResponses,
)
from .database_new.types import (
    NewStudentStoryState,
    StudentEntry as NewRosterEntry,
    NewRoster,
    ProcessedState,
    StoryState as NewStoryState,
    AppState
)

from .cr_types import HubbleData, ProgressSummary, QuestionInfo, MeasurementStatus

from .logger_setup import logger

class Student():

    student_id = None
    class_id = None
    story_state = {}
    stage_state = {}
    _data = None
    _mc_questions = {}
    _fr_questions = {}


    def __init__(self, student_id = None):
        self.student_id = student_id

    @property
    def data(self):
        return self._data


class StudentIDList(TypedDict):
    student_id: List[int]


class Roster():
    def __init__(self, class_id=None, query=None):

        self._mc_questions = None
        self._fr_questions = None
        self._questions = None
        self._question_keys = None
        self._mc_keys = {}
        self._fr_keys = {}
        self._report = None
        self._short_report = None

        self._refresh = False

        self.class_id = class_id
        logger.info(f"Creating roster for {class_id}")

        self.new_db = class_id >= 215 if class_id is not None else False
        if self.new_db:
            logger.info("Using new database scheme")

        if query is None:
            self.query = QueryCosmicDSApi(class_id=class_id, story=HUBBLE_ROUTE_PATH)
        else:
            self.query = query
            query.class_id = class_id
            query.story = HUBBLE_ROUTE_PATH
        self.data = None
        self.student_data: Dict[int, Any] = {}
        self.class_summary = None
        self.grab_data()
        self.has_real_names = False
        self.real_names: Optional[Dict[int, str]] = None

    def __eq__(self, other):
        if other.short_report() is None:
            return False
        return self.short_report() == other.short_report()

    @staticmethod
    def flatten_dict(d):
        return flatten(d)

    @staticmethod
    def fix_mc_scoring(roster):
        for i, student in enumerate(roster):
            count = 0
            story_state = student['story_state']
            mc_scoring = story_state['mc_scoring']
            for stage, scores in mc_scoring.items():
                for key, value in scores.items():
                    if value['tries'] == 0:
                        count += 1
                        mc_scoring[stage][key]['score'] = 10
                        mc_scoring[stage][key]['tries'] = 1
            roster[i]['story_state']['mc_scoring'] = mc_scoring
        return roster

    @staticmethod
    def dict_by_stage(data):
        stages = set([value['stage'] for value in data.values() if 'stage' in value.keys()])
        if len(stages) == 0:
            logger.debug('No stages found')
            return data
        new_data = {}
        for stage in stages:
            new_data[stage] = {
                key: value
                for key, value in data.items() if 'stage' in value and value['stage'] == stage
            }
        return new_data

    def fix_new_story_state(self, roster: List[NewRosterEntry]) -> List[OldRosterEntry]:
        """
        Transforms the story state structure from the new format (>= class_id 215) to the common format
        
        
        """
        for i, student in enumerate(roster):
            # Cast to proper types to help the type checker
            typed_student = cast(NewRosterEntry, student)
            story_state = cast(NewStudentStoryState, typed_student['story_state'])

            # Store app state separately
            roster[i]['app_state'] = cast(Dict, story_state['app'])

            # Replace story_state with just the story part
            roster[i]['story_state'] = story_state['story']  # type: ignore -- we don't use the mis-matched parameters

            # Ensure student_id is propagated
            roster[i]['student_id'] = student['student_id']

            # Process free responses
            # try:
            free_responses_dict = story_state['story']['free_responses'].copy()
            # except:
            # breakpoint()
            if 'responses' in free_responses_dict:
                free_responses = free_responses_dict.pop('responses')
                responses = self.dict_by_stage(free_responses)
                responses = {
                    stage_key: {q_key: q_value.get('response', '')
                                for q_key, q_value in stage_value.items()}
                    for stage_key, stage_value in responses.items()
                }
                cast(OldStudentStoryState, roster[i]['story_state'])['responses'] = responses

            # Remove free_responses after extraction
            if 'free_responses' in roster[i]['story_state']:
                roster[i]['story_state'].pop('free_responses')

            # Process multiple choice scoring
            mc_scoring_dict = story_state['story']['mc_scoring'].copy()
            if 'scores' in mc_scoring_dict:
                mc_scoring = mc_scoring_dict.pop('scores')
                roster[i]['story_state']['mc_scoring'] = self.dict_by_stage(mc_scoring)

        return cast(List[OldRosterEntry], roster)

    def include_stages(self):
        """
        Adds stage information to the story state for newer database versions
        
        
        """
        for i, student in enumerate(self.roster):
            stages = self.query.get_stages(student['student_id'])
            cast(OldStudentStoryState, self.roster[i]['story_state'])['stages'] = stages

    def grab_data(self) -> None:
        """
        Gets roster data from the API and processes it based on database version
        
        
        """
        logger.debug('Getting roster')

        # Get roster data from API
        api_roster = self.query.get_roster()

        # Cast to appropriate type based on class_id
        if self.new_db:
            self.roster = self.fix_new_story_state(api_roster)
            self.include_stages()
        else:
            self.roster = cast(List[OldRosterEntry], api_roster)

        self.data = None

        # Handle empty roster case
        if len(self.roster) == 0:
            self.student_id = {'student_id': []}
            self.story_name = {'story_name': []}
            self._story_state = {'stages': []}
            self._stages = []
            self.last_modified = {}
            self.stage_index = 0
            return

        # Process roster data
        keys = self.roster[0].keys()
        new_out = cast(StudentEntryList, l2d(self.roster))  # type: ignore
        keys = new_out.keys()
        for key in keys:
            if isinstance(new_out[key][0], dict):
                new_out[key] = l2d(new_out[key])
            elif isinstance(new_out[key], list):
                new_out[key] = {key: new_out[key]}
            else:
                logger.debug(f"for {key} new_out[key] as type: {type(new_out[key][0])}")

        self.student_id = cast(StudentIDList, new_out['student_id'])
        self.story_name = new_out['story_name'].get('story_name')[0]  # type: ignore
        self._story_state = cast(Dict,
                                 new_out['story_state'])  # Listed version of OldStudentStoryState (each key is a list)

        # Process stages
        keys = l2d(self._story_state['stages']).keys()
        self._stages = []

        def getstate(stage):
            if isinstance(stage, dict) and ('state' in stage.keys()):
                return stage['state']
            else:
                logger.debug(f'no state in class {self.class_id}')
                return {
                    'stage': {}, 'marker': None, 'responses': [], 'mc_scores': [], 'total_score': 0, 'state': {},
                    'title': None
                }

        for key in sorted(keys):
            self._stages.append([getstate(s) for s in l2d(self._story_state['stages'])[key]])

        self.last_modified = cast(Dict, new_out['last_modified'])

        # # Create processed state objects for all students
        # if self.new_db:
        #     self.new_story_state = [NewState(student['story_state']) for student in self.roster]
        # else:
        #     self.new_story_state = [State(student['story_state']) for student in self.roster]

        # # Calculate max stage values across all students
        # if len(self.new_story_state) > 0:
        #     self.max_stage_index = max([state.max_stage_index for state in self.new_story_state])
        #     self.max_marker = max([state.max_marker for state in self.new_story_state])
        # else:
        #     self.max_stage_index = 0
        #     self.max_marker = 0

    def l2d(self, list_of_dicts, fill_val=None):
        return l2d(list_of_dicts, fill_val)

    def get_class_data(self, refresh: bool = False, df: bool = False) -> Union[Dict, pd.DataFrame]:
        if self.data is None or self._refresh or refresh:
            res = self.query.get_class_data(class_id=self.class_id)
            if res is None or res == {} or len(res) == 0:
                res = {'student_id': []}
            self.data = res if res is not None else {'student_id': []}
            if len(self.student_data) == 0:
                groupdf = pd.DataFrame(self.data).groupby('student_id')
                for student_id in groupdf.groups.keys():
                    self.student_data[cast(int, student_id)] = groupdf.get_group(student_id).to_dict(orient='records')
        if df:
            return pd.DataFrame(self.data)
        return self.data

    def get_student_data(self, student_id, refresh=False, df=False):
        if (student_id not in self.student_data.keys()) or self._refresh or refresh:
            self.student_data[student_id] = self.query.get_student_data(student_id)['measurements']  # type: ignore
        if df:
            return pd.DataFrame(self.student_data[student_id])
        return self.student_data[student_id]

    def get_class_summary(self, refresh=False):
        if self.class_summary is None or self._refresh or refresh:
            measurements = self.measurements(refresh=refresh)

            def get_slope(x, y):
                # slope through origin
                return nan if (sum(x**2) == 0) else (sum(x * y) / sum(x**2))

            def slope2age(h0):
                return (1 / (h0 * u.km / u.s / u.Mpc)).to(u.Gyr).value

            H0 = []
            Age = []
            for student in self.student_ids:
                student_data = measurements[measurements['student_id'] == student]
                if len(student_data) == 5:
                    H0.append(get_slope(student_data['est_dist_value'], student_data['velocity_value']))
                    Age.append(slope2age(H0[-1]))
                else:
                    H0.append(nan)
                    Age.append(nan)
            self.class_summary = self.make_dataframe(pd.DataFrame({'H0': H0, 'age': Age}))

        return self.class_summary

    def class_measurement_status(self, refresh=False) -> MeasurementStatus:
        g = cast(pd.DataFrame, self.get_class_data(df=True, refresh=refresh)).groupby('student_id')
        nodist = g.apply(lambda x: 5 - sum(x['est_dist_value'] == 0))  # number of distances
        novel = g.apply(lambda x: 5 - sum(x['velocity_value'] == 0))  # number of velocities
        complete = (novel == 5) & (nodist == 5)
        df = pd.DataFrame({'distances': nodist, 'velocities': novel, 'complete': complete})
        m = set(df.index)
        a = set(self.student_ids)
        d = a - m  # students in roster but not in class data
        for d in a - m:
            df.loc[d] = {'distances': -9999, 'velocities': -9999, 'complete': False}  # type: ignore

        # summary
        summary = dict(
            num_complete=sum(df['complete']),  # number of students with complete data
            num_incomplete=len(df) - sum(df['complete']),  # number of students with incomplete data
            num_dist=sum(df['distances'] != -9999),  # number of students with distances
            num_vel=sum(df['velocities'] != -9999),  # number of students with velocities
            num_good=sum((df['distances'] != -9999) & (df['velocities'] != -9999)),  # number of students with good data
            num_total=len(df),  # number of students in class  
        )
        return {'summary': summary, 'status': df}

    def get_student_by_id(self, student_id):
        if student_id not in self.student_ids:
            # logger.debug(f'{student_id} not in roster')
            return None
        return [student for student in self.roster if student['student_id'] == student_id][0]

    def make_dataframe(self, dictionary, include_student_id=True, include_class_id=True, include_username=True):
        # take the dictionary and make a dataframe
        # add self.student_ids as a column

        if 'student_id' not in dictionary.keys() and include_student_id:
            dictionary['student_id'] = self.student_ids
        if 'class_id' not in dictionary.keys() and include_class_id:
            dictionary['class_id'] = self.class_id
        if 'username' not in dictionary.keys() and include_username:
            dictionary['username'] = self.students['username'].values
        # if isinstance(dictionary, pd.DataFrame):
        #     return dictionary.set_index('student_id')

        # add cols conditionally on inclusion
        first_cols = []
        if include_student_id:
            first_cols.append('student_id')
        if include_class_id:
            first_cols.append('class_id')
        if include_username:
            first_cols.append('username')

        cols = first_cols + [col for col in dictionary.keys() if col not in first_cols]
        dictionary = {k: dictionary[k] for k in cols}
        # df = pd.DataFrame(dictionary).set_index('student_id')
        return pd.DataFrame(dictionary)

    def measurements(self, refresh=False):
        if len(self.roster) > 0:
            if self.data is None or refresh:
                self.data = self.get_class_data(refresh=refresh)

            return pd.DataFrame(self.data)
        else:
            return pd.DataFrame()

    def multiple_choice_questions(self) -> Dict[str, List[MCScore]] | EmptyScoreOrResponse:
        if (self._mc_questions is not None) and (not self._refresh):
            return self._mc_questions
        if len(self.roster) > 0:
            out = l2d(self._story_state['mc_scoring'])
            out.update({'student_id': self.student_ids})
            self._mc_questions = out
            return out
        else:
            return {'student_id': self.student_ids}

    def free_response_questions(self) -> Dict[str, List[FreeResponses]] | EmptyScoreOrResponse:
        if (self._fr_questions) is not None and (not self._refresh):
            return self._fr_questions

        if len(self.roster) > 0:
            # if self.new_db:

            #     out = l2d(self.story_state['responses'])
            logger.debug(self._story_state['responses'])
            out = l2d(self._story_state['responses'])
            out.update({'student_id': self.student_ids})
            self._fr_questions = out
            # logger.debug(out)
            return out
        else:
            return {'student_id': self.student_ids}

    def questions(self):
        if (self._questions is not None) and (not self._refresh):
            return self._questions

        if len(self.roster) > 0:
            fr = self.free_response_questions()
            mc = self.multiple_choice_questions()
            df_fr = flatten(self.make_dataframe(fr, include_class_id=False, include_username=False))
            df_mc = flatten(self.make_dataframe(mc, include_class_id=False, include_username=False))  #.astype('Int64')
            self._questions = pd.merge(df_mc, df_fr, how='left', on='student_id')
        else:
            self._questions = pd.DataFrame({'student_id': self.student_ids})
        return self._questions

    def get_questions_text(self):
        qs = self.query.get_questions()
        if qs is None:
            logger.debug("""No questions found. Trying again after a moment.""")
            # wait 1 second
            time.sleep(1)
            qs = self.query.get_questions()
        return qs

    def question_keys(self, testing=False, get_all=True):
        if (self._question_keys is not None) and (not self._refresh):
            return self._question_keys

        self._question_keys = {}

        if get_all:
            questions = self.get_questions_text()
            if questions is None:
                logger.debug('No questions found')
                return self._question_keys

            keys = questions.keys()
            other_keys = set([c.split('.')[1] for c in self.questions().columns if '.' in c])
            keys = set(keys).union(other_keys)
        else:
            keys = set([c.split('.')[1] for c in self.questions().columns if '.' in c])

        for k in keys:
            if testing:
                q = {'text': 'Fake Long ' + k, 'shorthand': 'Fake Short ' + k}
            elif (k not in questions.keys()):
                logger.debug(f'{k} not in question database')
                nice_tag = ' '.join(k.replace('_', ' ').replace('-', ' ').split())
                q = {'text': 'Not in Question Database', 'shorthand': f'Not in Database ({nice_tag})'}
            else:
                q = questions[k]

            if q is not None:
                nice_tag = ' '.join(k.replace('_', ' ').replace('-', ' ').split())
                nice_tag = nice_tag[0].upper() + nice_tag[1:]

                short = q['shorthand']
                if short == '':
                    short = nice_tag
                self._question_keys[k] = {'text': q['text'], 'shorttext': short, 'nicetag': nice_tag}

        return self._question_keys

    def get_question_text(self, key) -> QuestionInfo:
        if key in self.question_keys().keys():
            return self.question_keys()[key]
        else:
            logger.debug(f'{key} not in question database')
            return {'text': 'Not in Question Database', 'shorttext': 'Not Available', 'nicetag': key}

    def mc_question_keys(self):
        mc = self.multiple_choice_questions()
        for stage in mc.keys():
            if stage == 'student_id':
                continue
            keys = self._mc_keys.get(stage, [])
            for s in mc[stage]:
                if s is not None:
                    for q in s.keys():
                        if q not in keys:
                            keys.append(q)
                    self._mc_keys[stage] = keys
        return self._mc_keys

    def fr_question_keys(self):
        fr = self.free_response_questions()
        for stage in fr.keys():
            if stage == 'student_id':
                continue
            keys = self._fr_keys.get(stage, [])
            for s in fr[stage]:
                if s is not None:
                    for q in s.keys():
                        if q not in keys:
                            keys.append(q)
                    self._fr_keys[stage] = keys

        return self._fr_keys

    @property
    def student_ids(self):
        if len(self.roster) > 0:
            return [student['student_id'] for student in self.roster]
        else:
            return []

    def set_student_names(self, student_names=None):
        """
        student_names is a dictionary of student_id: name
        """
        if len(self.roster) > 0:
            for student in self.roster:
                if student_names is None:
                    # use random string
                    student['student']['name'] = 'Student ' + str(student['student_id'])
                    # student['student']['name'] = student['username']
                else:
                    student['student']['name'] = student_names.get(student['student_id'],
                                                                   'Student ' + str(student['student_id']))

            # if student_names is not None:
        self.has_real_names = True
        self.real_names = student_names

    def get_student_name(self, sid=None):
        if sid is None:
            return 'None'
        if len(self.roster) > 0:
            index = self.student_ids.index(sid) if sid in self.student_ids else None
            if index is not None:
                return self.roster[index]['student'].get('name', str(sid))
            # else:
            #     logger.debug(f'{sid} not in roster')

        return str(sid)

    @property
    def responses(self):
        if len(self.roster) > 0:
            df = pd.DataFrame([student['story_state']['responses'] for student in self.roster])
            return self.make_dataframe(flatten(df))
        else:
            return self.make_dataframe(pd.DataFrame())

    def convert_column_of_dates_to_datetime(self, dataframe_column):
        return convert_column_of_dates_to_datetime(dataframe_column)

    @property
    def students(self):
        if len(self.roster) > 0:
            students = l2d([cast(Dict, student['student']) for student in self.roster])
            return self.make_dataframe(students)
        else:
            return pd.DataFrame({'student_id': [], 'username': [], 'class_id': []})

    @property
    def student_names(self):
        return [self.get_student_name(sid) for sid in self.student_ids]

    def student2state(self, student) -> StateInterface:
        """
        Creates a State object from a student's story state.
        Uses the appropriate State class based on database version.
        
        
        """
        if self.new_db:
            return cast(StateInterface, NewState(student['story_state']))
        else:
            return cast(StateInterface, State(student['story_state']))

    @property
    def out_of(self):
        if len(self.roster) == 0:
            return
        out_of = []
        for student in self.roster:
            state = self.student2state(student)
            state.mc_scoring
            out_of.append(state.get_possible_score())
        return out_of

    @property
    def student_scores(self):
        if len(self.roster) == 0:
            return None
        scores = []
        for student in self.roster:
            state = self.student2state(student)
            scores.append(state.story_score)
        return scores

    @property
    def max_stage_index(self):
        if hasattr(self, '_max_stage_index'):
            return self._max_stage_index
        if len(self.roster) == 0:
            return None
        max_stage = []
        for student in self.roster:
            state = self.student2state(student)
            max_stage.append(state.max_stage_index)
        return max_stage

    @property
    def max_stage_marker(self):
        if len(self.roster) == 0:
            return None
        max_stage = []
        for student in self.roster:
            state = self.student2state(student)
            max_stage.append(state.max_marker)
        return max_stage

    @property
    def stage_index(self):
        if len(self.roster) == 0:
            return None
        stage_index = []
        for student in self.roster:
            state = self.student2state(student)
            stage_index.append(state.stage_index)
        return stage_index

    @stage_index.setter
    def stage_index(self, value):
        # This property needs a setter since it's being assigned to in the code
        #
        self._stage_index = value

    @property
    def stage_name_to_index_map(self):
        """"""
        if len(self.roster) == 0:
            return {}

        # Create a mapping of stage names to indices
        stage_mapping = {}
        for student in self.roster:
            state = self.student2state(student)
            if hasattr(state, 'stage_names'):
                for i, name in enumerate(state.stage_names):
                    stage_mapping[name] = i
            else:
                stage_mapping[i] = i

        return stage_mapping

    def get_stage_index(self, stage_name: str) -> int:
        """
        Get the index for a stage name, used for sorting stages.
        
        """
        # Return the index if found, otherwise a high number to sort it last
        return self.stage_name_to_index_map.get(stage_name, 999)

    @property
    def progress_summary(self) -> Optional[ProgressSummary]:
        """"""
        if len(self.roster) == 0:
            return None

        completion_string, completion_percent = self.fraction_completed()
        return {'progress': completion_string, 'percent_story_complete': completion_percent}

    @property
    def hubble_data(self) -> HubbleData:
        """"""
        summary = self.get_class_summary()
        return {
            'hubble_constant': summary['H0'].apply(lambda x: round(x, 2)) if 'H0' in summary else None, 'age':
            summary['age'].apply(lambda x: round(x, 2)) if 'age' in summary else None
        }

    @property
    def last_modified_formatted(self):
        """"""
        if not hasattr(self, 'last_modified') or not self.last_modified:
            return None
        return pd.to_datetime(
            self.last_modified['last_modified']).tz_convert('US/Eastern').strftime("%Y-%m-%d %H:%M:%S (Eastern)")

    def fraction_completed(self):
        # for each stage, create a state object using their story_state
        how_far = []
        tot_perc = []
        for student in self.roster:
            state = self.student2state(student)
            how_far.append(state.how_far)
            tot_perc.append(state.percent_completion)
        return l2d(how_far)['string'], tot_perc

    def report(self, refresh=False, for_teacher=True):
        "refreshing data"

        if self._report is not None and not self._refresh and not refresh:
            return self._report

        if self._refresh:
            self.grab_data()

        if len(self.roster) == 0:
            return None

        if hasattr(self, 'stages') and (not for_teacher):
            data = [[get_or_none(s, 'marker', None) for s in stage] for stage in self._stages]
            cols = ['Stage 1 marker', 'Stage 3 marker', 'Stage 4 marker', 'Stage 5 marker', 'Stage 6 marker']
            c1 = {k: v for k, v in zip(cols, data)}
            df = pd.DataFrame(c1)
            df['student_id'] = self.student_id['student_id']
        else:
            df = pd.DataFrame({'student_id': self.student_id['student_id']})

        df['student_id'] = self.student_id['student_id']
        # add a string column containing roster.students['username']
        df['username'] = self.students['username'].values
        if 'name' in self.students.columns:
            df['name'] = self.students['name'].values
        df['class_id'] = self.class_id
        completion_string, completion_percent = self.fraction_completed()
        df['progress'] = completion_string
        df['percent_story_complete'] = completion_percent
        # df['percent_story_complete'] = df['percent_story_complete'].apply(lambda x: int(x))
        df['max_stage_index'] = self.max_stage_index
        df['max_stage_marker'] = self.max_stage_marker
        df['stage_index'] = self.stage_index
        df['total_score'] = self.student_scores
        df['out_of_possible'] = self.out_of
        summ = self.get_class_summary()
        df['Hubble_Constant'] = summ['H0'].apply(lambda x: round(x, 2))
        df['Age'] = summ['age'].apply(lambda x: round(x, 2))

        response = flatten(pd.DataFrame(self._story_state['responses']))
        response['student_id'] = self.student_id['student_id']
        df = df.merge(response, on='student_id', how='left')
        last_modified = pd.to_datetime(self.last_modified['last_modified']).tz_convert('US/Eastern').strftime(
            "%Y-%m-%d %H:%M:%S (Eastern)")  # in Easterm time
        df['last_modified'] = last_modified

        self._report = df

        return df

    def short_report(self, refresh=False):
        if self._short_report is not None and not self._refresh and not refresh:
            return self._short_report

        if self._refresh:
            self.grab_data()

        roster = self
        if len(roster.roster) == 0:
            return None
        if hasattr(roster, 'stages'):
            data = [[get_or_none(s, 'marker', None) for s in stage] for stage in roster._stages]
            cols = ['Stage 1 marker', 'Stage 3 marker', 'Stage 4 marker', 'Stage 5 marker', 'Stage 6 marker']
            c1 = {k: v for k, v in zip(cols, data)}
            df = pd.DataFrame(c1)
            df['student_id'] = roster.student_id['student_id']
        else:
            df = pd.DataFrame({'student_id': roster.student_id['student_id']})

        # add a string column containing roster.students['username']
        # nice usernames Student ID
        df['username'] = [f"Student {i}" for i in roster.student_id['student_id']] #roster.students['username'].values
        if 'name' in roster.students.columns:
            df['name'] = roster.students['name'].values
        df['class_id'] = roster.class_id
        completion_string, completion_percent = roster.fraction_completed()
        df['progress'] = completion_string
        df['percent_story_complete'] = completion_percent
        # df['percent_story_complete'] = df['percent_story_complete'].apply(lambda x: int(x))
        df['max_stage_index'] = roster.max_stage_index
        df['max_stage_marker'] = roster.max_stage_marker
        df['stage_index'] = roster.stage_index
        # df['total_score'] = roster.story_state['total_score']
        df['total_score'] = roster.student_scores
        df['out_of_possible'] = roster.out_of
        summ = roster.get_class_summary()
        df['Hubble_Constant'] = summ['H0'].apply(lambda x: round(x, 2))
        df['Age'] = summ['age'].apply(lambda x: round(x, 2))

        last_modified = pd.to_datetime(roster.last_modified['last_modified']).tz_convert('US/Eastern').strftime(
            "%Y-%m-%d %H:%M:%S (Eastern)")  # in Easterm time
        df['last_modified'] = last_modified

        self._short_report = df

        return df

    def refresh_data(self):
        """
        Refreshes all data for the roster
        
        
        """
        self._refresh = True
        logger.debug('****** Refreshing data ******')
        logger.debug(' >>> Grabbing class states')
        self.grab_data()
        logger.debug(' >>> Getting questions')
        self.question_keys()
        logger.debug(' >>> Getting class data')
        self.get_class_data()
        self._refresh = False

    def empty_copy(self):
        """
        Creates an empty copy of the roster with just the class ID
        
        
        """
        return Roster(class_id=self.class_id)



## create a cli so that will take the class_id as an argument, pass it to create report and export
# an excel fill called class_id_class_progress.xlsx

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Create a report for a class')
    parser.add_argument('class_id', type=int, help='The class id')
    # if there are multiple arguments given then loop over them
    args = parser.parse_args()

    if args.class_id is None:
        logger.debug('Please provide a class id')
        exit()

    roster = Roster(class_id = args.class_id)
    df = roster.report()#rgs.class_id)
    if df is None:
        logger.debug('No data found for class')
        exit()
    df.to_excel(f'{args.class_id}_class_progress.xlsx')

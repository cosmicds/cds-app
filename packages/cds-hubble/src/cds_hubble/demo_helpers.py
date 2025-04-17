from solara.toestand import Ref, Reactive
from cds_core.state import GlobalState
from .remote import LocalAPI
from .state import StudentMeasurement, LocalState

def set_dummy_wavelength(api: LocalAPI, local_state: Reactive[LocalState], global_state: Reactive[GlobalState]):
    dummy_measurements = api.get_dummy_data()
    measurements = []
    for measurement in dummy_measurements:
        measurements.append(StudentMeasurement(student_id=global_state.value.student.id,
                                                obs_wave_value=measurement.obs_wave_value,
                                                galaxy=measurement.galaxy))
    Ref(local_state.fields.measurements).set(measurements)
    

def set_dummy_wavelength_and_velocity(api: LocalAPI, local_state: Reactive[LocalState], global_state: Reactive[GlobalState]):
    dummy_measurements = api.get_dummy_data()
    measurements = []
    for measurement in dummy_measurements:
        measurements.append(StudentMeasurement(student_id=global_state.value.student.id,
                                                obs_wave_value=measurement.obs_wave_value,
                                                galaxy=measurement.galaxy,
                                                velocity_value=measurement.velocity_value))
    Ref(local_state.fields.measurements).set(measurements)


def set_dummy_wave_vel_ang(api: LocalAPI, local_state: Reactive[LocalState], global_state: Reactive[GlobalState]):
    dummy_measurements = api.get_dummy_data()
    measurements = []
    for measurement in dummy_measurements:
        measurements.append(StudentMeasurement(student_id=global_state.value.student.id,
                                                obs_wave_value=measurement.obs_wave_value,
                                                velocity_value=measurement.velocity_value,
                                                ang_size_value=measurement.ang_size_value,
                                                galaxy=measurement.galaxy))
    Ref(local_state.fields.measurements).set(measurements)
 
 
def set_dummy_angular_size_and_distance(api: LocalAPI, local_state: Reactive[LocalState], global_state: Reactive[GlobalState]):
    dummy_measurements = api.get_dummy_data()
    measurements = []
    for measurement in dummy_measurements:
        measurements.append(StudentMeasurement(student_id=global_state.value.student.id,
                                                ang_size_value=measurement.ang_size_value,
                                                galaxy=measurement.galaxy,
                                                est_dist_value=measurement.est_dist_value))
    Ref(local_state.fields.measurements).set(measurements)
    
def set_dummy_all_measurements(api: LocalAPI, local_state: Reactive[LocalState], global_state: Reactive[GlobalState]):
    dummy_measurements = api.get_dummy_data()
    for measurement in dummy_measurements:
        measurement.student_id = global_state.value.student.id
    Ref(local_state.fields.measurements).set(dummy_measurements)
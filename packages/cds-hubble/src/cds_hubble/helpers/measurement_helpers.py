from solara.toestand import Ref, Reactive
from cds_core.app_state import AppState
from ..remote import LocalAPI
from ..story_state import StudentMeasurement, StoryState
from ..utils import angular_size_for_velocity, distance_from_angular_size, observed_wavelength_from_redshift, rest_wavelength, velocity_from_wavelengths, w2v


def measurements_needed(local_state: StoryState) -> int:
    return max(5 - len(local_state.measurements), 0)


def add_wavelength(measurement: StudentMeasurement):
    galaxy = measurement.galaxy
    if (galaxy is None) or (measurement.obs_wave_value is not None):
        return

    rest = rest_wavelength(galaxy)
    lmb = observed_wavelength_from_redshift(galaxy.z, rest)
    measurement.obs_wave_value = lmb


def add_velocity(measurement: StudentMeasurement):
    galaxy = measurement.galaxy
    if (galaxy is None) or (measurement.velocity_value is not None):
        return

    if measurement.obs_wave_value is None:
        add_wavelength(measurement)
    measurement.velocity_value = w2v(measurement.obs_wave_value, rest_wavelength(galaxy))


def add_ang_size_value(measurement: StudentMeasurement):
    galaxy = measurement.galaxy
    if (galaxy is None) or (measurement.ang_size_value is not None):
        return

    velocity = measurement.velocity_value
    if not velocity:
        rest = rest_wavelength(galaxy)
        lmb = observed_wavelength_from_redshift(galaxy.z, rest)
        velocity = velocity_from_wavelengths(lmb, rest)
    measurement.ang_size_value = angular_size_for_velocity(velocity)


def add_distance(measurement: StudentMeasurement):
    galaxy = measurement.galaxy
    if (galaxy is None) or (measurement.est_dist_value is not None):
        return

    ang_size = measurement.ang_size_value
    if not ang_size:
        add_ang_size_value(measurement)
    measurement.est_dist_value = distance_from_angular_size(measurement.ang_size_value)


def fill_and_add_wavelengths(api: LocalAPI, local_state: Reactive[StoryState], global_state: Reactive[AppState]):
    measurements = [m for m in local_state.value.measurements]
    for measurement in measurements:
        add_wavelength(measurement)

    need = measurements_needed(local_state.value)
    dummy_measurements = api.get_dummy_data()[:need]
    for measurement in dummy_measurements:
        measurements.append(StudentMeasurement(student_id=global_state.value.student.id,
                                                obs_wave_value=measurement.obs_wave_value,
                                                galaxy=measurement.galaxy))
    Ref(local_state.fields.measurements).set(measurements)
    api.ignore_student(global_state.value.student.id)


def fill_and_add_velocities(api: LocalAPI, local_state: Reactive[StoryState], global_state: Reactive[AppState]):
    measurements = [m for m in local_state.value.measurements]
    for measurement in measurements:
        add_velocity(measurement)

    need = measurements_needed(local_state.value)
    dummy_measurements = api.get_dummy_data()[:need]
    for measurement in dummy_measurements:
        measurements.append(StudentMeasurement(student_id=global_state.value.student.id,
                                                obs_wave_value=measurement.obs_wave_value,
                                                galaxy=measurement.galaxy,
                                                velocity_value=measurement.velocity_value))
    Ref(local_state.fields.measurements).set(measurements)
    api.ignore_student(global_state.value.student.id)


def fill_add_wave_vel_ang(api: LocalAPI, local_state: Reactive[StoryState], global_state: Reactive[AppState]):
    measurements = [m for m in local_state.value.measurements]
    for measurement in measurements:
        add_velocity(measurement)
        add_ang_size_value(measurement)

    need = measurements_needed(local_state.value)
    dummy_measurements = api.get_dummy_data()[:need]
    for measurement in dummy_measurements:
        measurements.append(StudentMeasurement(student_id=global_state.value.student.id,
                                                obs_wave_value=measurement.obs_wave_value,
                                                velocity_value=measurement.velocity_value,
                                                ang_size_value=measurement.ang_size_value,
                                                galaxy=measurement.galaxy))
    Ref(local_state.fields.measurements).set(measurements)
    api.ignore_student(global_state.value.student.id)


def fill_add_angular_size_and_distance(api: LocalAPI, local_state: Reactive[StoryState], global_state: Reactive[AppState]):
    measurements = [m for m in local_state.value.measurements]
    for measurement in measurements:
        add_distance(measurement)

    need = measurements_needed(local_state.value)
    dummy_measurements = api.get_dummy_data()[:need]
    for measurement in dummy_measurements:
        measurements.append(StudentMeasurement(student_id=global_state.value.student.id,
                                                ang_size_value=measurement.ang_size_value,
                                                galaxy=measurement.galaxy,
                                                est_dist_value=measurement.est_dist_value))
    Ref(local_state.fields.measurements).set(measurements)
    api.ignore_student(global_state.value.student.id)


def fill_add_all_measurements(api: LocalAPI, local_state: Reactive[StoryState], global_state: Reactive[AppState]):
    measurements = [m for m in local_state.value.measurements]
    for measurement in measurements:
        add_velocity(measurement)
        add_distance(measurement)

    need = measurements_needed(local_state.value)
    dummy_measurements = api.get_dummy_data()[:need]
    for measurement in dummy_measurements:
        measurement.student_id = global_state.value.student.id
    Ref(local_state.fields.measurements).set(dummy_measurements)
    api.ignore_student(global_state.value.student.id)

STUDENT_MEASUREMENTS_LABEL = "student_measurements"
STUDENT_DATA_LABEL = "student_data"
CLASS_DATA_LABEL = "class_data"
ALL_DATA_LABEL = "all_measurements"
CLASS_SUMMARY_LABEL = "class_summary_data"
ALL_STUDENT_SUMMARIES_LABEL = "all_student_summaries"
ALL_CLASS_SUMMARIES_LABEL = "all_class_summaries"
SDSS_DATA_LABEL = "SDSS_all_sample_filtered"
SPECTRUM_DATA_LABEL = "spectrum_data"
HUBBLE_1929_DATA_LABEL = "Hubble 1929-Table 1"
HUBBLE_KEY_DATA_LABEL = "HSTkey2001"

BEST_FIT_SUBSET_LABEL = "best_fit_subset"
BEST_FIT_GALAXY_NAME = "Best Fit Galaxy"

EXAMPLE_GALAXY_SEED_DATA = "example_galaxy_seed_data"
EXAMPLE_GALAXY_DATA = "example_galaxy"
EXAMPLE_GALAXY_MEASUREMENTS = "example_galaxy_data"
EXAMPLE_GALAXY_STUDENT_DATA = "example_galaxy_student_data"
EXAMPLE_GALAXY_MEASUREMENTS_FIRST =  'first measurement'
EXAMPLE_GALAXY_MEASUREMENTS_SECOND = 'second measurement'
STUDENT_SLIDER_SUBSET_LABEL = "student_slider_subset"
CLASS_SLIDER_SUBSET_LABEL = "class_slider_subset"

### Data Components

# Measurements
MEASWAVE_COMPONENT = "measwave"
RESTWAVE_COMPONENT = "restwave"
VELOCITY_COMPONENT = "Velocity (km/s)"
DISTANCE_COMPONENT = "Distance (Mpc)"
ANGULAR_SIZE_COMPONENT = "angular_size"
NAME_COMPONENT = "name"
STUDENT_ID_COMPONENT = "student_id"
ELEMENT_COMPONENT = "element"
RA_COMPONENT = "ra"
DEC_COMPONENT = "decl"
Z_COMPONENT = "z"
GALTYPE_COMPONENT = "type"
BRIGHTNESS_COMPONENT = "brightness"

# Sample measurements
SAMPLE_ID_COMPONENT = "id"
MEASUREMENT_NUMBER_COMPONENT = "measurement_number"

# Summaries
CLASS_ID_COMPONENT = "class_id"
AGE_COMPONENT = "Age (Gyr)"
H0_COMPONENT = "H0"


### Database keys

# Measurements
DB_MEASWAVE_FIELD = "obs_wave_value"
DB_RESTWAVE_FIELD = "rest_wave_value"
DB_VELOCITY_FIELD = "velocity_value"
DB_DISTANCE_FIELD = "est_dist_value"
DB_ANGSIZE_FIELD = "ang_size_value"
DB_RA_FIELD = "ra"
DB_DEC_FIELD = "decl"
DB_NAME_FIELD = "name"
DB_Z_FIELD = "z"
DB_GALTYPE_FIELD = "type"
DB_ELEMENT_FIELD = "element"
DB_STUDENT_ID_FIELD = "student_id"
DB_LAST_MODIFIED_FIELD = "last_modified"
DB_BRIGHT_FIELD = "brightness"

DB_MEASNUM_FIELD = "measurement_number"

DB_GALNAME_FIELD = "galaxy_name"

DB_RESTWAVE_UNIT_FIELD = "rest_wave_unit"
DB_MEASWAVE_UNIT_FIELD = "obs_wave_unit"
DB_DISTANCE_UNIT_FIELD = "est_dist_unit"
DB_VELOCITY_UNIT_FIELD = "velocity_unit"
DB_ANGSIZE_UNIT_FIELD = "ang_size_unit"

DB_MEASUREMENT_FIELDS = [
    DB_MEASWAVE_FIELD,
    DB_RESTWAVE_FIELD,
    DB_VELOCITY_FIELD,
    DB_DISTANCE_FIELD,
    DB_ANGSIZE_FIELD,
    DB_RA_FIELD,
    DB_DEC_FIELD,
    DB_NAME_FIELD,
    DB_Z_FIELD,
    DB_GALTYPE_FIELD,
    DB_ELEMENT_FIELD,
    DB_STUDENT_ID_FIELD,
    DB_LAST_MODIFIED_FIELD,
]

DB_SAMPLE_MEASUREMENT_FIELDS = [DB_MEASNUM_FIELD, DB_BRIGHT_FIELD]

# Summaries
DB_H0_FIELD = "hubble_fit_value"
DB_AGE_FIELD = "age_value"

DB_SUMMARY_FIELDS = [DB_H0_FIELD, DB_AGE_FIELD]

# Misc
SPECTRUM_EXTENSION = ".fits"


def reverse(d):
    return {v: k for k, v in d.items()}


MEAS_TO_STATE = {
    MEASWAVE_COMPONENT: DB_MEASWAVE_FIELD,
    RESTWAVE_COMPONENT: DB_RESTWAVE_FIELD,
    VELOCITY_COMPONENT: DB_VELOCITY_FIELD,
    DISTANCE_COMPONENT: DB_DISTANCE_FIELD,
    NAME_COMPONENT: DB_GALNAME_FIELD,
    STUDENT_ID_COMPONENT: DB_STUDENT_ID_FIELD,
    ANGULAR_SIZE_COMPONENT: DB_ANGSIZE_FIELD,
}

STATE_TO_MEAS = reverse(MEAS_TO_STATE)

SUMM_TO_STATE = {H0_COMPONENT: DB_H0_FIELD, AGE_COMPONENT: DB_AGE_FIELD}

STATE_TO_SUMM = reverse(SUMM_TO_STATE)

UNITS_TO_STATE = {
    DB_RESTWAVE_UNIT_FIELD: "angstrom",
    DB_MEASWAVE_UNIT_FIELD: "angstrom",
    DB_DISTANCE_UNIT_FIELD: "Mpc",
    DB_VELOCITY_UNIT_FIELD: "km / s",
    DB_ANGSIZE_UNIT_FIELD: "arcsecond",
}


ELEMENT_REST = {"H-α": 6564.61, "Mg-I": 5176.7}
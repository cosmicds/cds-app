from collections import defaultdict
from astropy import units as u
from astropy.modeling import models, fitting
from numpy import argsort, array, pi

from cds_core.utils import component_type_for_field, mode, percent_around_center_indices
from pydantic import BaseModel

from glue.core import Data
from glue_jupyter.app import JupyterApplication
from numbers import Number
from typing import List, Set, Tuple, TypeVar, Optional, cast, Any
from collections.abc import Callable
import solara
from solara.routing import Router
from solara.toestand import Reactive
from solara.server import settings

from .story_state import GalaxyData, StudentMeasurement
from glue.core import Data
from numpy import asarray

from deepdiff import DeepDiff
from deepdiff.helper import NotPresent

from pathlib import Path

try:
    from astropy.cosmology import Planck18 as planck
except ImportError:
    from astropy.cosmology import Planck15 as planck

__all__ = [
    "HUBBLE_ROUTE_PATH",
    "MILKY_WAY_SIZE_MPC",
    "H_ALPHA_REST_LAMBDA",
    "MG_REST_LAMBDA",
    "GALAXY_FOV",
    "FULL_FOV",
    "angle_to_json",
    "angle_from_json",
    "age_in_gyr",
    "format_fov",
    "format_measured_angle",
]

HUBBLE_ROUTE_PATH = "hubbles_law"

MILKY_WAY_SIZE_LTYR = 100000 * u.lightyear
MILKY_WAY_SIZE_MPC = MILKY_WAY_SIZE_LTYR.to(u.Mpc).value
DISTANCE_CONSTANT = (
    round(MILKY_WAY_SIZE_MPC * 3600 * 180 / pi / 100) * 100
)  # theta = L/D:  Distance in Mpc = DISTANCE_CONSTANT / theta in arcsec; Round to hundreds to match slideshow notes.

AGE_CONSTANT = round(1.0e6 * u.pc.to(u.km) / (1e9 * u.yr.to(u.s)) / 10) * 10  # t = d/v
HST_KEY_AGE = 12.79687910  # (1/H_0) in Gyr

SPEED_OF_LIGHT = 3.0 * 10**5  # km/s
# Both in angstroms
H_ALPHA_REST_LAMBDA = 6565  # SDSS calibrates to wavelengths in a vacuum
MG_REST_LAMBDA = 5172  # The value used by SDSS is actually 5176.7, but that wavelength aligns with an upward bump, so we are adjusting it to 5172 to avoid confusing students. Ziegler & Bender 1997 uses lambda_0 ~ 5170, so our choice is justifiable.

GALAXY_FOV = 1.5 * u.arcmin
FULL_FOV = 60 * u.deg

PLOTLY_MARGINS = {"l": 60, "r": 20, "t": 20, "b": 60}

IMAGE_BASE_URL = "https://cosmicds.github.io/cds-website/hubbleds_images"

IMAGE_BASE_STATIC_PATH = "/static/public"


def get_image_path(router, sub_path):
    return f"{router.root_path}{IMAGE_BASE_STATIC_PATH}/{sub_path}"


def angle_to_json(angle, _widget):
    return {"value": angle.value, "unit": angle.unit.name}


def angle_from_json(jsn, _widget):
    return jsn["value"] * u.Unit(jsn["unit"])


def age_in_gyr(H0):
    """
    Given a value for the Hubble constant, computes the age of the universe
    in Gyr, based on the Planck cosmology.

    Parameters
    ----------
    H0: float
        The value of the Hubble constant

    Returns
    ----------
    age: numpy.float64
        The age of the universe, in Gyr
    """
    age = planck.clone(H0=H0).age(0)
    unit = age.unit
    return age.value * unit.to(u.Gyr)


def age_in_gyr_simple(H0):
    inv = 1 / H0
    mpc_to_km = u.Mpc.to(u.km)
    s_to_gyr = u.s.to(u.Gyr)
    return round(inv * mpc_to_km * s_to_gyr, 3)


def fit_line(x, y):
    try:
        fit = fitting.LinearLSQFitter()
        line_init = models.Linear1D(intercept=0, fixed={"intercept": True})
        fitted_line = fit(line_init, x, y)
        return fitted_line
    except ValueError as e:
        print(e)
        return None


def format_fov(fov, units=True):
    suffix = " (dd:mm:ss)" if units else ""
    return fov.to_string(unit=u.degree, sep=":", precision=0, pad=True) + suffix


def format_measured_angle(angle):
    if angle == 0:
        return ""
    return angle.to_string(unit=u.arcsec, precision=0)[:-6] + " arcseconds"


def velocity_from_wavelengths(lamb_meas, lamb_rest):
    return round((3 * (10**5) * (lamb_meas / lamb_rest - 1)), 0)


def w2v(lambda_meas, lamb_rest):
    return SPEED_OF_LIGHT * (lambda_meas / lamb_rest - 1)


def v2w(velocity, lamb_rest):
    return lamb_rest * (velocity / SPEED_OF_LIGHT + 1)


def distance_from_angular_size(theta):
    return round(DISTANCE_CONSTANT / theta, 0)


def data_summary_for_component(data, component_id):
    summary = {
        "mean": data.compute_statistic("mean", component_id),
        "median": data.compute_statistic("median", component_id),
        "mode": mode(data, component_id),
    }
    values = data[component_id]
    percents = [50, 68, 95]
    sorted_indices = argsort(values)

    for percent in percents:
        bottom_index, top_index = percent_around_center_indices(data.size, percent)
        bottom = values[sorted_indices[bottom_index]]
        top = values[sorted_indices[top_index]]
        summary[f"{percent}%"] = (bottom, top)

    return summary


def measurement_list_to_glue_data(
    measurements: list[StudentMeasurement] | list[dict], label=""
):
    x = []
    for measurement in measurements:
        if isinstance(measurement, StudentMeasurement):
            x.append(measurement.model_dump())
        else:
            x.append(measurement)
    return Data(label=label, **{k: asarray([r[k] for r in x]) for k in x[0].keys()})


M = TypeVar("M", bound=BaseModel)


def models_to_glue_data(
    items: List[M], label: str | None = None, ignore_components: list[str] | None = None
) -> Data:
    data_dict = {}
    if items:
        t = type(items[0])
        ignore = ignore_components or []
        for field, info in t.model_fields.items():
            if field not in ignore:
                component_type = component_type_for_field(info)
                data_dict[field] = component_type(
                    array([getattr(m, field) for m in items])
                )
    if label:
        data_dict["label"] = label
    return Data(**data_dict)


def create_single_summary(
    distances: List[Number], velocities: List[Number]
) -> Tuple[float, float]:
    line = fit_line(distances, velocities)
    h0 = line.slope.value
    age = age_in_gyr_simple(h0)
    return h0, age


def make_summary_data(
    measurement_data: Data,
    input_id_field: str = "id",
    output_id_field: str | None = None,
    label: str | None = None,
) -> Data:
    dists = defaultdict(list)
    vels = defaultdict(list)
    d = measurement_data["est_dist_value"]
    v = measurement_data["velocity_value"]
    ids: Set[int] = set()

    for i in range(measurement_data.size):
        id_num = measurement_data[input_id_field][i]
        ids.add(id_num)
        dist = d[i]
        vel = v[i]
        if dist is not None and vel is not None:
            dists[id_num].append(dist)
            vels[id_num].append(vel)

    hubbles: List[float] = []
    ages: List[float] = []
    for id_num in ids:
        h0, age = create_single_summary(dists[id_num], vels[id_num])
        hubbles.append(h0)
        ages.append(age)

    data_kwargs: dict = {"hubble_fit_value": hubbles, "age_value": ages}
    output_id_field = output_id_field or input_id_field
    data_kwargs[output_id_field] = list(ids)

    if label:
        data_kwargs["label"] = label

    return Data(**data_kwargs)


from typing import Generic

A = TypeVar("A", Any, Any)
B = TypeVar("B", Any, Any)


def sync_reactives(
    a: Reactive[A],
    b: Reactive[B],
    forward: Callable[[A], B] = lambda x: x,
    reverse: Callable[[B], A] = lambda x: x,
    after_a_synced: Optional[Callable[[Reactive[A]], None]] = None,
    after_b_synced: Optional[Callable[[Reactive[B]], None]] = None,
    prevent_sync: bool = True,
    prevent_sync_value=None,
):
    """
    Sync two reactive variables,
    with an optional transformation function between them.
    By default the transformation functions are the identity function.
    If you are syncing identical reactives, you may be doing something wrong.

    By default, the sync will not occur if the transformed value is None.

    a: Reactive
        The first reactive variable to sync.
    b: Reactive
        The second reactive variable to sync.

    forward [lambda x: x]: Optional, `function(a) -> b`
        A function that transforms from `a` to `b`.
        Default is the identity function.

    reverse [lambda x: x]: Optional, `function(b) -> a`
        A function that transforms from `b` to `a`.
        Default is the identity function.

    after_a_synced [None]: Optional, function(a) -> None
        Runs after `a` has been recieves a new value from `b`

    after_b_synced [None]: Optional, function(b) -> None
        Runs after `b` has been recieves a new value from `a`

    prevent_sync [True]: Optional, bool
        If True, the sync will not occur if the transformed value is `prevent_sync_value`

    prevent_sync_value [None]: Optional, Any.
        The value that will prevent sync if `prevent_sync` is True.
    """
    _equalish = lambda x, y: (x == y) or (x is y)  # np.nan requires 'is' -_-

    def on_a_changed(new: A):
        val = forward(new)
        if prevent_sync and _equalish(val, prevent_sync_value):
            return

        b.set(val)
        if after_b_synced:
            after_b_synced(b)

    def on_b_changed(new: B):
        val = reverse(new)
        if prevent_sync and _equalish(val, prevent_sync_value):
            return

        a.set(val)
        if after_a_synced:
            after_a_synced(a)

    a.subscribe(on_a_changed)
    b.subscribe(on_b_changed)


def _add_or_update_data(gjapp: JupyterApplication, data: Data):
    if data.label in gjapp.data_collection:
        existing = gjapp.data_collection[data.label]
        existing.update_values_from_data(data)
        return existing
    else:
        gjapp.data_collection.append(data)
        return data


from cds_core.utils import basic_link_exists


def _add_link(gjapp, from_dc_name, from_att, to_dc_name, to_att):
    if isinstance(from_dc_name, Data):
        from_dc = from_dc_name
    else:
        from_dc = gjapp.data_collection[from_dc_name]

    if isinstance(to_dc_name, Data):
        to_dc = to_dc_name
    else:
        to_dc = gjapp.data_collection[to_dc_name]
    if not basic_link_exists(
        gjapp.data_collection, from_dc.id[from_att], to_dc.id[to_att]
    ):
        gjapp.add_link(from_dc, from_att, to_dc, to_att)
    else:
        print(
            f"Link already exists between {from_dc.label} and {to_dc.label} for {from_att} and {to_att}"
        )


def subset_by_label(data, label):
    value = next((s for s in data.subsets if s.label == label), None)
    return value


def push_to_route(router: Router, location, route: str):
    if route != "/":
        path = Path(f"{router.root_path}/{route}")
        router.push(str(path))
    else:
        location.pathname = settings.main.base_url


def dict_diff(d1, d2, path=""):
    diffs = []

    keys = set(d1) | set(d2)
    for key in keys:
        key_path = f"{path}.{key}" if path else key

        if key not in d1:
            diffs.append(("added", key_path, d2[key]))
        elif key not in d2:
            diffs.append(("removed", key_path, d1[key]))
        else:
            v1, v2 = d1[key], d2[key]
            if isinstance(v1, dict) and isinstance(v2, dict):
                diffs.extend(dict_diff(v1, v2, path=key_path))
            elif v1 != v2:
                diffs.append(("changed", key_path, (v1, v2)))

    return diffs


def apply_changes(result, changes):
    for change in changes:
        path = change.path(output_format="list")
        value = change.t2
        if isinstance(value, NotPresent):
            value = None

        # Build nested dict structure
        current = result
        for key in path[:-1]:
            current = current.setdefault(key, {})

        current[path[-1]] = value


def extract_changed_subtree(old_dict, new_dict):
    diff = DeepDiff(old_dict, new_dict, view="tree")
    result = {}

    change_keys = [
        "values_changed",
        "iterable_item_added",
        "iterable_item_removed",
        "dictionary_item_added",
    ]

    for key in change_keys:
        if (changes := diff.get(key, None)) is not None:
            apply_changes(result, changes)

    return result


def observed_wavelength_from_redshift(z: float, rest_wavelength: float) -> float:
    return rest_wavelength * (1 + z)


def rest_wavelength(galaxy: GalaxyData) -> float:
    return MG_REST_LAMBDA if galaxy.element == "Mg-I" else H_ALPHA_REST_LAMBDA


def distance_for_velocity(velocity: float) -> float:
    return velocity / 70.85 # H0 = 70.85 km/s/Mpc for Age = 13.8 Gyr


def angular_size_for_velocity(velocity: float) -> float:
    return round(DISTANCE_CONSTANT / distance_for_velocity(velocity), 0)

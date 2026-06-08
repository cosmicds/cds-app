"""Top-level CDSClient and HubbleClient entry points."""

from .endpoints.classes import ClassesEndpoint
from .endpoints.educators import EducatorsEndpoint
from .endpoints.hubble.classes import HubbleClassesEndpoint
from .endpoints.hubble.galaxies import GalaxiesEndpoint
from .endpoints.hubble.measurements import MeasurementsEndpoint
from .endpoints.stories import StoriesEndpoint
from .endpoints.students import StudentsEndpoint
from .session import CDSSession

_HUBBLE_PREFIX = "/hubbles_law"


class HubbleClient:
    """Namespaced client for Hubble's Law story endpoints.

    Accessible via ``CDSClient.hubble``.
    """

    def __init__(self, session: CDSSession):
        hubble_session = session.with_prefix(_HUBBLE_PREFIX)
        self.measurements = MeasurementsEndpoint(hubble_session)
        self.galaxies = GalaxiesEndpoint(hubble_session)
        self.classes = HubbleClassesEndpoint(hubble_session)


class CDSClient:
    """Main entry point for the CosmicDS API.

    Parameters
    ----------
    api_key : str, optional
        API key sent as the ``Authorization`` header.  Defaults to the
        ``CDS_API_KEY`` environment variable.
    base_url : str, optional
        Override the default API base URL
        (``https://api.cosmicds.cfa.harvard.edu``).

    Examples
    --------
    >>> from cds_client import CDSClient
    >>> client = CDSClient()
    >>> student = client.students.get("abc123hash")
    >>> classes = client.classes.get_roster(class_id=5)
    >>> state = client.stories.get_story_state(student_id=7, story_name="hubbles_law")
    >>> galaxies = client.hubble.galaxies.get_all(types=["Sp"])
    >>> measurements = client.hubble.measurements.get(student_id=7)
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
    ):
        self._session = CDSSession(api_key=api_key, base_url=base_url)

        self.students = StudentsEndpoint(self._session)
        self.educators = EducatorsEndpoint(self._session)
        self.classes = ClassesEndpoint(self._session)
        self.stories = StoriesEndpoint(self._session)
        self.hubble = HubbleClient(self._session)

from ..session import CDSSession


class BaseEndpoint:
    def __init__(self, session: CDSSession):
        self._session = session

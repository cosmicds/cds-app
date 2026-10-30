from traitlets import Unicode

from ipywwt import WWTWidget


class HubbleWWTWidget(WWTWidget):

    background = Unicode(
        "Black Sky Background",
        help="The layer to show in the background (`str`)",
    ).tag(wwt=None, wwt_reset=True)

    foreground = Unicode(
        "SDSS 12",
        help="The layer to show in the foreground (`str`)",
    ).tag(wwt=None, wwt_reset=True)

    SURVEYS_URL = "https://gist.githubusercontent.com/Carifio24/447d69e14a3196665fa3cb59f93ec0ee/raw/1e7137802e6b6347f1b97c65fea3a5ce197be188/surveys_minimal.wtml"

    def __init__(self, *args, **kwargs):
        super().__init__(surveys_url=self.SURVEYS_URL, *args, **kwargs)

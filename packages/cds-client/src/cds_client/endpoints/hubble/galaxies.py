from contextlib import closing
from io import BytesIO

from ...exceptions import CDSNotFoundError
from ...models.hubble import Galaxy, SpectrumData
from ..base import BaseEndpoint


class GalaxiesEndpoint(BaseEndpoint):
    """Hubble's Law galaxy endpoints."""

    def get_all(
        self,
        types: list[str] | None = None,
        include_flags: bool = False,
    ) -> list[Galaxy]:
        """Return the galaxy catalog.

        Parameters
        ----------
        types : list of str, optional
            Filter by galaxy type codes (e.g. ``["Sp"]`` for spirals).
        include_flags : bool, optional
            Include bad-data flag fields in the response.
        """
        params: dict = {"flags": include_flags}
        if types:
            params["types"] = types
        data = self._session.get("/galaxies", params=params).json()
        return [Galaxy(**g) for g in data]

    def get_sample(self) -> Galaxy:
        """Return the designated sample (example) galaxy."""
        data = self._session.get("/sample-galaxy").json()
        return Galaxy(**data)

    def mark_bad(
        self,
        galaxy_id: int | None = None,
        galaxy_name: str | None = None,
    ) -> None:
        """Flag a galaxy's tileload as bad."""
        if galaxy_id is None and galaxy_name is None:
            raise ValueError("Provide either galaxy_id or galaxy_name.")
        payload = {}
        if galaxy_id is not None:
            payload["galaxy_id"] = galaxy_id
        if galaxy_name is not None:
            payload["galaxy_name"] = galaxy_name
        self._session.put("/mark-galaxy-bad", json=payload)

    def mark_spectrum_bad(
        self,
        galaxy_id: int | None = None,
        galaxy_name: str | None = None,
    ) -> None:
        """Flag a galaxy's spectrum as bad."""
        if galaxy_id is None and galaxy_name is None:
            raise ValueError("Provide either galaxy_id or galaxy_name.")
        payload = {}
        if galaxy_id is not None:
            payload["galaxy_id"] = galaxy_id
        if galaxy_name is not None:
            payload["galaxy_name"] = galaxy_name
        self._session.post("/mark-spectrum-bad", json=payload)

    def get_spectrum(self, galaxy_type: str, name: str) -> SpectrumData:
        """Download and parse a galaxy spectrum FITS file.

        Parameters
        ----------
        galaxy_type : str
            One of ``"spiral"``, ``"elliptical"``, or ``"irregular"``.
        name : str
            The FITS file name (with or without ``.fits`` extension).
        """
        try:
            from astropy.io import fits  # type: ignore[import]
        except ImportError as e:
            raise ImportError(
                "astropy is required to load spectrum data. "
                "Install it with: pip install astropy"
            ) from e

        file_name = name if name.endswith(".fits") else f"{name}.fits"
        response = self._session.get(f"/spectra/{galaxy_type}/{file_name}")

        with closing(BytesIO(response.content)) as f:
            f.name = file_name
            with fits.open(f) as hdulist:
                data = hdulist["COADD"].data if "COADD" in hdulist else None

        if data is None:
            raise ValueError(f"No 'COADD' extension found in spectrum for '{name}'.")

        return SpectrumData(
            name=name,
            wave=list(10 ** data["loglam"]),
            flux=list(data["flux"]),
            ivar=list(data["ivar"]),
        )

"""Download the consolidated DECP parquet file.

Dataset: "Données essentielles de la commande publique consolidées (format
tabulaire)" (producer: Colmo), published on data.gouv.fr:
https://www.data.gouv.fr/datasets/donnees-essentielles-de-la-commande-publique-consolidees-format-tabulaire

Licence: Licence Ouverte / Open Licence version 2.0 (Etalab), as declared
on that dataset page (``license: "lov2"`` in its data.gouv.fr metadata):
https://www.etalab.gouv.fr/licence-ouverte-open-licence

``DEFAULT_PARQUET_URL`` is the dataset's stable "latest resource" URL — it
always redirects to the current ``decp.parquet`` file, which the producer
refreshes about once a day. As checked on 2026-09-05, that file was ~235 MB.
"""

from __future__ import annotations

import shutil
import time
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import IO

DEFAULT_PARQUET_URL = "https://www.data.gouv.fr/api/1/datasets/r/11cea8e8-df3e-4ed1-932b-781e2635e432"

Opener = Callable[[str, float], IO[bytes]]


def _urlopen(url: str, timeout: float) -> IO[bytes]:
    return urllib.request.urlopen(url, timeout=timeout)  # noqa: S310 (fixed, non-user URL)


@dataclass(frozen=True)
class DownloadResult:
    path: Path
    bytes_downloaded: int
    elapsed_seconds: float


def download_parquet(
    destination: Path,
    url: str = DEFAULT_PARQUET_URL,
    *,
    timeout: float = 60.0,
    opener: Opener = _urlopen,
) -> DownloadResult:
    """Stream ``url`` to ``destination``, overwriting any existing file.

    Writes to a ``.part`` sibling file first and renames it on success, so a
    failed or interrupted download never leaves a corrupt file at
    ``destination``. ``opener`` is injectable so tests can exercise this
    without any real network call.
    """
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = destination.with_name(destination.name + ".part")

    start = time.perf_counter()
    with opener(url, timeout) as response, open(tmp_path, "wb") as out_file:
        shutil.copyfileobj(response, out_file, length=1024 * 1024)
    elapsed = time.perf_counter() - start

    tmp_path.replace(destination)
    return DownloadResult(
        path=destination,
        bytes_downloaded=destination.stat().st_size,
        elapsed_seconds=elapsed,
    )

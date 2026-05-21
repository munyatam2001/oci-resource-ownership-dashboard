"""Object Storage publishing interface stubs."""

from pathlib import Path
from typing import Optional


def upload_directory(
    source_dir: Path,
    bucket_name: str,
    namespace: Optional[str] = None,
) -> None:
    """Upload generated dashboard assets to Object Storage in a later phase."""

    raise NotImplementedError("Object Storage publishing is not implemented yet")

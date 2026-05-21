"""Object Storage publishing helpers."""

from pathlib import Path
from typing import Any, Iterable, Optional

from .auth import OciAuthContext
from .html_report import HTML_FILENAME


def _object_name(path: Path, object_prefix: Optional[str]) -> str:
    prefix = (object_prefix or "").strip("/")
    if prefix:
        return f"{prefix}/{path.name}"
    return path.name


def _files_to_upload(files: Iterable[Path], upload_html_only: bool) -> list[Path]:
    selected = [Path(file_path) for file_path in files]
    if upload_html_only:
        selected = [file_path for file_path in selected if file_path.name == HTML_FILENAME]
    return selected


def _client(auth_context: OciAuthContext, object_storage_client: Optional[Any] = None) -> Any:
    if object_storage_client is not None:
        return object_storage_client
    try:
        import oci
    except ImportError as exc:
        raise RuntimeError("The OCI SDK is required for Object Storage upload.") from exc
    return oci.object_storage.ObjectStorageClient(
        auth_context.config,
        signer=auth_context.signer,
    )


def upload_generated_files(
    auth_context: OciAuthContext,
    files: Iterable[Path],
    bucket_name: str,
    namespace: str,
    object_prefix: Optional[str] = None,
    upload_html_only: bool = False,
    object_storage_client: Optional[Any] = None,
) -> list[str]:
    """Upload generated report files and return uploaded object names."""

    client = _client(auth_context, object_storage_client)
    uploaded: list[str] = []

    for file_path in _files_to_upload(files, upload_html_only):
        object_name = _object_name(file_path, object_prefix)
        with file_path.open("rb") as content:
            client.put_object(
                namespace,
                bucket_name,
                object_name,
                content,
            )
        uploaded.append(object_name)

    return uploaded


def upload_directory(
    auth_context: OciAuthContext,
    source_dir: Path,
    bucket_name: str,
    namespace: str,
    object_prefix: Optional[str] = None,
    upload_html_only: bool = False,
    object_storage_client: Optional[Any] = None,
) -> list[str]:
    """Upload generated files from a directory."""

    files = sorted(path for path in source_dir.iterdir() if path.is_file())
    return upload_generated_files(
        auth_context=auth_context,
        files=files,
        bucket_name=bucket_name,
        namespace=namespace,
        object_prefix=object_prefix,
        upload_html_only=upload_html_only,
        object_storage_client=object_storage_client,
    )

from oci_resource_dashboard.auth import OciAuthContext
from oci_resource_dashboard.html_report import HTML_FILENAME
from oci_resource_dashboard.object_storage import upload_generated_files


class FakeObjectStorageClient:
    def __init__(self):
        self.uploads = []

    def put_object(self, namespace, bucket_name, object_name, content):
        self.uploads.append(
            {
                "namespace": namespace,
                "bucket_name": bucket_name,
                "object_name": object_name,
                "content": content.read(),
            }
        )


def _write_file(path, content):
    path.write_text(content, encoding="utf-8")
    return path


def test_upload_all_files(tmp_path):
    html = _write_file(tmp_path / HTML_FILENAME, "<html></html>")
    csv_file = _write_file(tmp_path / "oci_resources_with_tags.csv", "header\n")
    client = FakeObjectStorageClient()

    uploaded = upload_generated_files(
        auth_context=OciAuthContext(config={}),
        files=[csv_file, html],
        bucket_name="reports",
        namespace="ns",
        object_storage_client=client,
    )

    assert uploaded == ["oci_resources_with_tags.csv", HTML_FILENAME]
    assert [upload["object_name"] for upload in client.uploads] == uploaded
    assert client.uploads[0]["bucket_name"] == "reports"
    assert client.uploads[0]["namespace"] == "ns"


def test_upload_html_only(tmp_path):
    html = _write_file(tmp_path / HTML_FILENAME, "<html></html>")
    csv_file = _write_file(tmp_path / "oci_resources_with_tags.csv", "header\n")
    client = FakeObjectStorageClient()

    uploaded = upload_generated_files(
        auth_context=OciAuthContext(config={}),
        files=[csv_file, html],
        bucket_name="reports",
        namespace="ns",
        upload_html_only=True,
        object_storage_client=client,
    )

    assert uploaded == [HTML_FILENAME]
    assert [upload["object_name"] for upload in client.uploads] == [HTML_FILENAME]


def test_object_prefix_handling(tmp_path):
    html = _write_file(tmp_path / HTML_FILENAME, "<html></html>")
    client = FakeObjectStorageClient()

    uploaded = upload_generated_files(
        auth_context=OciAuthContext(config={}),
        files=[html],
        bucket_name="reports",
        namespace="ns",
        object_prefix="/dashboards/prod/",
        object_storage_client=client,
    )

    assert uploaded == [f"dashboards/prod/{HTML_FILENAME}"]
    assert client.uploads[0]["object_name"] == f"dashboards/prod/{HTML_FILENAME}"

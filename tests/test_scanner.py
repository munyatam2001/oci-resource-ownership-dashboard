import csv
from pathlib import Path
from types import SimpleNamespace

import pytest

from oci_resource_dashboard.auth import OciAuthContext
from oci_resource_dashboard.compartments import CompartmentDiscoveryResult
from oci_resource_dashboard.resource_search import sample_resources
from oci_resource_dashboard.scanner import (
    scan_resources,
    scan_summary_rows,
    validate_upload_options,
)


CONFIG_PATH = Path("config/mandatory_tags.example.yaml")


class FakeConsole:
    def __init__(self):
        self.messages = []

    def print(self, message):
        self.messages.append(str(message))


def _read_csv(path):
    with path.open("r", encoding="utf-8", newline="") as csv_file:
        return list(csv.DictReader(csv_file))


def test_max_resource_limiting_in_sample_mode(tmp_path):
    result = scan_resources(
        auth_method="instance_principal",
        region="us-ashburn-1",
        compartment_id="ocid1.compartment.oc1..root",
        include_subcompartments=True,
        mandatory_tags_path=CONFIG_PATH,
        output_dir=tmp_path,
        sample=True,
        max_resources=2,
        console=FakeConsole(),
    )

    assert result.total_resources_discovered == 5
    assert result.resources_processed == 2
    rows = _read_csv(tmp_path / "oci_resources_with_tags.csv")
    assert len(rows) == 2


def test_sample_mode_generates_all_csvs_and_html(tmp_path):
    result = scan_resources(
        auth_method="instance_principal",
        region="us-ashburn-1",
        compartment_id="ocid1.compartment.oc1..root",
        include_subcompartments=False,
        mandatory_tags_path=CONFIG_PATH,
        output_dir=tmp_path,
        sample=True,
        console=FakeConsole(),
    )

    generated_names = {path.name for path in result.generated_files}

    assert generated_names == {
        "oci_resources_with_tags.csv",
        "oci_resources_missing_mandatory_tags.csv",
        "oci_tag_compliance_summary.csv",
        "oci_tag_compliance_by_owner.csv",
        "oci_tag_compliance_by_compartment.csv",
        "oci_tag_key_usage.csv",
        "oci_tag_mapping_hints.csv",
        "oci_ownership_coverage_summary.csv",
        "oci_owner_backfill_recommendations.csv",
        "oci_resource_ownership_dashboard.html",
    }


def test_max_resource_limiting_in_live_mode_using_mocks(monkeypatch, tmp_path):
    class FakeCompartmentDiscovery:
        def __init__(self, auth_context):
            self.auth_context = auth_context

        def discover_compartments(self, compartment_id, include_subcompartments):
            return CompartmentDiscoveryResult(
                compartment_ids=["root"],
                compartment_id_to_name={"root": "Root"},
            )

    class FakeResourceSearch:
        def __init__(self, auth_context, compartment_id_to_name):
            self.auth_context = auth_context
            self.compartment_id_to_name = compartment_id_to_name

        def search_resources(self, compartment_ids, resource_query=None):
            return sample_resources()[:4]

    monkeypatch.setattr(
        "oci_resource_dashboard.scanner.build_auth_context",
        lambda settings: OciAuthContext(config={"region": "us-ashburn-1"}),
    )
    monkeypatch.setattr(
        "oci_resource_dashboard.scanner.OciCompartmentDiscovery",
        FakeCompartmentDiscovery,
    )
    monkeypatch.setattr(
        "oci_resource_dashboard.scanner.OciResourceSearch",
        FakeResourceSearch,
    )

    result = scan_resources(
        auth_method="instance_principal",
        region="us-ashburn-1",
        compartment_id="root",
        include_subcompartments=False,
        mandatory_tags_path=CONFIG_PATH,
        output_dir=tmp_path,
        max_resources=3,
        console=FakeConsole(),
    )

    assert result.mode == "live OCI"
    assert result.total_resources_discovered == 4
    assert result.resources_processed == 3
    rows = _read_csv(tmp_path / "oci_resources_with_tags.csv")
    assert len(rows) == 3


def test_invalid_max_resources_value(tmp_path):
    with pytest.raises(ValueError, match="greater than zero"):
        scan_resources(
            auth_method="instance_principal",
            region="us-ashburn-1",
            compartment_id="root",
            include_subcompartments=False,
            mandatory_tags_path=CONFIG_PATH,
            output_dir=tmp_path,
            sample=True,
            max_resources=0,
        )


def test_upload_validation_requires_bucket_name():
    with pytest.raises(ValueError, match="bucket-name"):
        validate_upload_options(upload=True, bucket_name=None, namespace="ns")


def test_upload_validation_requires_namespace():
    with pytest.raises(ValueError, match="namespace"):
        validate_upload_options(upload=True, bucket_name="reports", namespace=None)


def test_resource_query_propagates_into_resource_search(monkeypatch, tmp_path):
    captured = SimpleNamespace(query=None)

    class FakeCompartmentDiscovery:
        def __init__(self, auth_context):
            pass

        def discover_compartments(self, compartment_id, include_subcompartments):
            return CompartmentDiscoveryResult(
                compartment_ids=["root"],
                compartment_id_to_name={"root": "Root"},
            )

    class FakeResourceSearch:
        def __init__(self, auth_context, compartment_id_to_name):
            pass

        def search_resources(self, compartment_ids, resource_query=None):
            captured.query = resource_query
            return []

    monkeypatch.setattr(
        "oci_resource_dashboard.scanner.build_auth_context",
        lambda settings: OciAuthContext(config={"region": "us-ashburn-1"}),
    )
    monkeypatch.setattr(
        "oci_resource_dashboard.scanner.OciCompartmentDiscovery",
        FakeCompartmentDiscovery,
    )
    monkeypatch.setattr(
        "oci_resource_dashboard.scanner.OciResourceSearch",
        FakeResourceSearch,
    )

    scan_resources(
        auth_method="instance_principal",
        region="us-ashburn-1",
        compartment_id="root",
        include_subcompartments=False,
        mandatory_tags_path=CONFIG_PATH,
        output_dir=tmp_path,
        resource_query="query bucket resources",
        console=FakeConsole(),
    )

    assert captured.query == "query bucket resources"


def test_generated_summary_includes_resources_processed(tmp_path):
    result = scan_resources(
        auth_method="instance_principal",
        region="us-ashburn-1",
        compartment_id="root",
        include_subcompartments=False,
        mandatory_tags_path=CONFIG_PATH,
        output_dir=tmp_path,
        sample=True,
        max_resources=1,
        console=FakeConsole(),
    )

    rows = dict(scan_summary_rows(result))

    assert rows["Resources Processed"] == "1"
    assert rows["Max Resources Limit"] == "1"


def test_tag_diagnostics_still_work_when_max_resources_is_used(tmp_path):
    scan_resources(
        auth_method="instance_principal",
        region="us-ashburn-1",
        compartment_id="root",
        include_subcompartments=False,
        mandatory_tags_path=CONFIG_PATH,
        output_dir=tmp_path,
        sample=True,
        max_resources=1,
        console=FakeConsole(),
    )

    usage_rows = _read_csv(tmp_path / "oci_tag_key_usage.csv")
    keys = {row["tag_key"] for row in usage_rows}

    assert "Owner" in keys
    assert "Oracle-Tags.CreatedBy" in keys
    assert "Oracle-Tags.CreatedOn" in keys
    assert "created_by" not in keys


def test_upload_scan_outputs_reuses_existing_auth_context(monkeypatch, tmp_path):
    from oci_resource_dashboard.scanner import ScanResult, upload_scan_outputs

    uploaded_contexts = []

    def fake_upload_generated_files(
        auth_context,
        files,
        bucket_name,
        namespace,
        object_prefix=None,
        upload_html_only=False,
    ):
        uploaded_contexts.append(auth_context)
        return ["dashboard/index.html"]

    monkeypatch.setattr(
        "oci_resource_dashboard.scanner.upload_generated_files",
        fake_upload_generated_files,
    )

    auth_context = OciAuthContext(config={"region": "us-ashburn-1"})
    result = ScanResult(
        mode="live OCI",
        compartments_selected=1,
        total_resources_discovered=0,
        resources_processed=0,
        max_resources=None,
        resource_query="query all resources",
        elapsed_seconds=0.1,
        generated_files=[],
        auth_context=auth_context,
    )

    uploaded = upload_scan_outputs(
        result=result,
        auth_method="instance_principal",
        region="us-ashburn-1",
        bucket_name="reports",
        namespace="ns",
        object_prefix="dashboard",
        upload_html_only=True,
        console=FakeConsole(),
    )

    assert uploaded == ["dashboard/index.html"]
    assert uploaded_contexts == [auth_context]

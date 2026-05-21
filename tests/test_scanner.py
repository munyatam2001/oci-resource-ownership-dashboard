import csv
from pathlib import Path
from types import SimpleNamespace

import pytest

from oci_resource_dashboard.auth import OciAuthContext
from oci_resource_dashboard.compartments import CompartmentDiscoveryResult
from oci_resource_dashboard.resource_search import sample_resources
from oci_resource_dashboard.scanner import scan_resources, scan_summary_rows


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
    assert "Operations.CreatedBy" in keys
    assert "created_by" not in keys

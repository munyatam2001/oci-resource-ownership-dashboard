import csv

from oci_resource_dashboard.compliance import load_mandatory_tags
from oci_resource_dashboard.csv_report import INVENTORY_HEADERS, write_csv_outputs
from oci_resource_dashboard.resource_search import sample_resources


def _read_csv(path):
    with path.open("r", encoding="utf-8", newline="") as csv_file:
        return list(csv.DictReader(csv_file))


def test_inventory_csv_headers(tmp_path):
    tags = load_mandatory_tags("config/mandatory_tags.example.yaml")
    write_csv_outputs(sample_resources(), tags, tmp_path)

    with (tmp_path / "oci_resources_with_tags.csv").open(
        "r", encoding="utf-8", newline=""
    ) as csv_file:
        reader = csv.reader(csv_file)
        headers = next(reader)

    assert headers == INVENTORY_HEADERS


def test_missing_tags_csv_only_includes_noncompliant_resources(tmp_path):
    tags = load_mandatory_tags("config/mandatory_tags.example.yaml")
    write_csv_outputs(sample_resources(), tags, tmp_path)

    rows = _read_csv(tmp_path / "oci_resources_missing_mandatory_tags.csv")

    assert len(rows) == 3
    assert {row["resource_name"] for row in rows} == {
        "prod-app-subnet",
        "audit-log-bucket",
        "legacy-vcn",
    }
    assert all(row["is_compliant"] == "false" for row in rows)


def test_summary_csv_contains_expected_totals(tmp_path):
    tags = load_mandatory_tags("config/mandatory_tags.example.yaml")
    write_csv_outputs(sample_resources(), tags, tmp_path)

    rows = _read_csv(tmp_path / "oci_tag_compliance_summary.csv")

    assert rows == [
        {
            "total_resources": "5",
            "compliant_resources": "2",
            "noncompliant_resources": "3",
            "compliance_percent": "40.0",
        }
    ]


def test_owner_grouping_handles_missing_owner_as_unknown(tmp_path):
    tags = load_mandatory_tags("config/mandatory_tags.example.yaml")
    write_csv_outputs(sample_resources(), tags, tmp_path)

    rows = _read_csv(tmp_path / "oci_tag_compliance_by_owner.csv")
    by_group = {row["group"]: row for row in rows}

    assert by_group["Unknown"]["total_resources"] == "2"
    assert by_group["Unknown"]["compliant_resources"] == "0"
    assert by_group["Unknown"]["noncompliant_resources"] == "2"


def test_compartment_grouping_handles_missing_owner_as_unknown(tmp_path):
    tags = load_mandatory_tags("config/mandatory_tags.example.yaml")
    resources = sample_resources()
    resources[0] = dict(resources[0], compartment_name="")
    write_csv_outputs(resources, tags, tmp_path)

    rows = _read_csv(tmp_path / "oci_tag_compliance_by_compartment.csv")
    by_group = {row["group"]: row for row in rows}

    assert by_group["Unknown"]["total_resources"] == "1"


def test_tag_diagnostic_csvs_are_written(tmp_path):
    tags = load_mandatory_tags("config/mandatory_tags.example.yaml")
    paths = write_csv_outputs(sample_resources(), tags, tmp_path)

    assert tmp_path / "oci_tag_key_usage.csv" in paths
    assert tmp_path / "oci_tag_mapping_hints.csv" in paths

    usage_rows = _read_csv(tmp_path / "oci_tag_key_usage.csv")
    hint_rows = _read_csv(tmp_path / "oci_tag_mapping_hints.csv")

    assert any(row["tag_key"] == "Owner" for row in usage_rows)
    assert any(row["mandatory_tag"] == "Owner" for row in hint_rows)

from pathlib import Path

from oci_resource_dashboard.compliance import load_mandatory_tags


def test_loads_mandatory_tags_from_example_config():
    tags = load_mandatory_tags(Path("config/mandatory_tags.example.yaml"))

    assert [tag.canonical_name for tag in tags] == [
        "CreatedBy",
        "Owner",
        "CostCenter",
        "Environment",
        "Application",
    ]
    assert tags[0].defined_tag_namespace == "Operations"
    assert "created_by" in tags[0].aliases

from oci_resource_dashboard.models import MandatoryTag
from oci_resource_dashboard.tag_extractors import (
    extract_defined_tag,
    extract_freeform_tag,
    extract_mandatory_tag_value,
)


def test_extracts_tag_value_from_freeform_tags():
    tags = {"owner": "platform-team", "environment": "prod"}

    assert extract_freeform_tag(tags, "owner") == "platform-team"


def test_missing_freeform_tag_returns_none():
    assert extract_freeform_tag({"owner": ""}, "owner") is None
    assert extract_freeform_tag({}, "owner") is None


def test_extracts_tag_value_from_defined_tags():
    tags = {"Finance": {"CostCenter": "CC-1234"}}

    assert extract_defined_tag(tags, "Finance", "CostCenter") == "CC-1234"


def test_extracts_mandatory_defined_tag_value():
    mandatory_tag = MandatoryTag(
        name="cost_center",
        source="defined",
        namespace="Finance",
        key="CostCenter",
    )

    assert (
        extract_mandatory_tag_value({}, {"Finance": {"CostCenter": "CC-1234"}}, mandatory_tag)
        == "CC-1234"
    )

from oci_resource_dashboard.compliance import evaluate_resource, missing_mandatory_tags
from oci_resource_dashboard.models import MandatoryTag, ResourceRecord


def test_detects_missing_mandatory_tags():
    resource = ResourceRecord(
        identifier="ocid1.instance.oc1..example",
        display_name="app-server-1",
        resource_type="instance",
        compartment_id="ocid1.compartment.oc1..example",
        freeform_tags={"owner": "platform-team"},
        defined_tags={},
    )
    mandatory_tags = [
        MandatoryTag(name="owner", source="freeform"),
        MandatoryTag(
            name="cost_center",
            source="defined",
            namespace="Finance",
            key="CostCenter",
        ),
    ]

    missing = missing_mandatory_tags(resource, mandatory_tags)

    assert [tag.name for tag in missing] == ["cost_center"]


def test_compliance_result_is_compliant_when_all_tags_present():
    resource = ResourceRecord(
        identifier="ocid1.bucket.oc1..example",
        display_name="logs",
        resource_type="bucket",
        compartment_id="ocid1.compartment.oc1..example",
        freeform_tags={"owner": "security-team"},
        defined_tags={"Finance": {"CostCenter": "CC-5678"}},
    )
    mandatory_tags = [
        MandatoryTag(name="owner", source="freeform"),
        MandatoryTag(
            name="cost_center",
            source="defined",
            namespace="Finance",
            key="CostCenter",
        ),
    ]

    result = evaluate_resource(resource, mandatory_tags)

    assert result.is_compliant
    assert result.missing_tags == ()

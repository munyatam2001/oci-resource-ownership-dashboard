from oci_resource_dashboard.compliance import (
    evaluate_resource_compliance,
    missing_mandatory_tags,
    summarize_compliance,
)
from oci_resource_dashboard.models import MandatoryTag


MANDATORY_TAGS = [
    MandatoryTag(
        canonical_name="CreatedBy",
        defined_tag_namespace="Operations",
        defined_tag_key="CreatedBy",
        aliases=("created_by", "creator"),
    ),
    MandatoryTag(
        canonical_name="Owner",
        defined_tag_namespace="Operations",
        defined_tag_key="Owner",
        aliases=("owner",),
    ),
    MandatoryTag(
        canonical_name="CostCenter",
        defined_tag_namespace="Finance",
        defined_tag_key="CostCenter",
        aliases=("cost_center", "cc"),
    ),
    MandatoryTag(
        canonical_name="Environment",
        defined_tag_namespace="Operations",
        defined_tag_key="Environment",
        aliases=("env",),
    ),
    MandatoryTag(
        canonical_name="Application",
        defined_tag_namespace="Operations",
        defined_tag_key="Application",
        aliases=("app",),
    ),
]


def test_evaluate_resource_compliance_with_realistic_oci_tags():
    resource = {
        "id": "ocid1.instance.oc1..example",
        "display_name": "app-server-1",
        "defined_tags": {
            "Operations": {"CreatedBy": "alice@example.com", "Application": "billing"},
            "Finance": {"CostCenter": "CC-1234"},
        },
        "freeform_tags": {"Owner": "platform-team", "env": "prod"},
    }

    result = evaluate_resource_compliance(resource, MANDATORY_TAGS)

    assert result.is_compliant
    assert result.compliance_percent == 100.0
    assert result.present_tags == {
        "CreatedBy": "alice@example.com",
        "Owner": "platform-team",
        "CostCenter": "CC-1234",
        "Environment": "prod",
        "Application": "billing",
    }
    assert result.missing_tags == ()


def test_detects_resource_missing_cost_center():
    resource = {
        "defined_tags": {"Operations": {"CreatedBy": "alice@example.com"}},
        "freeform_tags": {"Owner": "platform-team", "env": "prod", "app": "billing"},
    }

    result = evaluate_resource_compliance(resource, MANDATORY_TAGS)

    assert result.compliance_percent == 80.0
    assert result.missing_tags == ("CostCenter",)


def test_resource_with_no_tags_is_noncompliant():
    result = evaluate_resource_compliance({}, MANDATORY_TAGS)

    assert not result.is_compliant
    assert result.compliance_percent == 0.0
    assert result.missing_tags == (
        "CreatedBy",
        "Owner",
        "CostCenter",
        "Environment",
        "Application",
    )


def test_resource_with_blank_tag_values_is_noncompliant_for_blank_tags():
    resource = {
        "defined_tags": {"Operations": {"CreatedBy": " ", "Application": "orders"}},
        "freeform_tags": {"Owner": "", "cost_center": "CC-1234", "env": "prod"},
    }

    result = evaluate_resource_compliance(resource, MANDATORY_TAGS)

    assert result.missing_tags == ("CreatedBy", "Owner")
    assert result.compliance_percent == 60.0


def test_missing_mandatory_tags_returns_canonical_names():
    resource = {"freeform_tags": {"owner": "security-team"}}

    assert missing_mandatory_tags(resource, MANDATORY_TAGS) == (
        "CreatedBy",
        "CostCenter",
        "Environment",
        "Application",
    )


def test_summarize_compliance_counts_present_and_missing_tags():
    resources = [
        {
            "defined_tags": {
                "Operations": {"CreatedBy": "alice@example.com", "Application": "billing"},
                "Finance": {"CostCenter": "CC-1234"},
            },
            "freeform_tags": {"Owner": "platform-team", "env": "prod"},
        },
        {
            "defined_tags": {"Operations": {"CreatedBy": "bob@example.com"}},
            "freeform_tags": {"Owner": "security-team", "env": "test", "app": "iam"},
        },
        {},
    ]

    summary = summarize_compliance(resources, MANDATORY_TAGS)

    assert summary.total_resources == 3
    assert summary.compliant_resources == 1
    assert summary.noncompliant_resources == 2
    assert summary.compliance_percent == 33.33
    assert summary.missing_count_by_tag == {
        "CreatedBy": 1,
        "Owner": 1,
        "CostCenter": 2,
        "Environment": 1,
        "Application": 1,
    }
    assert summary.present_count_by_tag == {
        "CreatedBy": 2,
        "Owner": 2,
        "CostCenter": 1,
        "Environment": 2,
        "Application": 2,
    }

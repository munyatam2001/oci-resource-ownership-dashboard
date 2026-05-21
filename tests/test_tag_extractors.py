from oci_resource_dashboard.models import MandatoryTag
from oci_resource_dashboard.tag_extractors import (
    extract_no_shutdown,
    extract_oracle_created_on,
    extract_defined_tag,
    extract_freeform_tag,
    extract_tag_value,
)


CREATED_BY = MandatoryTag(
    canonical_name="CreatedBy",
    defined_tag_namespace="Operations",
    defined_tag_key="CreatedBy",
    aliases=("created_by", "creator"),
)
OWNER = MandatoryTag(
    canonical_name="Owner",
    defined_tag_namespace="Operations",
    defined_tag_key="Owner",
    aliases=("owner", "resource_owner"),
)
ENVIRONMENT = MandatoryTag(
    canonical_name="Environment",
    defined_tag_namespace="Operations",
    defined_tag_key="Environment",
    aliases=("env", "stage"),
)


def test_extracts_tag_value_from_defined_tags_first():
    resource = {
        "defined_tags": {"Operations": {"CreatedBy": "alice@example.com"}},
        "freeform_tags": {"CreatedBy": "fallback@example.com"},
    }

    assert extract_tag_value(resource, CREATED_BY) == "alice@example.com"


def test_extracts_tag_value_from_freeform_canonical_name():
    resource = {"freeform_tags": {"Owner": "platform-team"}}

    assert extract_tag_value(resource, OWNER) == "platform-team"


def test_extracts_tag_value_from_freeform_alias():
    resource = {"freeform_tags": {"env": "prod"}}

    assert extract_tag_value(resource, ENVIRONMENT) == "prod"


def test_extracts_tag_value_from_flattened_defined_alias():
    resource = {"freeform_tags": {"Operations.CreatedBy": "bob@example.com"}}

    assert extract_tag_value(resource, CREATED_BY) == "bob@example.com"


def test_oracle_tags_created_by_defined_tag_is_created_by_alias():
    resource = {
        "defined_tags": {
            "Oracle-Tags": {"CreatedBy": "oracleidentitycloudservice/alice@example.com"}
        }
    }
    tag = MandatoryTag(
        canonical_name="CreatedBy",
        defined_tag_namespace="Operations",
        defined_tag_key="CreatedBy",
        aliases=("Oracle-Tags.CreatedBy",),
    )

    assert extract_tag_value(resource, tag) == "oracleidentitycloudservice/alice@example.com"


def test_extracts_oracle_created_on_metadata():
    resource = {"defined_tags": {"Oracle-Tags": {"CreatedOn": "2026-05-21T10:00:00Z"}}}

    assert extract_oracle_created_on(resource) == "2026-05-21T10:00:00Z"


def test_extracts_no_shutdown_metadata():
    resource = {"freeform_tags": {"NoShutDown": "Yes"}}

    assert extract_no_shutdown(resource) == "Yes"


def test_extracts_case_insensitive_freeform_tag_keys():
    resource = {"freeform_tags": {"owner": "security-team"}}

    assert extract_tag_value(resource, OWNER) == "security-team"


def test_blank_tag_values_return_none():
    resource = {
        "defined_tags": {"Operations": {"CreatedBy": "   "}},
        "freeform_tags": {"CreatedBy": ""},
    }

    assert extract_tag_value(resource, CREATED_BY) is None


def test_missing_or_malformed_tags_return_none():
    assert extract_tag_value({"freeform_tags": None, "defined_tags": None}, OWNER) is None
    assert extract_tag_value({"freeform_tags": [], "defined_tags": []}, OWNER) is None


def test_low_level_extractors_still_handle_direct_tag_dicts():
    assert extract_freeform_tag({"Owner": "platform-team"}, "Owner") == "platform-team"
    assert extract_defined_tag({"Finance": {"CostCenter": "CC-1234"}}, "Finance", "CostCenter") == "CC-1234"

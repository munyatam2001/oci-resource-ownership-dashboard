from oci_resource_dashboard.compliance import load_mandatory_tags
from oci_resource_dashboard.owner_backfill import (
    RECOMMENDATION_REASON,
    SUGGESTED_ACTION,
    owner_backfill_rows,
)


def test_owner_backfill_includes_only_created_by_present_owner_missing():
    tags = load_mandatory_tags("config/mandatory_tags.example.yaml")
    resources = [
        {
            "resource_name": "needs-owner",
            "resource_id": "ocid1.instance.oc1..needsowner",
            "resource_type": "Instance",
            "compartment_name": "App",
            "region": "us-ashburn-1",
            "lifecycle_state": "RUNNING",
            "defined_tags": {"Oracle-Tags": {"CreatedBy": "alice", "CreatedOn": "2026-05-01"}},
            "freeform_tags": {"NoShutDown": "Yes"},
        },
        {
            "resource_name": "missing-both",
            "defined_tags": {},
            "freeform_tags": {},
        },
        {
            "resource_name": "has-owner",
            "defined_tags": {"Oracle-Tags": {"CreatedBy": "bob"}},
            "freeform_tags": {"Owner": "team-a"},
        },
    ]

    rows = owner_backfill_rows(resources, tags)

    assert len(rows) == 1
    assert rows[0]["resource_name"] == "needs-owner"
    assert rows[0]["created_by"] == "alice"
    assert rows[0]["oracle_created_on"] == "2026-05-01"
    assert rows[0]["no_shutdown"] == "Yes"
    assert rows[0]["recommended_owner"] == ""
    assert rows[0]["recommendation_reason"] == RECOMMENDATION_REASON
    assert rows[0]["suggested_action"] == SUGGESTED_ACTION

from oci_resource_dashboard.compliance import load_mandatory_tags
from oci_resource_dashboard.ownership_coverage import (
    ownership_coverage_rows,
    summarize_ownership_coverage,
)


def test_ownership_coverage_summary_calculations_are_correct():
    tags = load_mandatory_tags("config/mandatory_tags.example.yaml")
    resources = [
        {"defined_tags": {"Oracle-Tags": {"CreatedBy": "alice"}}, "freeform_tags": {"Owner": "team-a"}},
        {"defined_tags": {"Oracle-Tags": {"CreatedBy": "bob"}}, "freeform_tags": {}},
        {"defined_tags": {}, "freeform_tags": {"Owner": "team-b"}},
        {"defined_tags": {}, "freeform_tags": {}},
    ]

    summary = summarize_ownership_coverage(resources, tags)

    assert summary.total_resources == 4
    assert summary.resources_with_created_by == 2
    assert summary.resources_with_owner == 2
    assert summary.resources_with_both_created_by_and_owner == 1
    assert summary.resources_missing_both_created_by_and_owner == 1
    assert summary.resources_missing_only_owner == 1
    assert summary.resources_missing_only_created_by == 1


def test_ownership_coverage_rows_include_expected_metrics():
    tags = load_mandatory_tags("config/mandatory_tags.example.yaml")
    summary = summarize_ownership_coverage(
        [
            {"defined_tags": {"Oracle-Tags": {"CreatedBy": "alice"}}, "freeform_tags": {}},
            {"defined_tags": {}, "freeform_tags": {}},
        ],
        tags,
    )

    rows = ownership_coverage_rows(summary)
    by_metric = {row["metric"]: row for row in rows}

    assert by_metric["Resources with CreatedBy"]["count"] == 1
    assert by_metric["Resources with CreatedBy"]["percent_of_total"] == 50.0
    assert by_metric["Resources missing only Owner"]["count"] == 1

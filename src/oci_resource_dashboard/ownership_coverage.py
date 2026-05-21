"""Ownership coverage analytics for CreatedBy and Owner tags."""

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from .compliance import evaluate_resource_compliance
from .models import MandatoryTag
from .tag_extractors import ResourceLike


@dataclass(frozen=True)
class OwnershipCoverageSummary:
    total_resources: int
    resources_with_created_by: int
    resources_with_owner: int
    resources_with_both_created_by_and_owner: int
    resources_missing_both_created_by_and_owner: int
    resources_missing_only_owner: int
    resources_missing_only_created_by: int


def summarize_ownership_coverage(
    resources: Iterable[ResourceLike],
    mandatory_tags: Iterable[MandatoryTag],
) -> OwnershipCoverageSummary:
    """Summarize partial ownership signal coverage."""

    tags = tuple(mandatory_tags)
    total = 0
    with_created_by = 0
    with_owner = 0
    with_both = 0
    missing_both = 0
    missing_only_owner = 0
    missing_only_created_by = 0

    for resource in resources:
        total += 1
        result = evaluate_resource_compliance(resource, tags)
        has_created_by = bool(result.present_tags.get("CreatedBy"))
        has_owner = bool(result.present_tags.get("Owner"))
        if has_created_by:
            with_created_by += 1
        if has_owner:
            with_owner += 1
        if has_created_by and has_owner:
            with_both += 1
        elif not has_created_by and not has_owner:
            missing_both += 1
        elif has_created_by and not has_owner:
            missing_only_owner += 1
        elif has_owner and not has_created_by:
            missing_only_created_by += 1

    return OwnershipCoverageSummary(
        total_resources=total,
        resources_with_created_by=with_created_by,
        resources_with_owner=with_owner,
        resources_with_both_created_by_and_owner=with_both,
        resources_missing_both_created_by_and_owner=missing_both,
        resources_missing_only_owner=missing_only_owner,
        resources_missing_only_created_by=missing_only_created_by,
    )


def _percent(count: int, total: int) -> float:
    if not total:
        return 0.0
    return round((count / total) * 100, 2)


def ownership_coverage_rows(summary: OwnershipCoverageSummary) -> list[dict[str, Any]]:
    """Return CSV-ready ownership coverage rows."""

    rows = [
        ("Resources with CreatedBy", summary.resources_with_created_by),
        ("Resources with Owner", summary.resources_with_owner),
        (
            "Resources with both CreatedBy and Owner",
            summary.resources_with_both_created_by_and_owner,
        ),
        (
            "Resources missing both CreatedBy and Owner",
            summary.resources_missing_both_created_by_and_owner,
        ),
        ("Resources missing only Owner", summary.resources_missing_only_owner),
        ("Resources missing only CreatedBy", summary.resources_missing_only_created_by),
    ]
    return [
        {
            "metric": metric,
            "count": count,
            "percent_of_total": _percent(count, summary.total_resources),
        }
        for metric, count in rows
    ]

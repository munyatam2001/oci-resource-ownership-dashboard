"""Owner tag backfill recommendation reporting."""

from collections.abc import Iterable
from typing import Any, Mapping

from .compliance import evaluate_resource_compliance
from .models import MandatoryTag
from .tag_extractors import extract_no_shutdown, extract_oracle_created_on


OWNER_BACKFILL_HEADERS = [
    "resource_name",
    "resource_id",
    "resource_type",
    "compartment_name",
    "region",
    "lifecycle_state",
    "created_by",
    "oracle_created_on",
    "no_shutdown",
    "recommended_owner",
    "recommendation_reason",
    "suggested_action",
]


RECOMMENDATION_REASON = "CreatedBy exists but Owner is missing"
SUGGESTED_ACTION = "Contact CreatedBy user or owning team to confirm Owner tag value"


def _resource_value(resource: Mapping[str, Any], *keys: str) -> str:
    for key in keys:
        value = resource.get(key)
        if value is not None:
            return str(value)
    return ""


def owner_backfill_rows(
    resources: Iterable[Mapping[str, Any]],
    mandatory_tags: Iterable[MandatoryTag],
) -> list[dict[str, Any]]:
    """Return resources where CreatedBy exists but Owner is missing."""

    rows: list[dict[str, Any]] = []
    tags = tuple(mandatory_tags)
    for resource in resources:
        result = evaluate_resource_compliance(resource, tags)
        created_by = result.present_tags.get("CreatedBy", "")
        owner = result.present_tags.get("Owner", "")
        if not created_by or owner:
            continue
        rows.append(
            {
                "resource_name": _resource_value(resource, "resource_name", "display_name", "name"),
                "resource_id": _resource_value(resource, "resource_id", "id"),
                "resource_type": _resource_value(resource, "resource_type"),
                "compartment_name": _resource_value(resource, "compartment_name"),
                "region": _resource_value(resource, "region"),
                "lifecycle_state": _resource_value(resource, "lifecycle_state"),
                "created_by": created_by,
                "oracle_created_on": extract_oracle_created_on(resource) or "",
                "no_shutdown": extract_no_shutdown(resource) or "",
                "recommended_owner": "",
                "recommendation_reason": RECOMMENDATION_REASON,
                "suggested_action": SUGGESTED_ACTION,
            }
        )
    return rows

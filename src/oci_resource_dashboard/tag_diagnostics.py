"""Tag usage diagnostics and mapping hints."""

from dataclasses import dataclass, field
from typing import Any, Mapping


MAX_EXAMPLE_VALUES = 5

MAPPING_HINTS = {
    "CreatedBy": {
        "createdby",
        "created_by",
        "creator",
        "created-by",
        "requestedby",
        "requested_by",
    },
    "Owner": {
        "owner",
        "ownedby",
        "owned_by",
        "team",
        "contact",
        "applicationowner",
    },
    "CostCenter": {
        "costcenter",
        "cost_center",
        "cost-centre",
        "costcode",
        "chargeback",
    },
    "Environment": {
        "env",
        "environment",
        "lifecycle",
        "stage",
    },
    "Application": {
        "app",
        "application",
        "appname",
        "service",
        "project",
    },
}


@dataclass
class TagUsage:
    """Aggregated usage for one freeform or defined tag key."""

    tag_type: str
    tag_key: str
    resources_with_key: int = 0
    resources_with_nonempty_value: int = 0
    example_values: list[str] = field(default_factory=list)


def _is_nonempty(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    return True


def _safe_mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    return {}


def _add_usage(
    usage_by_identity: dict[tuple[str, str], TagUsage],
    tag_type: str,
    tag_key: str,
    value: Any,
) -> None:
    identity = (tag_type, tag_key)
    usage = usage_by_identity.setdefault(identity, TagUsage(tag_type=tag_type, tag_key=tag_key))
    usage.resources_with_key += 1
    if _is_nonempty(value):
        usage.resources_with_nonempty_value += 1
        example = str(value).strip() if isinstance(value, str) else str(value)
        if example not in usage.example_values and len(usage.example_values) < MAX_EXAMPLE_VALUES:
            usage.example_values.append(example)


def collect_tag_usage(resources: list[Mapping[str, Any]]) -> list[TagUsage]:
    """Collect tag key usage across normalized resource dictionaries."""

    usage_by_identity: dict[tuple[str, str], TagUsage] = {}

    for resource in resources:
        freeform_tags = _safe_mapping(resource.get("freeform_tags"))
        for key, value in freeform_tags.items():
            _add_usage(usage_by_identity, "freeform", str(key), value)

        defined_tags = _safe_mapping(resource.get("defined_tags"))
        for namespace, namespace_tags in defined_tags.items():
            for key, value in _safe_mapping(namespace_tags).items():
                _add_usage(usage_by_identity, "defined", f"{namespace}.{key}", value)

    return sorted(
        usage_by_identity.values(),
        key=lambda usage: (-usage.resources_with_key, usage.tag_type, usage.tag_key.lower()),
    )


def _normalized_hint_key(tag_key: str) -> str:
    raw_key = tag_key.split(".")[-1]
    return raw_key.strip().casefold()


def find_mapping_hints(tag_usage: list[TagUsage]) -> list[dict[str, Any]]:
    """Find existing tag keys that look like mandatory tag candidates."""

    rows: list[dict[str, Any]] = []
    for usage in tag_usage:
        normalized_key = _normalized_hint_key(usage.tag_key)
        for mandatory_tag, candidates in MAPPING_HINTS.items():
            if normalized_key in {candidate.casefold() for candidate in candidates}:
                rows.append(
                    {
                        "mandatory_tag": mandatory_tag,
                        "candidate_existing_key": usage.tag_key,
                        "tag_type": usage.tag_type,
                        "resources_with_key": usage.resources_with_key,
                        "example_values": ";".join(usage.example_values),
                    }
                )

    return sorted(
        rows,
        key=lambda row: (
            row["mandatory_tag"],
            -int(row["resources_with_key"]),
            row["candidate_existing_key"].lower(),
        ),
    )


def tag_usage_rows(tag_usage: list[TagUsage]) -> list[dict[str, Any]]:
    """Return CSV-ready tag usage rows."""

    return [
        {
            "tag_type": usage.tag_type,
            "tag_key": usage.tag_key,
            "resources_with_key": usage.resources_with_key,
            "resources_with_nonempty_value": usage.resources_with_nonempty_value,
            "example_values": ";".join(usage.example_values),
        }
        for usage in tag_usage
    ]

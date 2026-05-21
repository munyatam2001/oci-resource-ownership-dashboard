"""CSV output generation for resource tag compliance reports."""

import csv
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path
from typing import Any, Mapping

from .compliance import evaluate_resource_compliance, summarize_compliance
from .models import MandatoryTag
from .tag_diagnostics import collect_tag_usage, find_mapping_hints, tag_usage_rows
from .tag_extractors import extract_no_shutdown, extract_oracle_created_on


INVENTORY_BASE_HEADERS = [
    "resource_name",
    "resource_id",
    "resource_type",
    "lifecycle_state",
    "compartment_id",
    "compartment_name",
    "region",
    "time_created",
]


INVENTORY_TRAILING_HEADERS = [
    "OracleCreatedOn",
    "NoShutDown",
    "missing_tags",
    "compliance_percent",
    "is_compliant",
]


INVENTORY_HEADERS = [
    *INVENTORY_BASE_HEADERS,
    "CreatedBy",
    "Owner",
    *INVENTORY_TRAILING_HEADERS,
]


SUMMARY_HEADERS = [
    "total_resources",
    "compliant_resources",
    "noncompliant_resources",
    "compliance_percent",
]


GROUP_HEADERS = [
    "group",
    "total_resources",
    "compliant_resources",
    "noncompliant_resources",
    "compliance_percent",
]


TAG_USAGE_HEADERS = [
    "tag_type",
    "tag_key",
    "resources_with_key",
    "resources_with_nonempty_value",
    "example_values",
]


MAPPING_HINT_HEADERS = [
    "mandatory_tag",
    "candidate_existing_key",
    "tag_type",
    "resources_with_key",
    "example_values",
]


CSV_FILENAMES = {
    "inventory": "oci_resources_with_tags.csv",
    "missing": "oci_resources_missing_mandatory_tags.csv",
    "summary": "oci_tag_compliance_summary.csv",
    "by_owner": "oci_tag_compliance_by_owner.csv",
    "by_compartment": "oci_tag_compliance_by_compartment.csv",
    "tag_usage": "oci_tag_key_usage.csv",
    "mapping_hints": "oci_tag_mapping_hints.csv",
}


def inventory_headers(mandatory_tags: Iterable[MandatoryTag]) -> list[str]:
    """Return inventory headers for the active mandatory tag model."""

    return [
        *INVENTORY_BASE_HEADERS,
        *(tag.canonical_name for tag in mandatory_tags),
        *INVENTORY_TRAILING_HEADERS,
    ]


def _resource_value(resource: Mapping[str, Any], *keys: str) -> str:
    for key in keys:
        value = resource.get(key)
        if value is not None:
            return str(value)
    return ""


def build_inventory_row(
    resource: Mapping[str, Any],
    mandatory_tags: Iterable[MandatoryTag],
) -> dict[str, Any]:
    """Build one resource inventory CSV row."""

    result = evaluate_resource_compliance(resource, mandatory_tags)
    tags = tuple(mandatory_tags)
    row = {
        "resource_name": _resource_value(resource, "resource_name", "display_name", "name"),
        "resource_id": _resource_value(resource, "resource_id", "id"),
        "resource_type": _resource_value(resource, "resource_type"),
        "lifecycle_state": _resource_value(resource, "lifecycle_state"),
        "compartment_id": _resource_value(resource, "compartment_id"),
        "compartment_name": _resource_value(resource, "compartment_name"),
        "region": _resource_value(resource, "region"),
        "time_created": _resource_value(resource, "time_created"),
        "OracleCreatedOn": extract_oracle_created_on(resource) or "",
        "NoShutDown": extract_no_shutdown(resource) or "",
        "missing_tags": ";".join(result.missing_tags),
        "compliance_percent": result.compliance_percent,
        "is_compliant": str(result.is_compliant).lower(),
    }
    for tag in tags:
        row[tag.canonical_name] = result.present_tags.get(tag.canonical_name, "")
    return row


def _write_rows(path: Path, headers: list[str], rows: Iterable[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def _group_summary_rows(
    resources: Iterable[Mapping[str, Any]],
    mandatory_tags: Iterable[MandatoryTag],
    group_key: str,
) -> list[dict[str, Any]]:
    grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    tags = tuple(mandatory_tags)

    for resource in resources:
        if group_key == "owner":
            result = evaluate_resource_compliance(resource, tags)
            group = str(result.present_tags.get("Owner") or "Unknown")
        elif group_key == "compartment":
            group = _resource_value(resource, "compartment_name") or "Unknown"
        else:
            raise ValueError(f"Unsupported group key: {group_key}")
        grouped[group].append(resource)

    rows: list[dict[str, Any]] = []
    for group, group_resources in sorted(grouped.items()):
        summary = summarize_compliance(group_resources, tags)
        rows.append(
            {
                "group": group,
                "total_resources": summary.total_resources,
                "compliant_resources": summary.compliant_resources,
                "noncompliant_resources": summary.noncompliant_resources,
                "compliance_percent": summary.compliance_percent,
            }
        )
    return rows


def write_csv_outputs(
    resources: Iterable[Mapping[str, Any]],
    mandatory_tags: Iterable[MandatoryTag],
    output_dir: Path,
) -> list[Path]:
    """Write all CSV outputs and return their paths."""

    output_dir.mkdir(parents=True, exist_ok=True)
    resource_list = list(resources)
    tags = tuple(mandatory_tags)

    inventory_rows = [build_inventory_row(resource, tags) for resource in resource_list]
    missing_rows = [row for row in inventory_rows if row["is_compliant"] == "false"]
    summary = summarize_compliance(resource_list, tags)

    paths = {
        name: output_dir / filename for name, filename in CSV_FILENAMES.items()
    }

    headers = inventory_headers(tags)
    _write_rows(paths["inventory"], headers, inventory_rows)
    _write_rows(paths["missing"], headers, missing_rows)
    _write_rows(
        paths["summary"],
        SUMMARY_HEADERS,
        [
            {
                "total_resources": summary.total_resources,
                "compliant_resources": summary.compliant_resources,
                "noncompliant_resources": summary.noncompliant_resources,
                "compliance_percent": summary.compliance_percent,
            }
        ],
    )
    _write_rows(paths["by_owner"], GROUP_HEADERS, _group_summary_rows(resource_list, tags, "owner"))
    _write_rows(
        paths["by_compartment"],
        GROUP_HEADERS,
        _group_summary_rows(resource_list, tags, "compartment"),
    )
    usage = collect_tag_usage(resource_list)
    _write_rows(paths["tag_usage"], TAG_USAGE_HEADERS, tag_usage_rows(usage))
    _write_rows(paths["mapping_hints"], MAPPING_HINT_HEADERS, find_mapping_hints(usage))

    return [paths[name] for name in CSV_FILENAMES]

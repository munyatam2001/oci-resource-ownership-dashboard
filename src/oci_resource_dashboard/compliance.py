"""Mandatory tag compliance checks."""

from collections.abc import Iterable
from pathlib import Path
from typing import Any, Union

import yaml

from .models import ComplianceResult, ComplianceSummary, MandatoryTag, ResourceRecord
from .tag_extractors import ResourceLike, extract_tag_value


def load_mandatory_tags(path: Union[str, Path]) -> list[MandatoryTag]:
    """Load mandatory tag definitions from YAML."""

    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as config_file:
        data = yaml.safe_load(config_file) or {}

    raw_tags = data.get("mandatory_tags", [])
    if not isinstance(raw_tags, list):
        raise ValueError("'mandatory_tags' must be a list")

    mandatory_tags: list[MandatoryTag] = []
    for raw_tag in raw_tags:
        if not isinstance(raw_tag, dict):
            raise ValueError("Each mandatory tag must be a mapping")
        aliases = raw_tag.get("aliases") or ()
        if isinstance(aliases, str) or not isinstance(aliases, Iterable):
            raise ValueError(f"aliases must be a list for tag {raw_tag!r}")
        mandatory_tags.append(
            MandatoryTag(
                canonical_name=str(raw_tag["canonical_name"]),
                defined_tag_namespace=raw_tag.get("defined_tag_namespace"),
                defined_tag_key=raw_tag.get("defined_tag_key"),
                aliases=tuple(str(alias) for alias in aliases),
            )
        )

    return mandatory_tags


def missing_mandatory_tags(
    resource: ResourceLike,
    mandatory_tags: Iterable[MandatoryTag],
) -> tuple[str, ...]:
    """Return mandatory tags missing from a resource."""

    missing: list[str] = []
    for tag in mandatory_tags:
        if extract_tag_value(resource, tag) is None:
            missing.append(tag.canonical_name)
    return tuple(missing)


def evaluate_resource_compliance(
    resource: ResourceLike,
    mandatory_tags: Iterable[MandatoryTag],
) -> ComplianceResult:
    """Evaluate one resource for mandatory tag compliance."""

    tags = tuple(mandatory_tags)
    present_tags: dict[str, Any] = {}
    missing_tags: list[str] = []

    for tag in tags:
        value = extract_tag_value(resource, tag)
        if value is None:
            missing_tags.append(tag.canonical_name)
        else:
            present_tags[tag.canonical_name] = value

    compliance_percent = 100.0
    if tags:
        compliance_percent = round((len(present_tags) / len(tags)) * 100, 2)

    return ComplianceResult(
        resource=resource,
        present_tags=present_tags,
        missing_tags=tuple(missing_tags),
        compliance_percent=compliance_percent,
    )


def evaluate_resource(
    resource: ResourceLike,
    mandatory_tags: Iterable[MandatoryTag],
) -> ComplianceResult:
    """Compatibility wrapper for evaluating one resource."""

    return evaluate_resource_compliance(resource, mandatory_tags)


def evaluate_resources(
    resources: Iterable[ResourceLike],
    mandatory_tags: Iterable[MandatoryTag],
) -> list[ComplianceResult]:
    """Evaluate multiple resources for mandatory tag compliance."""

    tags = tuple(mandatory_tags)
    return [evaluate_resource_compliance(resource, tags) for resource in resources]


def summarize_compliance(
    resources: Iterable[ResourceLike],
    mandatory_tags: Iterable[MandatoryTag],
) -> ComplianceSummary:
    """Summarize compliance across multiple resources."""

    tags = tuple(mandatory_tags)
    tag_names = [tag.canonical_name for tag in tags]
    missing_count_by_tag = {tag_name: 0 for tag_name in tag_names}
    present_count_by_tag = {tag_name: 0 for tag_name in tag_names}

    results = [evaluate_resource_compliance(resource, tags) for resource in resources]

    for result in results:
        for tag_name in result.present_tags:
            present_count_by_tag[tag_name] += 1
        for tag_name in result.missing_tags:
            missing_count_by_tag[tag_name] += 1

    total_resources = len(results)
    compliant_resources = sum(1 for result in results if result.is_compliant)
    noncompliant_resources = total_resources - compliant_resources
    compliance_percent = 100.0
    if total_resources:
        compliance_percent = round((compliant_resources / total_resources) * 100, 2)

    return ComplianceSummary(
        total_resources=total_resources,
        compliant_resources=compliant_resources,
        noncompliant_resources=noncompliant_resources,
        compliance_percent=compliance_percent,
        missing_count_by_tag=missing_count_by_tag,
        present_count_by_tag=present_count_by_tag,
    )

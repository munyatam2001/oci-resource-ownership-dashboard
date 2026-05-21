"""Mandatory tag compliance checks."""

from collections.abc import Iterable

from .models import ComplianceResult, MandatoryTag, ResourceRecord
from .tag_extractors import extract_mandatory_tag_value


def missing_mandatory_tags(
    resource: ResourceRecord,
    mandatory_tags: Iterable[MandatoryTag],
) -> tuple[MandatoryTag, ...]:
    """Return mandatory tags missing from a resource."""

    missing: list[MandatoryTag] = []
    for tag in mandatory_tags:
        value = extract_mandatory_tag_value(
            resource.freeform_tags,
            resource.defined_tags,
            tag,
        )
        if value is None:
            missing.append(tag)
    return tuple(missing)


def evaluate_resource(
    resource: ResourceRecord,
    mandatory_tags: Iterable[MandatoryTag],
) -> ComplianceResult:
    """Evaluate one resource for mandatory tag compliance."""

    return ComplianceResult(
        resource=resource,
        missing_tags=missing_mandatory_tags(resource, mandatory_tags),
    )


def evaluate_resources(
    resources: Iterable[ResourceRecord],
    mandatory_tags: Iterable[MandatoryTag],
) -> list[ComplianceResult]:
    """Evaluate multiple resources for mandatory tag compliance."""

    tags = tuple(mandatory_tags)
    return [evaluate_resource(resource, tags) for resource in resources]

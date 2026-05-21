"""Shared data models for resources, tags, and compliance results."""

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
class MandatoryTag:
    """A tag required for ownership or compliance reporting."""

    canonical_name: str
    defined_tag_namespace: Optional[str] = None
    defined_tag_key: Optional[str] = None
    aliases: tuple[str, ...] = ()

    @property
    def name(self) -> str:
        """Compatibility alias for older callers."""

        return self.canonical_name

    @property
    def flattened_defined_tag_key(self) -> Optional[str]:
        """Return the namespace.key freeform fallback key for this tag."""

        if not self.defined_tag_namespace or not self.defined_tag_key:
            return None
        return f"{self.defined_tag_namespace}.{self.defined_tag_key}"


@dataclass(frozen=True)
class ResourceRecord:
    """Normalized resource details used by reporting code."""

    identifier: str
    display_name: str
    resource_type: str
    compartment_id: str
    lifecycle_state: Optional[str] = None
    region: Optional[str] = None
    freeform_tags: dict[str, str] = field(default_factory=dict)
    defined_tags: dict[str, dict[str, Any]] = field(default_factory=dict)


@dataclass(frozen=True)
class ComplianceResult:
    """Mandatory tag compliance result for a single resource."""

    resource: Any
    present_tags: dict[str, Any]
    missing_tags: tuple[str, ...]
    compliance_percent: float

    @property
    def is_compliant(self) -> bool:
        return not self.missing_tags


@dataclass(frozen=True)
class ComplianceSummary:
    """Aggregate mandatory tag compliance summary."""

    total_resources: int
    compliant_resources: int
    noncompliant_resources: int
    compliance_percent: float
    missing_count_by_tag: dict[str, int]
    present_count_by_tag: dict[str, int]

"""Shared data models for resources, tags, and compliance results."""

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
class MandatoryTag:
    """A tag required for ownership or compliance reporting."""

    name: str
    source: str
    namespace: Optional[str] = None
    key: Optional[str] = None
    description: Optional[str] = None

    @property
    def lookup_key(self) -> str:
        return self.key or self.name


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

    resource: ResourceRecord
    missing_tags: tuple[MandatoryTag, ...]

    @property
    def is_compliant(self) -> bool:
        return not self.missing_tags

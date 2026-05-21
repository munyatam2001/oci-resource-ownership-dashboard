"""Helpers for extracting values from OCI tag dictionaries."""

from typing import Any, Optional

from .models import MandatoryTag


def extract_freeform_tag(
    freeform_tags: Optional[dict[str, Any]],
    tag_name: str,
) -> Optional[Any]:
    """Return a freeform tag value using OCI's case-sensitive tag key."""

    if not freeform_tags:
        return None
    value = freeform_tags.get(tag_name)
    return value if value not in ("", None) else None


def extract_defined_tag(
    defined_tags: Optional[dict[str, dict[str, Any]]],
    namespace: str,
    key: str,
) -> Optional[Any]:
    """Return a defined tag value from namespace/key dictionaries."""

    if not defined_tags:
        return None
    namespace_values = defined_tags.get(namespace) or {}
    value = namespace_values.get(key)
    return value if value not in ("", None) else None


def extract_mandatory_tag_value(
    freeform_tags: Optional[dict[str, Any]],
    defined_tags: Optional[dict[str, dict[str, Any]]],
    tag: MandatoryTag,
) -> Optional[Any]:
    """Extract a configured mandatory tag value from freeform or defined tags."""

    if tag.source == "freeform":
        return extract_freeform_tag(freeform_tags, tag.lookup_key)
    if tag.source == "defined":
        if not tag.namespace:
            raise ValueError(f"Defined tag '{tag.name}' requires a namespace")
        return extract_defined_tag(defined_tags, tag.namespace, tag.lookup_key)
    raise ValueError(f"Unsupported mandatory tag source: {tag.source}")

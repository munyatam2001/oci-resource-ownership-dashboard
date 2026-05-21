"""Helpers for extracting values from OCI tag dictionaries."""

from typing import Any, Mapping, Optional, Union

from .models import MandatoryTag, ResourceRecord


ResourceLike = Union[Mapping[str, Any], ResourceRecord]


def _normalize_blank(value: Any) -> Optional[Any]:
    if value is None:
        return None
    if isinstance(value, str) and not value.strip():
        return None
    return value


def _resource_tags(resource: ResourceLike) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    if isinstance(resource, ResourceRecord):
        return resource.freeform_tags or {}, resource.defined_tags or {}
    freeform_tags = resource.get("freeform_tags") or {}
    defined_tags = resource.get("defined_tags") or {}
    if not isinstance(freeform_tags, Mapping):
        freeform_tags = {}
    if not isinstance(defined_tags, Mapping):
        defined_tags = {}
    return freeform_tags, defined_tags


def extract_freeform_tag(
    freeform_tags: Optional[Mapping[str, Any]],
    tag_name: str,
) -> Optional[Any]:
    """Return a freeform tag value using OCI's case-sensitive tag key."""

    if not freeform_tags:
        return None
    return _normalize_blank(freeform_tags.get(tag_name))


def extract_defined_tag(
    defined_tags: Optional[Mapping[str, Any]],
    namespace: str,
    key: str,
) -> Optional[Any]:
    """Return a defined tag value from namespace/key dictionaries."""

    if not defined_tags:
        return None
    namespace_values = defined_tags.get(namespace) or {}
    if not isinstance(namespace_values, Mapping):
        return None
    return _normalize_blank(namespace_values.get(key))


def _candidate_freeform_keys(mandatory_tag: MandatoryTag) -> list[str]:
    keys = [mandatory_tag.canonical_name]
    keys.extend(mandatory_tag.aliases)
    if mandatory_tag.flattened_defined_tag_key:
        keys.append(mandatory_tag.flattened_defined_tag_key)
    if mandatory_tag.defined_tag_namespace:
        keys.append(f"{mandatory_tag.defined_tag_namespace}.{mandatory_tag.canonical_name}")

    deduped: list[str] = []
    for key in keys:
        if key and key not in deduped:
            deduped.append(key)
    return deduped


def extract_mandatory_tag_value(
    freeform_tags: Optional[Mapping[str, Any]],
    defined_tags: Optional[Mapping[str, Any]],
    tag: MandatoryTag,
) -> Optional[Any]:
    """Extract a mandatory tag from raw tag dictionaries."""

    if tag.defined_tag_namespace and tag.defined_tag_key:
        value = extract_defined_tag(defined_tags, tag.defined_tag_namespace, tag.defined_tag_key)
        if value is not None:
            return value

    freeform_tags = freeform_tags or {}
    candidate_keys = _candidate_freeform_keys(tag)
    for key in candidate_keys:
        value = extract_freeform_tag(freeform_tags, key)
        if value is not None:
            return value

    casefolded_candidates = {key.casefold() for key in candidate_keys}
    for key, value in freeform_tags.items():
        if str(key).casefold() in casefolded_candidates:
            normalized_value = _normalize_blank(value)
            if normalized_value is not None:
                return normalized_value

    return None


def extract_tag_value(resource: ResourceLike, mandatory_tag: MandatoryTag) -> Optional[Any]:
    """Extract a configured mandatory tag value from an OCI-like resource."""

    freeform_tags, defined_tags = _resource_tags(resource)
    return extract_mandatory_tag_value(freeform_tags, defined_tags, mandatory_tag)

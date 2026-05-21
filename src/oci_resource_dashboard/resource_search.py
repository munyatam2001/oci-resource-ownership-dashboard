"""OCI Resource Search integration and sample resources."""

from collections.abc import Iterable
from datetime import datetime
from typing import Any, Mapping, Optional, Protocol

from .auth import OciAuthContext
from .models import ResourceRecord


class ResourceSearch(Protocol):
    """Interface for discovering OCI resources."""

    def search_resources(self, compartment_ids: Iterable[str]) -> Iterable[ResourceRecord]:
        """Return normalized resource records."""


def _get_attr(value: Any, name: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        return value.get(name, default)
    return getattr(value, name, default)


def _stringify_time(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _safe_tags(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    return {}


def _escape_query_value(value: str) -> str:
    return value.replace("'", "\\'")


class OciResourceSearch:
    """OCI-backed resource search implementation."""

    def __init__(
        self,
        auth_context: OciAuthContext,
        compartment_id_to_name: Optional[dict[str, str]] = None,
        resource_search_client: Optional[Any] = None,
    ) -> None:
        self.auth_context = auth_context
        self.compartment_id_to_name = compartment_id_to_name or {}
        self.resource_search_client = resource_search_client

    def _client(self) -> Any:
        if self.resource_search_client is not None:
            return self.resource_search_client
        try:
            import oci
        except ImportError as exc:
            raise RuntimeError("The OCI SDK is required for live resource discovery.") from exc
        return oci.resource_search.ResourceSearchClient(
            self.auth_context.config,
            signer=self.auth_context.signer,
        )

    def _structured_search_details(self, query: str) -> Any:
        try:
            import oci
        except ImportError as exc:
            raise RuntimeError("The OCI SDK is required for live resource discovery.") from exc
        return oci.resource_search.models.StructuredSearchDetails(
            query=query,
            matching_context_type="NONE",
        )

    def search_resources(self, compartment_ids: Iterable[str]) -> list[dict[str, Any]]:
        """Discover and normalize resources in the selected compartments."""

        client = self._client()
        resources: list[dict[str, Any]] = []

        for compartment_id in compartment_ids:
            page: Optional[str] = None
            while True:
                query = (
                    "query all resources where compartmentId = "
                    f"'{_escape_query_value(compartment_id)}'"
                )
                details = self._structured_search_details(query)
                response = client.search_resources(details, page=page)
                for item in self._response_items(response):
                    resources.append(self.normalize_resource(item))
                page = self._next_page(response)
                if not page:
                    break

        return resources

    def normalize_resource(self, resource: Any) -> dict[str, Any]:
        """Normalize an OCI Resource Search item into the internal dictionary shape."""

        compartment_id = str(_get_attr(resource, "compartment_id", "") or "")
        identifier = _get_attr(resource, "identifier") or _get_attr(resource, "id") or ""
        display_name = (
            _get_attr(resource, "display_name")
            or _get_attr(resource, "name")
            or identifier
            or "Unknown"
        )
        return {
            "resource_name": str(display_name),
            "resource_id": str(identifier),
            "resource_type": str(_get_attr(resource, "resource_type", "") or ""),
            "lifecycle_state": str(_get_attr(resource, "lifecycle_state", "") or ""),
            "compartment_id": compartment_id,
            "compartment_name": self.compartment_id_to_name.get(compartment_id, ""),
            "region": str(_get_attr(resource, "region", "") or self.auth_context.config.get("region", "")),
            "time_created": _stringify_time(_get_attr(resource, "time_created")),
            "freeform_tags": _safe_tags(_get_attr(resource, "freeform_tags")),
            "defined_tags": _safe_tags(_get_attr(resource, "defined_tags")),
        }

    @staticmethod
    def _response_items(response: Any) -> list[Any]:
        data = getattr(response, "data", None)
        items = _get_attr(data, "items")
        if items is None and isinstance(data, list):
            items = data
        return list(items or [])

    @staticmethod
    def _next_page(response: Any) -> Optional[str]:
        headers = getattr(response, "headers", {}) or {}
        if hasattr(headers, "get"):
            return headers.get("opc-next-page")
        return None


def enrich_compartment_names(
    resources: Iterable[dict[str, Any]],
    compartment_id_to_name: dict[str, str],
) -> list[dict[str, Any]]:
    """Fill compartment names after discovery if they are missing."""

    enriched: list[dict[str, Any]] = []
    for resource in resources:
        copied = dict(resource)
        compartment_id = str(copied.get("compartment_id") or "")
        copied["compartment_name"] = copied.get("compartment_name") or compartment_id_to_name.get(
            compartment_id,
            "",
        )
        enriched.append(copied)
    return enriched


def sample_resources() -> list[dict[str, Any]]:
    """Return realistic OCI-like resources for validating report output shape."""

    return [
        {
            "resource_name": "prod-api-01",
            "resource_id": "ocid1.instance.oc1.iad.examplecompute",
            "resource_type": "Instance",
            "lifecycle_state": "RUNNING",
            "compartment_id": "ocid1.compartment.oc1..prod",
            "compartment_name": "Prod",
            "region": "us-ashburn-1",
            "time_created": "2026-05-01T10:15:00Z",
            "defined_tags": {
                "Operations": {
                    "CreatedBy": "alice@example.com",
                    "Environment": "prod",
                    "Application": "payments",
                },
                "Finance": {"CostCenter": "CC-1001"},
            },
            "freeform_tags": {"Owner": "platform-team"},
        },
        {
            "resource_name": "prod-app-subnet",
            "resource_id": "ocid1.subnet.oc1.iad.examplesubnet",
            "resource_type": "Subnet",
            "lifecycle_state": "AVAILABLE",
            "compartment_id": "ocid1.compartment.oc1..prod-network",
            "compartment_name": "Prod Network",
            "region": "us-ashburn-1",
            "time_created": "2026-05-02T08:30:00Z",
            "defined_tags": {
                "Operations": {
                    "CreatedBy": "bob@example.com",
                    "Owner": "network-team",
                    "Environment": "prod",
                    "Application": "shared-network",
                }
            },
            "freeform_tags": {},
        },
        {
            "resource_name": "audit-log-bucket",
            "resource_id": "ocid1.bucket.oc1.iad.examplebucket",
            "resource_type": "Bucket",
            "lifecycle_state": "ACTIVE",
            "compartment_id": "ocid1.compartment.oc1..security",
            "compartment_name": "Security",
            "region": "us-ashburn-1",
            "time_created": "2026-05-03T12:00:00Z",
            "defined_tags": {
                "Operations": {
                    "CreatedBy": "carol@example.com",
                    "Environment": "prod",
                },
                "Finance": {"CostCenter": "CC-2002"},
            },
            "freeform_tags": {},
        },
        {
            "resource_name": "dev-data-volume",
            "resource_id": "ocid1.volume.oc1.iad.examplevolume",
            "resource_type": "Volume",
            "lifecycle_state": "AVAILABLE",
            "compartment_id": "ocid1.compartment.oc1..dev",
            "compartment_name": "Dev",
            "region": "us-ashburn-1",
            "time_created": "2026-05-04T16:45:00Z",
            "defined_tags": {},
            "freeform_tags": {
                "created_by": "dana@example.com",
                "owner": "data-team",
                "cost_center": "CC-3003",
                "env": "dev",
                "app": "analytics",
            },
        },
        {
            "resource_name": "legacy-vcn",
            "resource_id": "ocid1.vcn.oc1.iad.examplevcn",
            "resource_type": "Vcn",
            "lifecycle_state": "AVAILABLE",
            "compartment_id": "ocid1.compartment.oc1..legacy",
            "compartment_name": "Legacy",
            "region": "us-ashburn-1",
            "time_created": "2026-05-05T09:20:00Z",
            "defined_tags": {},
            "freeform_tags": {},
        },
    ]

"""Resource search interface stubs."""

from collections.abc import Iterable
from typing import Any, Protocol

from .models import ResourceRecord


class ResourceSearch(Protocol):
    """Interface for discovering OCI resources."""

    def search_resources(self, compartment_ids: Iterable[str]) -> Iterable[ResourceRecord]:
        """Return normalized resource records."""


class OciResourceSearch:
    """Future OCI-backed resource search implementation."""

    def search_resources(self, compartment_ids: Iterable[str]) -> Iterable[ResourceRecord]:
        raise NotImplementedError("OCI resource search is not implemented yet")


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

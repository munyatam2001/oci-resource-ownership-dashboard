"""OCI compartment discovery."""

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, Optional, Protocol

from .auth import OciAuthContext


ACTIVE_STATES = {"ACTIVE"}


@dataclass(frozen=True)
class CompartmentDiscoveryResult:
    """Compartment IDs and display names selected for scanning."""

    compartment_ids: list[str]
    compartment_id_to_name: dict[str, str]


class CompartmentDiscovery(Protocol):
    """Interface for listing compartments in a tenancy."""

    def list_compartment_ids(
        self,
        root_compartment_id: str,
        include_subcompartments: bool,
    ) -> Iterable[str]:
        """Return compartment IDs to scan."""


def _get_attr(value: Any, name: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(name, default)
    return getattr(value, name, default)


def _is_active_compartment(compartment: Any) -> bool:
    lifecycle_state = _get_attr(compartment, "lifecycle_state")
    if lifecycle_state is None:
        return True
    return str(lifecycle_state).upper() in ACTIVE_STATES


class OciCompartmentDiscovery:
    """OCI-backed compartment discovery implementation."""

    def __init__(self, auth_context: OciAuthContext, identity_client: Optional[Any] = None) -> None:
        self.auth_context = auth_context
        self.identity_client = identity_client

    def _client(self) -> Any:
        if self.identity_client is not None:
            return self.identity_client
        try:
            import oci
        except ImportError as exc:
            raise RuntimeError(
                "The OCI SDK is required for live compartment discovery."
            ) from exc
        return oci.identity.IdentityClient(
            self.auth_context.config,
            signer=self.auth_context.signer,
        )

    def discover_compartments(
        self,
        root_compartment_id: str,
        include_subcompartments: bool,
    ) -> CompartmentDiscoveryResult:
        """Discover the root compartment and optionally active child compartments."""

        client = self._client()
        compartment_id_to_name = {root_compartment_id: root_compartment_id}
        compartment_ids = [root_compartment_id]

        root_name = self._fetch_compartment_name(client, root_compartment_id)
        if root_name:
            compartment_id_to_name[root_compartment_id] = root_name

        if not include_subcompartments:
            return CompartmentDiscoveryResult(compartment_ids, compartment_id_to_name)

        page: Optional[str] = None
        while True:
            response = client.list_compartments(
                root_compartment_id,
                compartment_id_in_subtree=True,
                access_level="ACCESSIBLE",
                page=page,
            )
            for compartment in getattr(response, "data", []) or []:
                compartment_id = _get_attr(compartment, "id")
                if not compartment_id or not _is_active_compartment(compartment):
                    continue
                compartment_name = _get_attr(compartment, "name") or compartment_id
                if compartment_id not in compartment_id_to_name:
                    compartment_ids.append(compartment_id)
                compartment_id_to_name[compartment_id] = str(compartment_name)

            page = self._next_page(response)
            if not page:
                break

        return CompartmentDiscoveryResult(compartment_ids, compartment_id_to_name)

    def list_compartment_ids(
        self,
        root_compartment_id: str,
        include_subcompartments: bool,
    ) -> Iterable[str]:
        return self.discover_compartments(
            root_compartment_id,
            include_subcompartments,
        ).compartment_ids

    @staticmethod
    def _next_page(response: Any) -> Optional[str]:
        headers = getattr(response, "headers", {}) or {}
        if hasattr(headers, "get"):
            return headers.get("opc-next-page")
        return None

    @staticmethod
    def _fetch_compartment_name(client: Any, compartment_id: str) -> Optional[str]:
        try:
            response = client.get_compartment(compartment_id)
        except Exception:
            return None
        compartment = getattr(response, "data", None)
        name = _get_attr(compartment, "name")
        return str(name) if name else None

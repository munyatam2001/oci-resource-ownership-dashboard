"""Compartment discovery interface stubs."""

from collections.abc import Iterable
from typing import Protocol


class CompartmentDiscovery(Protocol):
    """Interface for listing compartments in a tenancy."""

    def list_compartment_ids(
        self,
        root_compartment_id: str,
        include_subcompartments: bool,
    ) -> Iterable[str]:
        """Return compartment IDs to scan."""


class OciCompartmentDiscovery:
    """Future OCI-backed compartment discovery implementation."""

    def list_compartment_ids(
        self,
        root_compartment_id: str,
        include_subcompartments: bool,
    ) -> Iterable[str]:
        raise NotImplementedError("OCI compartment discovery is not implemented yet")

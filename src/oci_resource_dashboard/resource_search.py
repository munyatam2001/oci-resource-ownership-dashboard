"""Resource search interface stubs."""

from collections.abc import Iterable
from typing import Protocol

from .models import ResourceRecord


class ResourceSearch(Protocol):
    """Interface for discovering OCI resources."""

    def search_resources(self, compartment_ids: Iterable[str]) -> Iterable[ResourceRecord]:
        """Return normalized resource records."""


class OciResourceSearch:
    """Future OCI-backed resource search implementation."""

    def search_resources(self, compartment_ids: Iterable[str]) -> Iterable[ResourceRecord]:
        raise NotImplementedError("OCI resource search is not implemented yet")

"""Authentication provider interfaces for OCI clients."""

from dataclasses import dataclass
from typing import Any, Protocol


class AuthProvider(Protocol):
    """Interface for future OCI authentication implementations."""

    def signer(self) -> Any:
        """Return an OCI SDK signer."""

    def config(self) -> dict[str, Any]:
        """Return OCI SDK config values."""


@dataclass(frozen=True)
class AuthSettings:
    """Configuration for selecting an OCI auth provider."""

    method: str
    region: str


def build_auth_provider(settings: AuthSettings) -> AuthProvider:
    """Create an auth provider.

    OCI SDK integration is intentionally deferred until the discovery phase.
    """

    raise NotImplementedError(
        f"Auth provider '{settings.method}' is not implemented in this phase"
    )

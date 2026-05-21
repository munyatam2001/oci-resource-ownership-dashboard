"""Authentication helpers for OCI SDK clients."""

from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class AuthSettings:
    """Configuration for selecting an OCI auth provider."""

    method: str
    region: Optional[str] = None


@dataclass(frozen=True)
class OciAuthContext:
    """OCI SDK auth material shared by service clients."""

    config: dict[str, Any]
    signer: Any = None


def build_auth_context(settings: AuthSettings) -> OciAuthContext:
    """Create OCI SDK config and signer values for the selected auth mode."""

    try:
        import oci
    except ImportError as exc:
        raise RuntimeError(
            "The OCI SDK is required for live discovery. Install requirements.txt first."
        ) from exc

    if settings.method == "config":
        config = dict(oci.config.from_file())
        if settings.region:
            config["region"] = settings.region
        return OciAuthContext(config=config, signer=None)

    if settings.method == "instance_principal":
        signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
        config: dict[str, Any] = {}
        if settings.region:
            config["region"] = settings.region
        return OciAuthContext(config=config, signer=signer)

    raise ValueError(f"Unsupported auth method: {settings.method}")


def build_auth_provider(settings: AuthSettings) -> OciAuthContext:
    """Compatibility wrapper for older callers."""

    return build_auth_context(settings)

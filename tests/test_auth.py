import sys
from types import SimpleNamespace

from oci_resource_dashboard.auth import AuthSettings, build_auth_context


def test_config_auth_uses_oci_config_from_file_with_region_override(monkeypatch):
    fake_oci = SimpleNamespace(
        config=SimpleNamespace(from_file=lambda: {"region": "us-phoenix-1", "tenancy": "t"}),
    )
    monkeypatch.setitem(sys.modules, "oci", fake_oci)

    context = build_auth_context(AuthSettings(method="config", region="us-ashburn-1"))

    assert context.config["region"] == "us-ashburn-1"
    assert context.config["tenancy"] == "t"
    assert context.signer is None


def test_instance_principal_auth_builds_signer_and_region_config(monkeypatch):
    signer = object()
    fake_oci = SimpleNamespace(
        auth=SimpleNamespace(
            signers=SimpleNamespace(
                InstancePrincipalsSecurityTokenSigner=lambda: signer,
            ),
        ),
    )
    monkeypatch.setitem(sys.modules, "oci", fake_oci)

    context = build_auth_context(
        AuthSettings(method="instance_principal", region="eu-frankfurt-1")
    )

    assert context.config == {"region": "eu-frankfurt-1"}
    assert context.signer is signer

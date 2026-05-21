from types import SimpleNamespace

from oci_resource_dashboard.auth import OciAuthContext
from oci_resource_dashboard.compartments import OciCompartmentDiscovery


class FakeIdentityClient:
    def __init__(self):
        self.pages = [
            SimpleNamespace(
                data=[
                    SimpleNamespace(
                        id="ocid1.compartment.oc1..child1",
                        name="App",
                        lifecycle_state="ACTIVE",
                    ),
                    SimpleNamespace(
                        id="ocid1.compartment.oc1..deleted",
                        name="Deleted",
                        lifecycle_state="DELETED",
                    ),
                ],
                headers={"opc-next-page": "next"},
            ),
            SimpleNamespace(
                data=[
                    SimpleNamespace(
                        id="ocid1.compartment.oc1..child2",
                        name="Data",
                        lifecycle_state="ACTIVE",
                    )
                ],
                headers={},
            ),
        ]
        self.calls = []

    def get_compartment(self, compartment_id):
        return SimpleNamespace(data=SimpleNamespace(id=compartment_id, name="Root"))

    def list_compartments(self, compartment_id, **kwargs):
        self.calls.append((compartment_id, kwargs))
        return self.pages.pop(0)


def test_discover_compartments_includes_root_and_active_children():
    client = FakeIdentityClient()
    discovery = OciCompartmentDiscovery(
        OciAuthContext(config={}),
        identity_client=client,
    )

    result = discovery.discover_compartments(
        "ocid1.compartment.oc1..root",
        include_subcompartments=True,
    )

    assert result.compartment_ids == [
        "ocid1.compartment.oc1..root",
        "ocid1.compartment.oc1..child1",
        "ocid1.compartment.oc1..child2",
    ]
    assert result.compartment_id_to_name["ocid1.compartment.oc1..root"] == "Root"
    assert result.compartment_id_to_name["ocid1.compartment.oc1..child1"] == "App"
    assert "ocid1.compartment.oc1..deleted" not in result.compartment_id_to_name
    assert client.calls[0][1]["compartment_id_in_subtree"] is True


def test_discover_compartments_can_return_only_root():
    client = FakeIdentityClient()
    discovery = OciCompartmentDiscovery(
        OciAuthContext(config={}),
        identity_client=client,
    )

    result = discovery.discover_compartments(
        "ocid1.compartment.oc1..root",
        include_subcompartments=False,
    )

    assert result.compartment_ids == ["ocid1.compartment.oc1..root"]
    assert result.compartment_id_to_name == {"ocid1.compartment.oc1..root": "Root"}
    assert client.calls == []

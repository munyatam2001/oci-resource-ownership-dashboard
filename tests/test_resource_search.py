import sys
from datetime import datetime, timezone
from types import SimpleNamespace

from oci_resource_dashboard.auth import OciAuthContext
from oci_resource_dashboard.resource_search import (
    OciResourceSearch,
    build_resource_query,
    enrich_compartment_names,
)


class FakeStructuredSearchDetails:
    def __init__(self, query, matching_context_type):
        self.query = query
        self.matching_context_type = matching_context_type


class FakeResourceSearchClient:
    def __init__(self):
        self.calls = []
        self.pages = [
            SimpleNamespace(
                data=SimpleNamespace(
                    items=[
                        SimpleNamespace(
                            identifier="ocid1.instance.oc1..example",
                            display_name="app-server",
                            resource_type="Instance",
                            lifecycle_state="RUNNING",
                            compartment_id="ocid1.compartment.oc1..app",
                            region="us-ashburn-1",
                            time_created=datetime(2026, 5, 1, tzinfo=timezone.utc),
                            freeform_tags={"Owner": "platform-team"},
                            defined_tags={"Operations": {"CreatedBy": "alice@example.com"}},
                        )
                    ]
                ),
                headers={"opc-next-page": "next"},
            ),
            SimpleNamespace(data=SimpleNamespace(items=[]), headers={}),
        ]

    def search_resources(self, details, page=None):
        self.calls.append((details, page))
        return self.pages.pop(0)


def test_resource_search_normalizes_paginated_resources(monkeypatch):
    fake_oci = SimpleNamespace(
        resource_search=SimpleNamespace(
            models=SimpleNamespace(StructuredSearchDetails=FakeStructuredSearchDetails),
        ),
    )
    monkeypatch.setitem(sys.modules, "oci", fake_oci)
    client = FakeResourceSearchClient()
    search = OciResourceSearch(
        OciAuthContext(config={"region": "us-ashburn-1"}),
        compartment_id_to_name={"ocid1.compartment.oc1..app": "App"},
        resource_search_client=client,
    )

    resources = search.search_resources(["ocid1.compartment.oc1..app"])

    assert len(resources) == 1
    assert resources[0]["resource_name"] == "app-server"
    assert resources[0]["resource_id"] == "ocid1.instance.oc1..example"
    assert resources[0]["compartment_name"] == "App"
    assert resources[0]["freeform_tags"] == {"Owner": "platform-team"}
    assert resources[0]["defined_tags"] == {
        "Operations": {"CreatedBy": "alice@example.com"}
    }
    assert client.calls[0][0].matching_context_type == "NONE"
    assert "compartmentId" in client.calls[0][0].query
    assert client.calls[1][1] == "next"


def test_enrich_compartment_names_fills_missing_names():
    resources = [{"resource_name": "vcn", "compartment_id": "ocid1.compartment.oc1..net"}]

    enriched = enrich_compartment_names(
        resources,
        {"ocid1.compartment.oc1..net": "Network"},
    )

    assert enriched[0]["compartment_name"] == "Network"
    assert resources[0].get("compartment_name") is None


def test_build_resource_query_uses_custom_query_with_compartment_placeholder():
    query = build_resource_query(
        "ocid1.compartment.oc1..app",
        "query instance resources where compartmentId = '{compartment_id}'",
    )

    assert query == "query instance resources where compartmentId = 'ocid1.compartment.oc1..app'"


def test_build_resource_query_uses_custom_query_without_placeholder():
    query = build_resource_query(
        "ocid1.compartment.oc1..app",
        "query bucket resources",
    )

    assert query == "query bucket resources"

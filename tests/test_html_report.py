from datetime import datetime, timezone

from oci_resource_dashboard.compliance import load_mandatory_tags
from oci_resource_dashboard.html_report import HTML_FILENAME, write_html_dashboard
from oci_resource_dashboard.resource_search import sample_resources


def _render_dashboard(tmp_path):
    tags = load_mandatory_tags("config/mandatory_tags.example.yaml")
    return write_html_dashboard(
        sample_resources(),
        tags,
        tmp_path,
        region="us-ashburn-1",
        root_compartment_id="ocid1.compartment.oc1..example",
        generated_at=datetime(2026, 5, 21, 12, 0, tzinfo=timezone.utc),
    )


def test_html_file_is_created(tmp_path):
    path = _render_dashboard(tmp_path)

    assert path == tmp_path / HTML_FILENAME
    assert path.exists()


def test_dashboard_contains_summary_metrics(tmp_path):
    html = _render_dashboard(tmp_path).read_text(encoding="utf-8")

    assert "Total Resources" in html
    assert "Compliant Resources" in html
    assert "Non-Compliant Resources" in html
    assert "60%" in html
    assert "Resources with CreatedBy" in html
    assert "Resources with Owner" in html
    assert "Resources with NoShutDown" in html
    assert "Resources with Oracle CreatedOn" in html
    assert "Unique Owners" in html
    assert "Unique Creators" in html


def test_dashboard_contains_tag_based_attribution_note(tmp_path):
    html = _render_dashboard(tmp_path).read_text(encoding="utf-8")

    assert "Attribution is tag-based only" in html
    assert "OCI Audit is not used" in html
    assert "Current mandatory ownership tags: CreatedBy and Owner" in html
    assert "Tag-based ownership and compliance visibility" in html


def test_dashboard_contains_sample_resource_names(tmp_path):
    html = _render_dashboard(tmp_path).read_text(encoding="utf-8")

    assert "prod-api-01" in html
    assert "prod-app-subnet" in html
    assert "audit-log-bucket" in html
    assert "dev-data-volume" in html
    assert "legacy-vcn" in html


def test_dashboard_contains_existing_tag_usage_section(tmp_path):
    html = _render_dashboard(tmp_path).read_text(encoding="utf-8")

    assert "Existing Tag Usage" in html
    assert "Potential Mapping Hints" in html
    assert "Operations.CreatedBy" in html


def test_dashboard_contains_compliance_progress_indicator(tmp_path):
    html = _render_dashboard(tmp_path).read_text(encoding="utf-8")

    assert "Ownership Compliance Progress" in html
    assert "progress-track" in html
    assert "aria-label=\"60% compliant\"" in html


def test_dashboard_contains_ownership_coverage_section(tmp_path):
    html = _render_dashboard(tmp_path).read_text(encoding="utf-8")

    assert "Ownership Coverage" in html
    assert "Full compliance requires both CreatedBy and Owner" in html
    assert "Resources missing only Owner" in html


def test_dashboard_contains_filter_toolbar_controls(tmp_path):
    html = _render_dashboard(tmp_path).read_text(encoding="utf-8")

    assert "inventoryFilters" in html
    assert "inventoryResourceType" in html
    assert "inventoryCompartment" in html
    assert "inventoryCompliance" in html
    assert "inventoryMissingTag" in html
    assert "inventoryNoShutDown" in html
    assert "inventoryCreatedFrom" in html
    assert "inventoryCreatedTo" in html
    assert "inventoryClearFilters" in html
    assert "inventoryRowCount" in html


def test_dashboard_contains_missing_table_filters_and_quick_chips(tmp_path):
    html = _render_dashboard(tmp_path).read_text(encoding="utf-8")

    assert "missingFilters" in html
    assert "missingResourceType" in html
    assert "missingCompartment" in html
    assert "missingMissingTag" in html
    assert "missingNoShutDown" in html
    assert "missingClearFilters" in html
    assert "missingRowCount" in html
    assert "Missing Owner" in html
    assert "Missing CreatedBy" in html
    assert "Has CreatedBy but Missing Owner" in html
    assert "Missing Both Ownership Tags" in html
    assert "Has Both Ownership Tags" in html
    assert "Has CreatedBy" in html
    assert "NoShutDown = Yes" in html
    assert "Created in last 30 days" in html
    assert "Inactive resources" in html


def test_dashboard_contains_operational_insights(tmp_path):
    html = _render_dashboard(tmp_path).read_text(encoding="utf-8")

    assert "Oracle-Tags.CreatedBy is being used as the CreatedBy ownership signal." in html
    assert "NoShutDown is present on 1 resources." in html
    assert "Oracle-Tags.CreatedOn is available for creation-date analysis." in html


def test_dashboard_uses_no_external_cdn_references(tmp_path):
    html = _render_dashboard(tmp_path).read_text(encoding="utf-8").lower()

    assert "https://" not in html
    assert "http://" not in html
    assert "cdn" not in html
    assert "unpkg" not in html

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
    assert "40%" in html
    assert "Unique Owners" in html
    assert "Unique Creators" in html


def test_dashboard_contains_tag_based_attribution_note(tmp_path):
    html = _render_dashboard(tmp_path).read_text(encoding="utf-8")

    assert "Attribution is tag-based only" in html
    assert "not OCI Audit" in html


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


def test_dashboard_uses_no_external_cdn_references(tmp_path):
    html = _render_dashboard(tmp_path).read_text(encoding="utf-8").lower()

    assert "https://" not in html
    assert "http://" not in html
    assert "cdn" not in html
    assert "unpkg" not in html

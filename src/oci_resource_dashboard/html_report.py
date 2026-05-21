"""Self-contained static HTML dashboard generation."""

from collections.abc import Iterable
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Any, Mapping, Optional

from .compliance import evaluate_resource_compliance, summarize_compliance
from .csv_report import build_inventory_row
from .models import MandatoryTag
from .tag_diagnostics import collect_tag_usage, find_mapping_hints


HTML_FILENAME = "oci_resource_ownership_dashboard.html"


def _short_ocid(value: Any) -> str:
    text = str(value or "")
    if len(text) <= 28:
        return text
    return f"{text[:18]}...{text[-8:]}"


def _fmt_percent(value: float) -> str:
    if value == int(value):
        return f"{int(value)}%"
    return f"{value:.2f}%"


def _metric_card(label: str, value: Any) -> str:
    return (
        '<div class="metric-card">'
        f'<div class="metric-value">{escape(str(value))}</div>'
        f'<div class="metric-label">{escape(label)}</div>'
        "</div>"
    )


def _table(headers: list[str], rows: list[list[Any]], table_id: Optional[str] = None) -> str:
    id_attr = f' id="{escape(table_id)}"' if table_id else ""
    thead = "".join(f"<th>{escape(header)}</th>" for header in headers)
    body_rows = []
    for row in rows:
        cells = "".join(f"<td>{escape(str(value))}</td>" for value in row)
        body_rows.append(f"<tr>{cells}</tr>")
    tbody = "".join(body_rows)
    return f"<table{id_attr}><thead><tr>{thead}</tr></thead><tbody>{tbody}</tbody></table>"


def _resource_value(resource: Mapping[str, Any], *keys: str) -> str:
    for key in keys:
        value = resource.get(key)
        if value is not None:
            return str(value)
    return ""


def _render_dashboard_html(
    resources: list[Mapping[str, Any]],
    mandatory_tags: tuple[MandatoryTag, ...],
    region: str,
    root_compartment_id: str,
    generated_at: datetime,
) -> str:
    summary = summarize_compliance(resources, mandatory_tags)
    inventory_rows = [build_inventory_row(resource, mandatory_tags) for resource in resources]
    evaluated = [evaluate_resource_compliance(resource, mandatory_tags) for resource in resources]

    unique_owners = {
        str(result.present_tags["Owner"])
        for result in evaluated
        if result.present_tags.get("Owner")
    }
    unique_creators = {
        str(result.present_tags["CreatedBy"])
        for result in evaluated
        if result.present_tags.get("CreatedBy")
    }

    tag_rows = []
    for tag in mandatory_tags:
        present = summary.present_count_by_tag[tag.canonical_name]
        missing = summary.missing_count_by_tag[tag.canonical_name]
        percent = 100.0
        if summary.total_resources:
            percent = round((present / summary.total_resources) * 100, 2)
        tag_rows.append([tag.canonical_name, present, missing, _fmt_percent(percent)])

    missing_resource_rows = []
    for row in inventory_rows:
        if row["is_compliant"] == "false":
            missing_resource_rows.append(
                [
                    row["resource_name"],
                    row["resource_type"],
                    row["compartment_name"],
                    row["lifecycle_state"],
                    row["Owner"] or "Unknown",
                    row["CreatedBy"] or "Unknown",
                    row["missing_tags"],
                    _short_ocid(row["resource_id"]),
                ]
            )

    full_inventory_rows = [
        [
            row["resource_name"],
            row["resource_type"],
            row["compartment_name"],
            row["lifecycle_state"],
            row["CreatedBy"] or "Unknown",
            row["Owner"] or "Unknown",
            row["CostCenter"] or "Unknown",
            row["Environment"] or "Unknown",
            row["Application"] or "Unknown",
            _fmt_percent(float(row["compliance_percent"])),
        ]
        for row in inventory_rows
    ]
    tag_usage = collect_tag_usage(resources)
    tag_usage_rows = [
        [
            usage.tag_type,
            usage.tag_key,
            usage.resources_with_key,
            usage.resources_with_nonempty_value,
            "; ".join(usage.example_values),
        ]
        for usage in tag_usage
    ]
    mapping_hint_rows = [
        [
            row["mandatory_tag"],
            row["candidate_existing_key"],
            row["tag_type"],
            row["resources_with_key"],
            row["example_values"].replace(";", "; "),
        ]
        for row in find_mapping_hints(tag_usage)
    ]

    generated_text = generated_at.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    cards = "".join(
        [
            _metric_card("Total Resources", summary.total_resources),
            _metric_card("Compliant Resources", summary.compliant_resources),
            _metric_card("Non-Compliant Resources", summary.noncompliant_resources),
            _metric_card("Compliance", _fmt_percent(summary.compliance_percent)),
            _metric_card("Unique Owners", len(unique_owners)),
            _metric_card("Unique Creators", len(unique_creators)),
        ]
    )

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>OCI Resource Ownership Dashboard</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f5f7fb;
      --surface: #ffffff;
      --line: #d9e1ec;
      --text: #202936;
      --muted: #5f6f82;
      --accent: #006b8f;
      --accent-soft: #e5f4f8;
      --danger: #9f2a2a;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Arial, Helvetica, sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.45;
    }}
    header {{
      background: #182332;
      color: #ffffff;
      padding: 28px 32px;
    }}
    h1, h2 {{ margin: 0; }}
    h1 {{ font-size: 30px; font-weight: 700; }}
    h2 {{ font-size: 20px; margin-bottom: 14px; }}
    main {{ padding: 24px 32px 40px; }}
    .meta {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 8px 20px;
      margin-top: 16px;
      color: #dce7f2;
      font-size: 14px;
    }}
    .note {{
      margin-top: 16px;
      padding: 10px 12px;
      background: rgba(255, 255, 255, 0.12);
      border-left: 4px solid #6fd1e6;
      max-width: 960px;
    }}
    section {{ margin-top: 24px; }}
    .cards {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
      gap: 14px;
    }}
    .metric-card {{
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 16px;
    }}
    .metric-value {{ font-size: 28px; font-weight: 700; color: var(--accent); }}
    .metric-label {{ margin-top: 4px; color: var(--muted); font-size: 13px; }}
    .panel {{
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 16px;
      overflow-x: auto;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      min-width: 780px;
      font-size: 14px;
    }}
    th, td {{
      border-bottom: 1px solid var(--line);
      padding: 10px 12px;
      text-align: left;
      vertical-align: top;
    }}
    th {{
      background: var(--accent-soft);
      color: #173444;
      font-weight: 700;
    }}
    tr:hover td {{ background: #f8fbfd; }}
    .search-row {{
      display: flex;
      justify-content: flex-end;
      margin-bottom: 12px;
    }}
    input[type="search"] {{
      width: min(420px, 100%);
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 10px 12px;
      font-size: 14px;
    }}
    .empty {{
      color: var(--muted);
      padding: 10px 0;
    }}
  </style>
</head>
<body>
  <header>
    <h1>OCI Resource Ownership Dashboard</h1>
    <div class="meta">
      <div><strong>Generated:</strong> {escape(generated_text)}</div>
      <div><strong>Region:</strong> {escape(region)}</div>
      <div><strong>Root compartment:</strong> {escape(root_compartment_id)}</div>
    </div>
    <div class="note">Attribution is tag-based only. CreatedBy and Owner are derived from resource tags, not OCI Audit.</div>
  </header>
  <main>
    <section>
      <div class="cards">{cards}</div>
    </section>
    <section class="panel">
      <h2>Mandatory Tag Compliance</h2>
      {_table(["Tag", "Present Count", "Missing Count", "Compliance %"], tag_rows)}
    </section>
    <section class="panel">
      <h2>Resources Missing Mandatory Tags</h2>
      {_table(["Resource Name", "Type", "Compartment Name", "Lifecycle State", "Owner", "Created By", "Missing Tags", "Shortened OCID"], missing_resource_rows) if missing_resource_rows else '<div class="empty">No resources are missing mandatory tags.</div>'}
    </section>
    <section class="panel">
      <h2>Existing Tag Usage</h2>
      {_table(["Tag Type", "Tag Key", "Resources With Key", "Non-Empty Values", "Example Values"], tag_usage_rows) if tag_usage_rows else '<div class="empty">No tags were found on the scanned resources.</div>'}
    </section>
    <section class="panel">
      <h2>Potential Mapping Hints</h2>
      {_table(["Mandatory Tag", "Candidate Existing Key", "Tag Type", "Resources With Key", "Example Values"], mapping_hint_rows) if mapping_hint_rows else '<div class="empty">No likely mapping hints were found.</div>'}
    </section>
    <section class="panel">
      <h2>Full Resource Inventory</h2>
      <div class="search-row">
        <input id="inventorySearch" type="search" placeholder="Search inventory">
      </div>
      {_table(["Resource", "Type", "Compartment", "State", "CreatedBy", "Owner", "CostCenter", "Environment", "Application", "Compliance %"], full_inventory_rows, "inventoryTable")}
    </section>
  </main>
  <script>
    (function () {{
      var search = document.getElementById("inventorySearch");
      var table = document.getElementById("inventoryTable");
      if (!search || !table) {{ return; }}
      var rows = Array.prototype.slice.call(table.querySelectorAll("tbody tr"));
      search.addEventListener("input", function () {{
        var needle = search.value.toLowerCase();
        rows.forEach(function (row) {{
          row.style.display = row.textContent.toLowerCase().indexOf(needle) === -1 ? "none" : "";
        }});
      }});
    }})();
  </script>
</body>
</html>
"""


def write_html_dashboard(
    resources: Iterable[Mapping[str, Any]],
    mandatory_tags: Iterable[MandatoryTag],
    output_dir: Path,
    region: str,
    root_compartment_id: str,
    generated_at: Optional[datetime] = None,
) -> Path:
    """Write the self-contained HTML dashboard and return its path."""

    output_dir.mkdir(parents=True, exist_ok=True)
    resource_list = list(resources)
    tags = tuple(mandatory_tags)
    timestamp = generated_at or datetime.now(timezone.utc)
    output_path = output_dir / HTML_FILENAME
    output_path.write_text(
        _render_dashboard_html(resource_list, tags, region, root_compartment_id, timestamp),
        encoding="utf-8",
    )
    return output_path

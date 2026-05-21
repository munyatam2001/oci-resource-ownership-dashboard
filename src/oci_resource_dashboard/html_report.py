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


def _title_cell(value: Any, css_class: str = "truncate") -> str:
    text = str(value or "")
    return f'<span class="{css_class}" title="{escape(text)}">{escape(text)}</span>'


def _short_title_cell(value: Any, css_class: str = "ocid") -> str:
    text = str(value or "")
    return f'<span class="{css_class}" title="{escape(text)}">{escape(_short_ocid(text))}</span>'


def _badge(value: Any, kind: str = "neutral") -> str:
    text = str(value or "Unknown")
    return f'<span class="badge badge-{escape(kind)}" title="{escape(text)}">{escape(text)}</span>'


def _tag_badges(value: str) -> str:
    tags = [tag for tag in value.split(";") if tag]
    if not tags:
        return ""
    return " ".join(_badge(tag, "missing") for tag in tags)


def _metric_card(label: str, value: Any, detail: str = "") -> str:
    return (
        '<div class="metric-card">'
        f'<div class="metric-value">{escape(str(value))}</div>'
        f'<div class="metric-label">{escape(label)}</div>'
        f'<div class="metric-detail">{escape(detail)}</div>'
        "</div>"
    )


def _table(
    headers: list[str],
    rows: list[list[Any]],
    table_id: Optional[str] = None,
    raw: bool = False,
) -> str:
    id_attr = f' id="{escape(table_id)}"' if table_id else ""
    thead = "".join(f"<th>{escape(header)}</th>" for header in headers)
    body_rows = []
    for row in rows:
        cells = "".join(f"<td>{value if raw else escape(str(value))}</td>" for value in row)
        body_rows.append(f"<tr>{cells}</tr>")
    tbody = "".join(body_rows)
    return f"<table{id_attr}><thead><tr>{thead}</tr></thead><tbody>{tbody}</tbody></table>"


def _state_badge(state: str) -> str:
    normalized = state.upper()
    if normalized in {"RUNNING", "ACTIVE", "AVAILABLE"}:
        return _badge(state, "good")
    if normalized in {"STOPPED", "TERMINATED", "DELETED", "FAILED"}:
        return _badge(state, "bad")
    return _badge(state or "Unknown", "neutral")


def _compliance_badge(percent: float) -> str:
    if percent >= 100:
        return _badge(_fmt_percent(percent), "good")
    if percent <= 0:
        return _badge(_fmt_percent(percent), "bad")
    return _badge(_fmt_percent(percent), "warn")


def _insights(
    summary_missing: dict[str, int],
    total_resources: int,
    mapping_hint_rows: list[dict[str, Any]],
) -> list[str]:
    insights: list[str] = []
    if summary_missing:
        tag, missing_count = max(summary_missing.items(), key=lambda item: item[1])
        if missing_count:
            insights.append(f"Most resources are missing {tag}: {missing_count} of {total_resources}.")

    created_by_hints = [
        row for row in mapping_hint_rows if row["mandatory_tag"] == "CreatedBy"
    ]
    if created_by_hints:
        oracle_hint = next(
            (
                row
                for row in created_by_hints
                if row["candidate_existing_key"] == "Oracle-Tags.CreatedBy"
            ),
            None,
        )
        top_hint = oracle_hint or max(
            created_by_hints,
            key=lambda row: int(row["resources_with_key"]),
        )
        insights.append(
            f"CreatedBy appears in existing tags such as {top_hint['candidate_existing_key']}."
        )

    if mapping_hint_rows:
        insights.append("Use Potential Mapping Hints to update tag aliases.")

    if not insights:
        insights.append("Ownership tags are easy to interpret for the current scan.")
    return insights


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
    tag_names = [tag.canonical_name for tag in mandatory_tags]

    resources_with_created_by = summary.present_count_by_tag.get("CreatedBy", 0)
    resources_with_owner = summary.present_count_by_tag.get("Owner", 0)
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
        tag_rows.append(
            [
                _badge(tag.canonical_name, "tag"),
                present,
                missing,
                _compliance_badge(percent),
            ]
        )

    missing_resource_rows = []
    for row in inventory_rows:
        if row["is_compliant"] == "false":
            missing_resource_rows.append(
                [
                    _title_cell(row["resource_name"]),
                    _title_cell(row["resource_type"], "compact"),
                    _title_cell(row["compartment_name"]),
                    _state_badge(row["lifecycle_state"]),
                    _title_cell(row.get("Owner") or "Unknown"),
                    _title_cell(row.get("CreatedBy") or "Unknown"),
                    _tag_badges(row["missing_tags"]),
                    _short_title_cell(row["resource_id"]),
                ]
            )

    full_inventory_rows = []
    for row in inventory_rows:
        resource_cells = [
            _title_cell(row["resource_name"]),
            _title_cell(row["resource_type"], "compact"),
            _title_cell(row["compartment_name"]),
            _state_badge(row["lifecycle_state"]),
        ]
        tag_cells = [_title_cell(row.get(tag_name) or "Unknown") for tag_name in tag_names]
        full_inventory_rows.append(
            [
                *resource_cells,
                *tag_cells,
                _compliance_badge(float(row["compliance_percent"])),
            ]
        )

    tag_usage = collect_tag_usage(resources)
    tag_usage_rows = [
        [
            _badge(usage.tag_type, "tag"),
            _title_cell(usage.tag_key),
            usage.resources_with_key,
            usage.resources_with_nonempty_value,
            _title_cell("; ".join(usage.example_values), "examples"),
        ]
        for usage in tag_usage
    ]
    mapping_hint_data = find_mapping_hints(tag_usage)
    mapping_hint_rows = [
        [
            _badge(row["mandatory_tag"], "tag"),
            _title_cell(row["candidate_existing_key"]),
            _badge(row["tag_type"], "tag"),
            row["resources_with_key"],
            _title_cell(row["example_values"].replace(";", "; "), "examples"),
        ]
        for row in mapping_hint_data
    ]

    generated_text = generated_at.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    cards = "".join(
        [
            _metric_card("Total Resources", summary.total_resources, "Resources in scope"),
            _metric_card("Compliant Resources", summary.compliant_resources, "Have CreatedBy and Owner"),
            _metric_card("Non-Compliant Resources", summary.noncompliant_resources, "Missing ownership tags"),
            _metric_card("Compliance %", _fmt_percent(summary.compliance_percent), "Mandatory ownership coverage"),
            _metric_card("Resources with CreatedBy", resources_with_created_by, "Tag-derived creator signal"),
            _metric_card("Resources with Owner", resources_with_owner, "Tag-derived owner signal"),
            _metric_card("Unique Owners", len(unique_owners), "Distinct tag-derived owners"),
            _metric_card("Unique Creators", len(unique_creators), "Distinct tag-derived creators"),
        ]
    )
    progress_value = max(0.0, min(100.0, float(summary.compliance_percent)))
    insight_items = "".join(f"<li>{escape(insight)}</li>" for insight in _insights(summary.missing_count_by_tag, summary.total_resources, mapping_hint_data))
    mandatory_scope = " and ".join(tag_names) if tag_names else "none"

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>OCI Resource Ownership Dashboard</title>
  <style>
    :root {{
      --bg: #eef3f8;
      --surface: #ffffff;
      --surface-soft: #f8fafc;
      --line: #d9e2ec;
      --text: #182231;
      --muted: #637083;
      --accent: #176b87;
      --accent-strong: #0f4e63;
      --good: #19744b;
      --good-bg: #e8f6ef;
      --warn: #9a6200;
      --warn-bg: #fff3d8;
      --bad: #a33a36;
      --bad-bg: #fde9e7;
      --shadow: 0 16px 40px rgba(24, 34, 49, 0.10);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.45;
    }}
    header {{
      background: linear-gradient(135deg, #17364a 0%, #245b6e 100%);
      color: #fff;
      padding: 34px 32px 92px;
    }}
    h1, h2, p {{ margin-top: 0; }}
    h1 {{ margin-bottom: 10px; font-size: 34px; letter-spacing: 0; }}
    .subtitle {{ margin: 0 0 16px; color: #dce9f1; font-size: 16px; }}
    h2 {{ margin-bottom: 6px; font-size: 20px; }}
    main {{ margin-top: -68px; padding: 0 32px 42px; }}
    .header-grid {{
      display: grid;
      grid-template-columns: minmax(0, 1.8fr) minmax(280px, 0.9fr);
      gap: 22px;
      align-items: end;
    }}
    .meta {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 8px 18px;
      color: #dce9f1;
      font-size: 14px;
    }}
    .scope-card {{
      background: rgba(255, 255, 255, 0.13);
      border: 1px solid rgba(255, 255, 255, 0.24);
      border-radius: 18px;
      padding: 18px;
      box-shadow: var(--shadow);
    }}
    .scope-card p {{ margin: 0 0 8px; }}
    .dashboard-grid {{
      display: grid;
      gap: 18px;
    }}
    .cards {{
      display: grid;
      grid-template-columns: repeat(6, minmax(140px, 1fr));
      gap: 14px;
    }}
    .metric-card, .panel, .insight-panel {{
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 18px;
      box-shadow: var(--shadow);
    }}
    .metric-card {{ padding: 18px; min-height: 118px; }}
    .metric-value {{ font-size: 30px; font-weight: 760; color: var(--accent-strong); }}
    .metric-label {{ margin-top: 6px; color: var(--text); font-size: 13px; font-weight: 700; }}
    .metric-detail {{ margin-top: 4px; color: var(--muted); font-size: 12px; }}
    .progress-card {{ padding: 18px; }}
    .progress-head {{ display: flex; justify-content: space-between; gap: 18px; align-items: center; }}
    .progress-track {{
      height: 14px;
      margin-top: 14px;
      background: #dbe5ed;
      border-radius: 999px;
      overflow: hidden;
    }}
    .progress-fill {{
      width: {progress_value:.2f}%;
      height: 100%;
      background: linear-gradient(90deg, #2c9b74, #176b87);
    }}
    .panel {{ padding: 20px; overflow: hidden; }}
    .section-copy {{ color: var(--muted); margin-bottom: 14px; max-width: 920px; }}
    .table-wrap {{ overflow: auto; max-height: 560px; border: 1px solid var(--line); border-radius: 14px; }}
    table {{ width: 100%; border-collapse: separate; border-spacing: 0; min-width: 820px; font-size: 13px; }}
    th, td {{ border-bottom: 1px solid var(--line); padding: 11px 12px; text-align: left; vertical-align: top; }}
    th {{
      position: sticky;
      top: 0;
      z-index: 2;
      background: var(--surface-soft);
      color: #304154;
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.02em;
    }}
    tr:hover td {{ background: #fbfdff; }}
    .badge {{
      display: inline-flex;
      align-items: center;
      max-width: 260px;
      padding: 4px 8px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 700;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      vertical-align: middle;
    }}
    .badge-good {{ color: var(--good); background: var(--good-bg); }}
    .badge-warn {{ color: var(--warn); background: var(--warn-bg); }}
    .badge-bad, .badge-missing {{ color: var(--bad); background: var(--bad-bg); }}
    .badge-tag, .badge-neutral {{ color: var(--accent-strong); background: #e7f2f6; }}
    .truncate, .compact, .examples, .ocid {{
      display: inline-block;
      max-width: 280px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }}
    .compact {{ max-width: 140px; }}
    .examples {{ max-width: 420px; white-space: normal; }}
    .ocid {{ max-width: 180px; color: var(--muted); font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 12px; }}
    .header-ocid {{
      display: inline-block;
      max-width: 360px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      vertical-align: bottom;
      color: #fff;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 13px;
    }}
    .insight-panel {{ padding: 18px 20px; background: #fffdf8; border-color: #f0dfb7; }}
    .insight-panel ul {{ margin: 10px 0 0; padding-left: 20px; color: #4b3b18; }}
    .search-row {{ display: flex; justify-content: flex-end; margin-bottom: 12px; }}
    input[type="search"] {{
      width: min(420px, 100%);
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 11px 14px;
      font-size: 14px;
      background: #fff;
    }}
    .empty {{ color: var(--muted); padding: 12px 0; }}
    @media (max-width: 1200px) {{ .cards {{ grid-template-columns: repeat(3, minmax(160px, 1fr)); }} }}
    @media (max-width: 760px) {{
      header {{ padding: 24px 18px 82px; }}
      main {{ padding: 0 14px 28px; }}
      .header-grid {{ grid-template-columns: 1fr; }}
      .cards {{ grid-template-columns: 1fr; }}
      h1 {{ font-size: 27px; }}
    }}
  </style>
</head>
<body>
  <header>
    <div class="header-grid">
      <div>
        <h1>OCI Resource Ownership Dashboard</h1>
        <p class="subtitle">Tag-based ownership and compliance visibility</p>
        <div class="meta">
          <div><strong>Generated:</strong> {escape(generated_text)}</div>
          <div><strong>Region:</strong> {escape(region)}</div>
          <div><strong>Root compartment:</strong> {_short_title_cell(root_compartment_id, "header-ocid")}</div>
        </div>
      </div>
      <div class="scope-card">
        <p><strong>Current mandatory ownership tags: {escape(mandatory_scope)}</strong></p>
        <p>Attribution is tag-based only. OCI Audit is not used.</p>
      </div>
    </div>
  </header>
  <main>
    <div class="dashboard-grid">
      <section class="cards">{cards}</section>
      <section class="panel progress-card">
        <div class="progress-head">
          <div>
            <h2>Ownership Compliance Progress</h2>
            <p class="section-copy">Accessible value: {_fmt_percent(summary.compliance_percent)} compliant.</p>
          </div>
          {_compliance_badge(summary.compliance_percent)}
        </div>
        <div class="progress-track" role="img" aria-label="{_fmt_percent(summary.compliance_percent)} compliant">
          <div class="progress-fill"></div>
        </div>
      </section>
      <section class="insight-panel">
        <h2>Insights</h2>
        <ul>{insight_items}</ul>
      </section>
      <section class="panel">
        <h2>Mandatory Tag Compliance</h2>
        <p class="section-copy">Coverage for the current ownership tag model. These counts drive resource compliance.</p>
        <div class="table-wrap">{_table(["Tag", "Present Count", "Missing Count", "Compliance"], tag_rows, raw=True)}</div>
      </section>
      <section class="panel">
        <h2>Resources Missing Mandatory Tags</h2>
        <p class="section-copy">Resources below are missing CreatedBy, Owner, or both. OCIDs are shortened visually but available on hover.</p>
        <div class="table-wrap">{_table(["Resource Name", "Type", "Compartment Name", "Lifecycle State", "Owner", "Created By", "Missing Tags", "Shortened OCID"], missing_resource_rows, raw=True) if missing_resource_rows else '<div class="empty">No resources are missing mandatory tags.</div>'}</div>
      </section>
      <section class="panel">
        <h2>Existing Tag Usage</h2>
        <p class="section-copy">All tag keys discovered on scanned resources, including tags that are not mandatory. Use this to understand the tenancy vocabulary.</p>
        <div class="table-wrap">{_table(["Tag Type", "Tag Key", "Resources With Key", "Non-Empty Values", "Example Values"], tag_usage_rows, raw=True) if tag_usage_rows else '<div class="empty">No tags were found on the scanned resources.</div>'}</div>
      </section>
      <section class="panel">
        <h2>Potential Mapping Hints</h2>
        <p class="section-copy">Likely existing keys that can be mapped into the mandatory ownership model by adding aliases.</p>
        <div class="table-wrap">{_table(["Mandatory Tag", "Candidate Existing Key", "Tag Type", "Resources With Key", "Example Values"], mapping_hint_rows, raw=True) if mapping_hint_rows else '<div class="empty">No likely mapping hints were found.</div>'}</div>
      </section>
      <section class="panel">
        <h2>Full Resource Inventory</h2>
        <p class="section-copy">Searchable inventory with active mandatory ownership tags and compliance status.</p>
        <div class="search-row">
          <input id="inventorySearch" type="search" placeholder="Search inventory">
        </div>
        <div class="table-wrap">{_table(["Resource", "Type", "Compartment", "State", *tag_names, "Compliance"], full_inventory_rows, "inventoryTable", raw=True)}</div>
      </section>
    </div>
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

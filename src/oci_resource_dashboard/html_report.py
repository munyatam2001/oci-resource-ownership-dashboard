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
DISPLAY_ROW_LIMIT = 500


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


def _select_options(values: Iterable[str]) -> str:
    options = ['<option value="">All</option>']
    for value in sorted({str(item) for item in values if str(item)}):
        options.append(f'<option value="{escape(value)}">{escape(value)}</option>')
    return "".join(options)


def _filter_toolbar(
    prefix: str,
    resource_types: Iterable[str],
    compartments: Iterable[str],
    states: Iterable[str],
    created_by_values: Iterable[str],
    owner_values: Iterable[str],
    include_dates: bool,
) -> str:
    date_controls = ""
    if include_dates:
        date_controls = f"""
          <label>CreatedOn From<input id="{prefix}CreatedFrom" data-filter="{prefix}" data-field="createdonFrom" type="date"></label>
          <label>CreatedOn To<input id="{prefix}CreatedTo" data-filter="{prefix}" data-field="createdonTo" type="date"></label>
        """
    compliance_control = ""
    if prefix == "inventory":
        compliance_control = f"""
          <label>Compliance
            <select id="{prefix}Compliance" data-filter="{prefix}" data-field="compliance">
              <option value="">All</option>
              <option value="compliant">Compliant</option>
              <option value="non-compliant">Non-Compliant</option>
            </select>
          </label>
        """
    return f"""
      <div class="filter-toolbar" id="{prefix}Filters">
        <label>Search<input id="{prefix}Search" data-filter="{prefix}" data-field="search" type="search" placeholder="Search rows"></label>
        <label>Resource Type<select id="{prefix}ResourceType" data-filter="{prefix}" data-field="type">{_select_options(resource_types)}</select></label>
        <label>Compartment<select id="{prefix}Compartment" data-filter="{prefix}" data-field="compartment">{_select_options(compartments)}</select></label>
        <label>Lifecycle State<select id="{prefix}State" data-filter="{prefix}" data-field="state">{_select_options(states)}</select></label>
        {compliance_control}
        <label>Missing Tag
          <select id="{prefix}MissingTag" data-filter="{prefix}" data-field="missing">
            <option value="">All</option>
            <option value="CreatedBy">CreatedBy</option>
            <option value="Owner">Owner</option>
          </select>
        </label>
        <label>CreatedBy<select id="{prefix}CreatedBy" data-filter="{prefix}" data-field="createdby">{_select_options(created_by_values)}</select></label>
        <label>Owner<select id="{prefix}Owner" data-filter="{prefix}" data-field="owner">{_select_options(owner_values)}</select></label>
        <label>NoShutDown
          <select id="{prefix}NoShutDown" data-filter="{prefix}" data-field="noshutdown">
            <option value="">All</option>
            <option value="yes">Yes</option>
            <option value="blank">No/Blank</option>
          </select>
        </label>
        {date_controls}
        <button type="button" id="{prefix}ClearFilters" data-clear="{prefix}">Clear Filters</button>
        <span class="row-count" id="{prefix}RowCount">Showing 0 of 0 rows</span>
      </div>
    """


def _row_attrs(row: Mapping[str, Any]) -> str:
    status = "compliant" if row["is_compliant"] == "true" else "non-compliant"
    created_on = str(row.get("OracleCreatedOn") or "")
    created_date = created_on[:10] if len(created_on) >= 10 else ""
    values = {
        "type": row["resource_type"],
        "compartment": row["compartment_name"],
        "state": row["lifecycle_state"],
        "compliance": status,
        "missing": row["missing_tags"],
        "createdby": row.get("CreatedBy") or "",
        "owner": row.get("Owner") or "",
        "noshutdown": "yes" if str(row.get("NoShutDown") or "").casefold() == "yes" else "blank",
        "createdon": created_date,
    }
    return " ".join(f'data-{key}="{escape(str(value))}"' for key, value in values.items())


def _raw_table_with_attrs(
    headers: list[str],
    rows: list[tuple[Mapping[str, Any], list[Any]]],
    table_id: str,
) -> str:
    thead = "".join(f"<th>{escape(header)}</th>" for header in headers)
    body_rows = []
    for row_data, cells in rows:
        rendered = "".join(f"<td>{cell}</td>" for cell in cells)
        body_rows.append(f'<tr {_row_attrs(row_data)}>{rendered}</tr>')
    return f'<table id="{escape(table_id)}"><thead><tr>{thead}</tr></thead><tbody>{"".join(body_rows)}</tbody></table>'


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
    no_shutdown_count: int,
    oracle_created_on_count: int,
    oracle_created_by_mapped: bool,
) -> list[str]:
    insights: list[str] = []
    if summary_missing:
        tag, missing_count = max(summary_missing.items(), key=lambda item: item[1])
        if missing_count:
            insights.append(f"Most resources are missing {tag}: {missing_count} of {total_resources}.")

    if oracle_created_by_mapped:
        insights.append("Oracle-Tags.CreatedBy is being used as the CreatedBy ownership signal.")

    if no_shutdown_count:
        insights.append(f"NoShutDown is present on {no_shutdown_count} resources.")

    if oracle_created_on_count:
        insights.append("Oracle-Tags.CreatedOn is available for creation-date analysis.")

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
    resources_with_no_shutdown = sum(1 for row in inventory_rows if row.get("NoShutDown"))
    resources_with_oracle_created_on = sum(1 for row in inventory_rows if row.get("OracleCreatedOn"))
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

    missing_resource_rows: list[tuple[Mapping[str, Any], list[Any]]] = []
    for row in inventory_rows:
        if row["is_compliant"] == "false":
            missing_resource_rows.append(
                (row, [
                    _title_cell(row["resource_name"]),
                    _title_cell(row["resource_type"], "compact"),
                    _title_cell(row["compartment_name"]),
                    _state_badge(row["lifecycle_state"]),
                    _title_cell(row.get("CreatedBy") or "Unknown"),
                    _title_cell(row.get("Owner") or "Unknown"),
                    _title_cell(row.get("OracleCreatedOn") or "Unknown"),
                    _badge(row.get("NoShutDown") or "No/Blank", "tag" if row.get("NoShutDown") else "neutral"),
                    _tag_badges(row["missing_tags"]),
                    _short_title_cell(row["resource_id"]),
                ])
            )

    full_inventory_rows: list[tuple[Mapping[str, Any], list[Any]]] = []
    for row in inventory_rows:
        resource_cells = [
            _title_cell(row["resource_name"]),
            _title_cell(row["resource_type"], "compact"),
            _title_cell(row["compartment_name"]),
            _state_badge(row["lifecycle_state"]),
        ]
        tag_cells = [_title_cell(row.get(tag_name) or "Unknown") for tag_name in tag_names]
        full_inventory_rows.append(
            (row, [
                *resource_cells,
                *tag_cells,
                _title_cell(row.get("OracleCreatedOn") or "Unknown"),
                _badge(row.get("NoShutDown") or "No/Blank", "tag" if row.get("NoShutDown") else "neutral"),
                _compliance_badge(float(row["compliance_percent"])),
            ])
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
    oracle_created_by_mapped = any(
        row["mandatory_tag"] == "CreatedBy"
        and row["candidate_existing_key"] == "Oracle-Tags.CreatedBy"
        for row in mapping_hint_data
    )
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
            _metric_card("Resources with NoShutDown", resources_with_no_shutdown, "Operational shutdown marker"),
            _metric_card("Resources with Oracle CreatedOn", resources_with_oracle_created_on, "Creation timestamp tag"),
            _metric_card("Unique Owners", len(unique_owners), "Distinct tag-derived owners"),
            _metric_card("Unique Creators", len(unique_creators), "Distinct tag-derived creators"),
        ]
    )
    progress_value = max(0.0, min(100.0, float(summary.compliance_percent)))
    insight_items = "".join(
        f"<li>{escape(insight)}</li>"
        for insight in _insights(
            summary.missing_count_by_tag,
            summary.total_resources,
            mapping_hint_data,
            resources_with_no_shutdown,
            resources_with_oracle_created_on,
            oracle_created_by_mapped,
        )
    )
    mandatory_scope = " and ".join(tag_names) if tag_names else "none"
    displayed_inventory_rows = full_inventory_rows[:DISPLAY_ROW_LIMIT]
    displayed_missing_rows = missing_resource_rows[:DISPLAY_ROW_LIMIT]
    resource_types = [row["resource_type"] for row in inventory_rows]
    compartments = [row["compartment_name"] for row in inventory_rows]
    states = [row["lifecycle_state"] for row in inventory_rows]
    created_by_values = [row.get("CreatedBy", "") for row in inventory_rows]
    owner_values = [row.get("Owner", "") for row in inventory_rows]
    has_created_on = resources_with_oracle_created_on > 0

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
      grid-template-columns: repeat(5, minmax(140px, 1fr));
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
    .filter-toolbar {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
      gap: 10px;
      align-items: end;
      margin-bottom: 12px;
      padding: 12px;
      background: var(--surface-soft);
      border: 1px solid var(--line);
      border-radius: 14px;
    }}
    .filter-toolbar label {{ display: grid; gap: 5px; color: var(--muted); font-size: 12px; font-weight: 700; }}
    .filter-toolbar input, .filter-toolbar select {{
      min-width: 0;
      border: 1px solid var(--line);
      border-radius: 10px;
      padding: 9px 10px;
      background: #fff;
      color: var(--text);
      font-size: 13px;
    }}
    .filter-toolbar button, .quick-chip {{
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 9px 12px;
      background: #fff;
      color: var(--accent-strong);
      font-weight: 700;
      cursor: pointer;
    }}
    .row-count {{ color: var(--muted); font-size: 13px; align-self: center; }}
    .quick-filters {{ display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 12px; }}
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
        <p class="section-copy">Table display may be limited; full data is available in CSV exports.</p>
        {_filter_toolbar("missing", resource_types, compartments, states, created_by_values, owner_values, False)}
        <div class="table-wrap">{_raw_table_with_attrs(["Resource Name", "Type", "Compartment Name", "Lifecycle State", "CreatedBy", "Owner", "OracleCreatedOn", "NoShutDown", "Missing Tags", "Shortened OCID"], displayed_missing_rows, "missingTable") if missing_resource_rows else '<div class="empty">No resources are missing mandatory tags.</div>'}</div>
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
        <p class="section-copy">Table display may be limited; full data is available in CSV exports.</p>
        <div class="quick-filters">
          <button class="quick-chip" type="button" data-chip="missing-owner">Missing Owner</button>
          <button class="quick-chip" type="button" data-chip="missing-createdby">Missing CreatedBy</button>
          <button class="quick-chip" type="button" data-chip="has-createdby">Has CreatedBy</button>
          <button class="quick-chip" type="button" data-chip="noshutdown-yes">NoShutDown = Yes</button>
          <button class="quick-chip" type="button" data-chip="created-last-30" {"disabled" if not has_created_on else ""}>Created in last 30 days</button>
          <button class="quick-chip" type="button" data-chip="inactive">Inactive resources</button>
        </div>
        {_filter_toolbar("inventory", resource_types, compartments, states, created_by_values, owner_values, True)}
        <div class="table-wrap">{_raw_table_with_attrs(["Resource", "Type", "Compartment", "State", *tag_names, "OracleCreatedOn", "NoShutDown", "Compliance"], displayed_inventory_rows, "inventoryTable")}</div>
      </section>
    </div>
  </main>
  <script>
    (function () {{
      function value(id) {{
        var el = document.getElementById(id);
        return el ? el.value : "";
      }}
      function setValue(id, val) {{
        var el = document.getElementById(id);
        if (el) {{ el.value = val; }}
      }}
      function rowMatches(row, prefix) {{
        var search = value(prefix + "Search").toLowerCase();
        if (search && row.textContent.toLowerCase().indexOf(search) === -1) {{ return false; }}
        var checks = [
          ["ResourceType", "type"],
          ["Compartment", "compartment"],
          ["State", "state"],
          ["Compliance", "compliance"],
          ["CreatedBy", "createdby"],
          ["Owner", "owner"]
        ];
        for (var i = 0; i < checks.length; i++) {{
          var wanted = value(prefix + checks[i][0]);
          if (wanted && row.dataset[checks[i][1]] !== wanted) {{ return false; }}
        }}
        var missing = value(prefix + "MissingTag");
        if (missing && row.dataset.missing.indexOf(missing) === -1) {{ return false; }}
        var noShutdown = value(prefix + "NoShutDown");
        if (noShutdown && row.dataset.noshutdown !== noShutdown) {{ return false; }}
        var from = value(prefix + "CreatedFrom");
        var to = value(prefix + "CreatedTo");
        if (from && (!row.dataset.createdon || row.dataset.createdon < from)) {{ return false; }}
        if (to && (!row.dataset.createdon || row.dataset.createdon > to)) {{ return false; }}
        return true;
      }}
      function applyFilters(prefix) {{
        var table = document.getElementById(prefix + "Table");
        if (!table) {{ return; }}
        var rows = Array.prototype.slice.call(table.querySelectorAll("tbody tr"));
        var visible = 0;
        rows.forEach(function (row) {{
          var match = rowMatches(row, prefix);
          row.style.display = match ? "" : "none";
          if (match) {{ visible += 1; }}
        }});
        var count = document.getElementById(prefix + "RowCount");
        if (count) {{ count.textContent = "Showing " + visible + " of " + rows.length + " rows"; }}
      }}
      function clearFilters(prefix) {{
        Array.prototype.slice.call(document.querySelectorAll('[data-filter="' + prefix + '"]')).forEach(function (el) {{ el.value = ""; }});
        applyFilters(prefix);
      }}
      ["inventory", "missing"].forEach(function (prefix) {{
        Array.prototype.slice.call(document.querySelectorAll('[data-filter="' + prefix + '"]')).forEach(function (el) {{
          el.addEventListener("input", function () {{ applyFilters(prefix); }});
          el.addEventListener("change", function () {{ applyFilters(prefix); }});
        }});
        var clear = document.querySelector('[data-clear="' + prefix + '"]');
        if (clear) {{ clear.addEventListener("click", function () {{ clearFilters(prefix); }}); }}
        applyFilters(prefix);
      }});
      Array.prototype.slice.call(document.querySelectorAll("[data-chip]")).forEach(function (chip) {{
        chip.addEventListener("click", function () {{
          clearFilters("inventory");
          var type = chip.dataset.chip;
          if (type === "missing-owner") {{ setValue("inventoryMissingTag", "Owner"); }}
          if (type === "missing-createdby") {{ setValue("inventoryMissingTag", "CreatedBy"); }}
          if (type === "has-createdby") {{ setValue("inventoryMissingTag", ""); setValue("inventoryCreatedBy", value("inventoryCreatedBy")); }}
          if (type === "noshutdown-yes") {{ setValue("inventoryNoShutDown", "yes"); }}
          if (type === "created-last-30") {{
            var today = new Date();
            var from = new Date(today.getTime() - 30 * 24 * 60 * 60 * 1000);
            setValue("inventoryCreatedFrom", from.toISOString().slice(0, 10));
          }}
          if (type === "inactive") {{ setValue("inventoryState", "TERMINATED"); }}
          applyFilters("inventory");
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

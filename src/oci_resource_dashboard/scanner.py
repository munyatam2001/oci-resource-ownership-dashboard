"""Scan orchestration for sample and live OCI resource discovery."""

from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Any, Optional

from .auth import AuthSettings, build_auth_context
from .compartments import OciCompartmentDiscovery
from .compliance import load_mandatory_tags
from .csv_report import write_csv_outputs
from .html_report import write_html_dashboard
from .resource_search import (
    DEFAULT_RESOURCE_QUERY,
    OciResourceSearch,
    enrich_compartment_names,
    sample_resources,
)


ATTRIBUTION_SOURCE = "resource tags only; OCI Audit is not used"


@dataclass(frozen=True)
class ScanResult:
    """Operational metadata returned after a scan."""

    mode: str
    compartments_selected: int
    total_resources_discovered: int
    resources_processed: int
    max_resources: Optional[int]
    resource_query: str
    elapsed_seconds: float
    generated_files: list[Path]

    @property
    def elapsed_text(self) -> str:
        return f"{self.elapsed_seconds:.2f}s"


class _NullConsole:
    def print(self, *_args: Any, **_kwargs: Any) -> None:
        return None


def _log(console: Any, message: str) -> None:
    console.print(f"[cyan]{message}[/cyan]")


def _validate_max_resources(max_resources: Optional[int]) -> None:
    if max_resources is not None and max_resources <= 0:
        raise ValueError("--max-resources must be greater than zero")


def _limit_resources(
    resources: list[dict[str, Any]],
    max_resources: Optional[int],
) -> list[dict[str, Any]]:
    if max_resources is None:
        return resources
    return resources[:max_resources]


def scan_resources(
    auth_method: str,
    region: str,
    compartment_id: str,
    include_subcompartments: bool,
    mandatory_tags_path: Path,
    output_dir: Path,
    sample: bool = False,
    max_resources: Optional[int] = None,
    resource_query: Optional[str] = None,
    console: Optional[Any] = None,
) -> ScanResult:
    """Run a sample or live scan and generate CSV and HTML outputs."""

    _validate_max_resources(max_resources)
    active_console = console or _NullConsole()
    started = perf_counter()
    query_used = resource_query or DEFAULT_RESOURCE_QUERY

    _log(active_console, "Loading mandatory tag configuration")
    configured_tags = load_mandatory_tags(mandatory_tags_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    if sample:
        _log(active_console, "Using in-memory sample resources")
        discovered_resources = sample_resources()
        compartment_count = len(
            {resource.get("compartment_id", "") for resource in discovered_resources}
        )
    else:
        _log(active_console, "Authenticating to OCI")
        auth_context = build_auth_context(AuthSettings(method=auth_method, region=region))

        _log(active_console, "Discovering compartments")
        compartment_result = OciCompartmentDiscovery(auth_context).discover_compartments(
            compartment_id,
            include_subcompartments,
        )
        compartment_count = len(compartment_result.compartment_ids)

        _log(active_console, "Searching resources")
        discovered_resources = OciResourceSearch(
            auth_context,
            compartment_result.compartment_id_to_name,
        ).search_resources(compartment_result.compartment_ids, resource_query=resource_query)
        discovered_resources = enrich_compartment_names(
            discovered_resources,
            compartment_result.compartment_id_to_name,
        )

    total_discovered = len(discovered_resources)
    if max_resources is not None:
        _log(active_console, f"Applying max resource limit: {max_resources}")
    resources = _limit_resources(discovered_resources, max_resources)

    _log(active_console, "Evaluating compliance")
    _log(active_console, "Collecting tag diagnostics")
    _log(active_console, "Writing CSVs")
    generated_files = write_csv_outputs(resources, configured_tags, output_dir)

    _log(active_console, "Generating HTML")
    generated_files.append(
        write_html_dashboard(
            resources,
            configured_tags,
            output_dir,
            region=region,
            root_compartment_id=compartment_id,
        )
    )

    elapsed = perf_counter() - started
    _log(active_console, f"Completed in {elapsed:.2f}s")

    return ScanResult(
        mode="sample" if sample else "live OCI",
        compartments_selected=compartment_count,
        total_resources_discovered=total_discovered,
        resources_processed=len(resources),
        max_resources=max_resources,
        resource_query=query_used,
        elapsed_seconds=elapsed,
        generated_files=generated_files,
    )


def scan_summary_rows(result: ScanResult) -> list[tuple[str, str]]:
    """Return display-ready scan summary rows."""

    return [
        ("Mode", result.mode),
        ("Compartments Selected", str(result.compartments_selected)),
        ("Total Resources Discovered", str(result.total_resources_discovered)),
        ("Resources Processed", str(result.resources_processed)),
        ("Max Resources Limit", str(result.max_resources) if result.max_resources else "none"),
        ("Resource Query Used", result.resource_query),
        ("Elapsed Time", result.elapsed_text),
        ("Attribution Source", ATTRIBUTION_SOURCE),
    ]

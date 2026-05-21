"""Command line interface for the OCI resource dashboard generator."""

from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from .auth import AuthSettings, build_auth_context
from .compartments import OciCompartmentDiscovery
from .compliance import load_mandatory_tags
from .csv_report import write_csv_outputs
from .html_report import write_html_dashboard
from .resource_search import OciResourceSearch, enrich_compartment_names, sample_resources

console = Console()


@click.group()
def main() -> None:
    """Generate OCI resource ownership and tag compliance dashboards."""


@main.command()
@click.option(
    "--auth",
    "auth_method",
    type=click.Choice(["instance_principal", "config"]),
    required=True,
    help="Authentication mode to use when OCI discovery is implemented.",
)
@click.option("--region", required=True, help="OCI region to scan.")
@click.option("--compartment-id", required=True, help="Root compartment OCID to scan.")
@click.option(
    "--include-subcompartments",
    is_flag=True,
    help="Include child compartments in the intended scan.",
)
@click.option(
    "--mandatory-tags",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
    help="Path to mandatory tag YAML configuration.",
)
@click.option(
    "--output-dir",
    type=click.Path(file_okay=False, path_type=Path),
    required=True,
    help="Directory where CSV and HTML outputs will be written.",
)
@click.option(
    "--sample",
    is_flag=True,
    help="Use in-memory sample resources instead of calling OCI APIs.",
)
def scan(
    auth_method: str,
    region: str,
    compartment_id: str,
    include_subcompartments: bool,
    mandatory_tags: Path,
    output_dir: Path,
    sample: bool,
) -> None:
    """Generate tag-based OCI resource ownership reports."""

    configured_tags = load_mandatory_tags(mandatory_tags)
    output_dir.mkdir(parents=True, exist_ok=True)

    compartment_count = 0
    if sample:
        resources = sample_resources()
        compartment_count = len({resource.get("compartment_id", "") for resource in resources})
    else:
        auth_context = build_auth_context(AuthSettings(method=auth_method, region=region))
        compartment_result = OciCompartmentDiscovery(auth_context).discover_compartments(
            compartment_id,
            include_subcompartments,
        )
        compartment_count = len(compartment_result.compartment_ids)
        discovered_resources = OciResourceSearch(
            auth_context,
            compartment_result.compartment_id_to_name,
        ).search_resources(compartment_result.compartment_ids)
        resources = enrich_compartment_names(
            discovered_resources,
            compartment_result.compartment_id_to_name,
        )

    generated_files = write_csv_outputs(resources, configured_tags, output_dir)
    generated_files.append(
        write_html_dashboard(
            resources,
            configured_tags,
            output_dir,
            region=region,
            root_compartment_id=compartment_id,
        )
    )

    table = Table(title="OCI Resource Dashboard Scan Plan")
    table.add_column("Setting", style="bold")
    table.add_column("Value")
    table.add_row("Auth", auth_method)
    table.add_row("Region", region)
    table.add_row("Compartment ID", compartment_id)
    table.add_row("Include Subcompartments", "yes" if include_subcompartments else "no")
    table.add_row("Mandatory Tag Config", str(mandatory_tags))
    table.add_row("Mandatory Tags Loaded", str(len(configured_tags)))
    table.add_row("Output Directory", str(output_dir))
    table.add_row("Mode", "sample" if sample else "live OCI")
    table.add_row("Compartments Selected", str(compartment_count))
    table.add_row("Total Resources Discovered", str(len(resources)))
    table.add_row("Attribution Source", "resource tags only; OCI Audit is not used")

    console.print(table)

    files_table = Table(title="Generated Files")
    files_table.add_column("File", style="bold")
    files_table.add_column("Path")
    for generated_file in generated_files:
        files_table.add_row(generated_file.name, str(generated_file))
    console.print(files_table)


if __name__ == "__main__":
    main()

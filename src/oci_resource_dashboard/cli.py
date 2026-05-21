"""Command line interface for the OCI resource dashboard generator."""

from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from .compliance import load_mandatory_tags
from .csv_report import write_csv_outputs
from .resource_search import sample_resources

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
def scan(
    auth_method: str,
    region: str,
    compartment_id: str,
    include_subcompartments: bool,
    mandatory_tags: Path,
    output_dir: Path,
) -> None:
    """Prepare a tag-based resource ownership scan without calling OCI yet."""

    configured_tags = load_mandatory_tags(mandatory_tags)
    output_dir.mkdir(parents=True, exist_ok=True)
    resources = sample_resources()
    generated_files = write_csv_outputs(resources, configured_tags, output_dir)

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
    table.add_row("OCI API Calls", "not implemented in this phase")
    table.add_row("Sample Resources Evaluated", str(len(resources)))

    console.print(table)

    files_table = Table(title="Generated CSV Files")
    files_table.add_column("File", style="bold")
    files_table.add_column("Path")
    for generated_file in generated_files:
        files_table.add_row(generated_file.name, str(generated_file))
    console.print(files_table)


if __name__ == "__main__":
    main()

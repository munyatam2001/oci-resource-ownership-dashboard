"""Command line interface for the OCI resource dashboard generator."""

from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table

from .scanner import scan_resources, scan_summary_rows

console = Console()


def _validate_positive_integer(
    _ctx: click.Context,
    _param: click.Parameter,
    value: Optional[int],
) -> Optional[int]:
    if value is not None and value <= 0:
        raise click.BadParameter("must be greater than zero")
    return value


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
@click.option(
    "--max-resources",
    type=int,
    callback=_validate_positive_integer,
    help="Limit resources processed after discovery for testing.",
)
@click.option(
    "--resource-query",
    help=(
        "Override the OCI Resource Search query. Use {compartment_id} as a placeholder "
        "when the query should remain compartment-scoped."
    ),
)
def scan(
    auth_method: str,
    region: str,
    compartment_id: str,
    include_subcompartments: bool,
    mandatory_tags: Path,
    output_dir: Path,
    sample: bool,
    max_resources: Optional[int],
    resource_query: Optional[str],
) -> None:
    """Generate tag-based OCI resource ownership reports."""

    result = scan_resources(
        auth_method=auth_method,
        region=region,
        compartment_id=compartment_id,
        include_subcompartments=include_subcompartments,
        mandatory_tags_path=mandatory_tags,
        output_dir=output_dir,
        sample=sample,
        max_resources=max_resources,
        resource_query=resource_query,
        console=console,
    )

    table = Table(title="OCI Resource Dashboard Scan Summary")
    table.add_column("Setting", style="bold")
    table.add_column("Value")
    table.add_row("Auth", auth_method)
    table.add_row("Region", region)
    table.add_row("Compartment ID", compartment_id)
    table.add_row("Include Subcompartments", "yes" if include_subcompartments else "no")
    table.add_row("Mandatory Tag Config", str(mandatory_tags))
    table.add_row("Output Directory", str(output_dir))
    for setting, value in scan_summary_rows(result):
        table.add_row(setting, value)

    console.print(table)

    files_table = Table(title="Generated Files")
    files_table.add_column("File", style="bold")
    files_table.add_column("Path")
    for generated_file in result.generated_files:
        files_table.add_row(generated_file.name, str(generated_file))
    console.print(files_table)


if __name__ == "__main__":
    main()

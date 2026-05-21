"""Command line interface for the OCI resource dashboard generator."""

from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table

from .scanner import (
    scan_resources,
    scan_summary_rows,
    upload_scan_outputs,
    validate_upload_options,
)

console = Console()


def _validate_positive_integer(
    _ctx: click.Context,
    _param: click.Parameter,
    value: Optional[int],
) -> Optional[int]:
    if value is not None and value <= 0:
        raise click.BadParameter("must be greater than zero")
    return value


def _validate_upload_options(
    upload: bool,
    bucket_name: Optional[str],
    namespace: Optional[str],
) -> None:
    try:
        validate_upload_options(upload, bucket_name, namespace)
    except ValueError as exc:
        raise click.UsageError(str(exc)) from exc


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
@click.option("--upload", is_flag=True, help="Upload generated files to Object Storage.")
@click.option("--bucket-name", help="Object Storage bucket name for uploads.")
@click.option("--namespace", help="Object Storage namespace for uploads.")
@click.option("--object-prefix", help="Optional Object Storage object name prefix.")
@click.option(
    "--upload-html-only",
    is_flag=True,
    help="Upload only oci_resource_ownership_dashboard.html.",
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
    upload: bool,
    bucket_name: Optional[str],
    namespace: Optional[str],
    object_prefix: Optional[str],
    upload_html_only: bool,
) -> None:
    """Generate tag-based OCI resource ownership reports."""

    _validate_upload_options(upload, bucket_name, namespace)

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

    uploaded_objects = []
    if upload:
        uploaded_objects = upload_scan_outputs(
            result=result,
            auth_method=auth_method,
            region=region,
            bucket_name=bucket_name or "",
            namespace=namespace or "",
            object_prefix=object_prefix,
            upload_html_only=upload_html_only,
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

    if upload:
        upload_table = Table(title="Uploaded Object Storage Objects")
        upload_table.add_column("Object Name", style="bold")
        for object_name in uploaded_objects:
            upload_table.add_row(object_name)
        console.print(upload_table)


if __name__ == "__main__":
    main()

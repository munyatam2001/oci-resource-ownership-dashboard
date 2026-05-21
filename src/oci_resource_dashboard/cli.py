"""Command line interface for the OCI resource dashboard generator."""

from pathlib import Path

import click
import yaml
from rich.console import Console
from rich.table import Table

from .models import MandatoryTag

console = Console()


def load_mandatory_tags(path: Path) -> list[MandatoryTag]:
    """Load mandatory tag definitions from YAML."""

    with path.open("r", encoding="utf-8") as config_file:
        data = yaml.safe_load(config_file) or {}

    tags = data.get("mandatory_tags", [])
    if not isinstance(tags, list):
        raise click.ClickException("'mandatory_tags' must be a list")

    mandatory_tags: list[MandatoryTag] = []
    for raw_tag in tags:
        if not isinstance(raw_tag, dict):
            raise click.ClickException("Each mandatory tag must be a mapping")
        try:
            mandatory_tags.append(MandatoryTag(**raw_tag))
        except TypeError as exc:
            raise click.ClickException(f"Invalid mandatory tag entry: {raw_tag}") from exc

    return mandatory_tags


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

    console.print(table)


if __name__ == "__main__":
    main()

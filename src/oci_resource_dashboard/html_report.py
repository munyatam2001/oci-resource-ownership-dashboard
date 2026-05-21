"""Static HTML report generation interface."""

from collections.abc import Iterable
from pathlib import Path

from .models import ComplianceResult


def render_html_report(
    results: Iterable[ComplianceResult],
    output_path: Path,
) -> None:
    """Render a static HTML compliance report.

    Jinja2 templates will be introduced when reporting is implemented.
    """

    raise NotImplementedError("HTML report rendering is not implemented yet")

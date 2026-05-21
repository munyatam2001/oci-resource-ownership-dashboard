# Agent Notes

This project generates CSV and static HTML reports for OCI resource ownership and mandatory tag compliance.

## Ground Rules

- Do not use OCI Audit as the source of truth for resource creator or owner attribution.
- Creator and owner attribution must be tag-based only.
- Keep OCI discovery behind interfaces so runtime targets can move from an OCI VM to OCI Functions or a scheduled container.
- Prefer small, typed modules with focused responsibilities.
- Do not add OCI API calls until the discovery implementation phase.

## Initial Runtime

The first runtime target is an OCI VM using instance principal authentication.

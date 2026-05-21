# Architecture

The dashboard generator is organized as a small Python package with explicit boundaries around authentication, compartment discovery, resource search, compliance evaluation, and report generation.

## Data Flow

1. Load mandatory tag configuration from YAML.
2. Resolve compartments to scan.
3. Discover resources and normalize them into `ResourceRecord` objects.
4. Extract tag values from freeform and defined tags.
5. Evaluate mandatory tag compliance.
6. Generate CSV and static HTML outputs.
7. Optionally publish outputs to Object Storage.

OCI discovery is not implemented in the initial scaffold. The stubs in `auth.py`, `compartments.py`, and `resource_search.py` define the boundaries for the next phase.

## Ownership Attribution

Owner and creator attribution must be tag-based only. OCI Audit events are intentionally excluded as a source of truth because they are event history, not durable resource metadata.

## Portability

The first runtime target is an OCI VM using instance principal authentication. The package should remain suitable for OCI Functions or a scheduled container by keeping runtime dependencies and side effects isolated.

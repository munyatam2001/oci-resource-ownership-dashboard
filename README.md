# OCI Resource Ownership Dashboard

A professional static HTML dashboard generator for OCI tenancy resource ownership and mandatory tag compliance.

The project generates CSV files and a self-contained static HTML dashboard for OCI resource ownership and mandatory tag compliance.

## Principles

- OCI Audit is not used as the source of truth.
- Creator and owner attribution are tag-based only.
- The initial runtime target is an OCI VM using instance principal authentication.
- The design should remain portable to OCI Functions or a containerized scheduled job.
- Outputs include CSV and static HTML.

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

## Usage

```bash
oci-resource-dashboard scan \
  --auth instance_principal \
  --region us-ashburn-1 \
  --compartment-id ocid1.compartment.oc1..example \
  --include-subcompartments \
  --mandatory-tags config/mandatory_tags.example.yaml \
  --output-dir out
```

Use sample mode for demos or local validation without OCI access:

```bash
oci-resource-dashboard scan \
  --sample \
  --auth instance_principal \
  --region us-ashburn-1 \
  --compartment-id ocid1.compartment.oc1..example \
  --include-subcompartments \
  --mandatory-tags config/mandatory_tags.example.yaml \
  --output-dir out
```

Without `--sample`, the tool authenticates with the OCI SDK, discovers compartments, queries OCI Resource Search, and generates the same CSV and HTML outputs.

## Instance Principal IAM

For an OCI VM, create a dynamic group matching the instance and grant read-only discovery permissions, for example:

```text
Allow dynamic-group <dashboard-dynamic-group> to inspect compartments in tenancy
Allow dynamic-group <dashboard-dynamic-group> to inspect all-resources in tenancy
Allow dynamic-group <dashboard-dynamic-group> to read tag-namespaces in tenancy
```

Scope these policies to selected compartments where possible.

## Development

```bash
make test
```

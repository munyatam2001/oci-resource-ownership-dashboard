# OCI Resource Ownership Dashboard

A professional static HTML dashboard generator for OCI tenancy resource ownership and mandatory tag compliance.

This first project step establishes the repository structure, CLI, configuration format, data models, compliance logic, and report interfaces. It intentionally does not call OCI APIs yet.

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

For now, `scan` loads the mandatory tag configuration, creates the output directory, and prints the intended scan settings. OCI discovery will be implemented behind the stub interfaces in a later step.

## Development

```bash
make test
```

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

### Sample Mode

Use sample mode for demos or local validation without OCI access:

```bash
oci-resource-dashboard scan \
  --sample \
  --auth instance_principal \
  --region us-ashburn-1 \
  --compartment-id ocid1.compartment.oc1..example \
  --mandatory-tags config/mandatory_tags.example.yaml \
  --output-dir out
```

### Live Root Compartment Scan

Scan only the provided root compartment:

```bash
oci-resource-dashboard scan \
  --auth instance_principal \
  --region us-ashburn-1 \
  --compartment-id ocid1.compartment.oc1..example \
  --mandatory-tags config/mandatory_tags.example.yaml \
  --output-dir out-real
```

### Live Subcompartment Scan

Scan the provided compartment and accessible child compartments:

```bash
oci-resource-dashboard scan \
  --auth instance_principal \
  --region ap-mumbai-1 \
  --compartment-id ocid1.compartment.oc1..example \
  --include-subcompartments \
  --mandatory-tags config/mandatory_tags.example.yaml \
  --output-dir out-real
```

### Limited Test Scan

Limit processing after discovery while validating output shape:

```bash
oci-resource-dashboard scan \
  --auth instance_principal \
  --region ap-mumbai-1 \
  --compartment-id ocid1.compartment.oc1..example \
  --include-subcompartments \
  --max-resources 100 \
  --mandatory-tags config/mandatory_tags.example.yaml \
  --output-dir out-limited
```

### Custom Resource Search Query

Override the default Resource Search query. Use `{compartment_id}` when the query should remain scoped to each selected compartment:

```bash
oci-resource-dashboard scan \
  --auth instance_principal \
  --region ap-mumbai-1 \
  --compartment-id ocid1.compartment.oc1..example \
  --resource-query "query instance resources where compartmentId = '{compartment_id}'" \
  --mandatory-tags config/mandatory_tags.example.yaml \
  --output-dir out-instances
```

You can also provide a broad query when you intentionally do not want the tool to inject compartment scope:

```bash
oci-resource-dashboard scan \
  --auth instance_principal \
  --region ap-mumbai-1 \
  --compartment-id ocid1.compartment.oc1..example \
  --resource-query "query bucket resources" \
  --mandatory-tags config/mandatory_tags.example.yaml \
  --output-dir out-buckets
```

Without `--sample`, the tool authenticates with the OCI SDK, discovers compartments, queries OCI Resource Search, and generates the same CSV and HTML outputs.

### Upload Reports To Object Storage

Generate reports locally and upload all generated CSV and HTML files:

```bash
oci-resource-dashboard scan \
  --auth instance_principal \
  --region ap-mumbai-1 \
  --compartment-id ocid1.compartment.oc1..example \
  --include-subcompartments \
  --mandatory-tags config/mandatory_tags.example.yaml \
  --output-dir out-real \
  --upload \
  --namespace <object-storage-namespace> \
  --bucket-name <bucket-name> \
  --object-prefix resource-ownership/latest
```

Upload only the static dashboard HTML:

```bash
oci-resource-dashboard scan \
  --sample \
  --auth instance_principal \
  --region us-ashburn-1 \
  --compartment-id ocid1.compartment.oc1..example \
  --mandatory-tags config/mandatory_tags.example.yaml \
  --output-dir out \
  --upload \
  --namespace <object-storage-namespace> \
  --bucket-name <bucket-name> \
  --upload-html-only
```

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

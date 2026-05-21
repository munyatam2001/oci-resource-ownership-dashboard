# Operations

## Initial VM Runtime

1. Install Python 3.10 or newer.
2. Configure an OCI dynamic group matching the VM.
3. Grant read-only IAM policies for the resources to scan.
4. Install the package and run the CLI with `--auth instance_principal`.

## Example

```bash
oci-resource-dashboard scan \
  --auth instance_principal \
  --region us-ashburn-1 \
  --compartment-id ocid1.tenancy.oc1..example \
  --include-subcompartments \
  --mandatory-tags config/mandatory_tags.example.yaml \
  --output-dir out
```

The current command prepares scan settings only. OCI API discovery, CSV generation, HTML rendering, and Object Storage publishing will be implemented in later phases.

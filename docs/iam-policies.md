# IAM Policies

Live discovery uses the OCI SDK with either config-file auth or VM instance principal auth. The tool reads compartment metadata and Resource Search results only. It does not use OCI Audit.

Example policy shape for an instance principal dynamic group:

```text
Allow dynamic-group <dashboard-dynamic-group> to inspect compartments in tenancy
Allow dynamic-group <dashboard-dynamic-group> to inspect all-resources in tenancy
Allow dynamic-group <dashboard-dynamic-group> to read tag-namespaces in tenancy
```

Scope these policies to the minimum required compartments where possible.

For a narrower compartment scope:

```text
Allow dynamic-group <dashboard-dynamic-group> to inspect compartments in compartment <compartment-name>
Allow dynamic-group <dashboard-dynamic-group> to inspect all-resources in compartment <compartment-name>
Allow dynamic-group <dashboard-dynamic-group> to read tag-namespaces in tenancy
```

If scanning child compartments, grant access at the parent level or repeat policies for each required compartment.

# IAM Policies

The initial scaffold does not call OCI APIs. Future OCI discovery will require read-only access to compartments, resource search, and tag metadata.

Example policy shape for an instance principal dynamic group:

```text
Allow dynamic-group <dashboard-dynamic-group> to inspect compartments in tenancy
Allow dynamic-group <dashboard-dynamic-group> to inspect all-resources in tenancy
Allow dynamic-group <dashboard-dynamic-group> to read tag-namespaces in tenancy
```

Scope these policies to the minimum required compartments where possible.

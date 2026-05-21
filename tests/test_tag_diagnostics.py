from oci_resource_dashboard.tag_diagnostics import collect_tag_usage, find_mapping_hints


def test_tag_usage_aggregation_counts_keys_and_nonempty_values():
    resources = [
        {
            "freeform_tags": {"Owner": "platform-team", "empty": ""},
            "defined_tags": {"Operations": {"CreatedBy": "alice@example.com"}},
        },
        {
            "freeform_tags": {"Owner": "security-team", "empty": "   "},
            "defined_tags": {"Operations": {"CreatedBy": None}},
        },
    ]

    usage = collect_tag_usage(resources)
    by_key = {(row.tag_type, row.tag_key): row for row in usage}

    assert by_key[("freeform", "Owner")].resources_with_key == 2
    assert by_key[("freeform", "Owner")].resources_with_nonempty_value == 2
    assert by_key[("freeform", "empty")].resources_with_key == 2
    assert by_key[("freeform", "empty")].resources_with_nonempty_value == 0
    assert by_key[("defined", "Operations.CreatedBy")].resources_with_key == 2
    assert by_key[("defined", "Operations.CreatedBy")].resources_with_nonempty_value == 1


def test_example_values_are_capped_at_five():
    resources = [
        {"freeform_tags": {"project": f"project-{index}"}, "defined_tags": {}}
        for index in range(8)
    ]

    usage = collect_tag_usage(resources)

    assert usage[0].example_values == [
        "project-0",
        "project-1",
        "project-2",
        "project-3",
        "project-4",
    ]


def test_mapping_hints_detect_likely_keys_case_insensitively():
    resources = [
        {
            "freeform_tags": {
                "REQUESTED_BY": "alice@example.com",
                "ApplicationOwner": "platform-team",
                "COSTCODE": "CC-1001",
                "Lifecycle": "prod",
                "AppName": "billing",
            },
            "defined_tags": {"Operations": {"Creator": "bob@example.com"}},
        }
    ]

    hints = find_mapping_hints(collect_tag_usage(resources))
    pairs = {(row["mandatory_tag"], row["candidate_existing_key"]) for row in hints}

    assert ("CreatedBy", "REQUESTED_BY") in pairs
    assert ("CreatedBy", "Operations.Creator") in pairs
    assert ("Owner", "ApplicationOwner") in pairs
    assert ("CostCenter", "COSTCODE") in pairs
    assert ("Environment", "Lifecycle") in pairs
    assert ("Application", "AppName") in pairs

package devops.sandbox_plan_test

import data.devops.sandbox_plan.allow

base := {
    "environment": "sandbox",
    "plan_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "approval": {"valid": true, "plan_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"},
    "plan": {"resource_changes": [{
        "address": "aws_subnet.private",
        "type": "aws_subnet",
        "change": {"actions": ["create"], "after": {
            "map_public_ip_on_launch": false,
            "tags": {"owner": "team", "cost_center": "cc1", "environment": "sandbox"}
        }}
    }]},
}

test_approved_private_plan if {
    allow with input as base
}

test_wrong_digest_denied if {
    not allow with input as object.union(base, {"plan_sha256": "changed"})
}

test_missing_plan_denied if {
    not allow with input as object.remove(base, ["plan"])
}

test_missing_tags_field_denied if {
    plan := {"resource_changes": [{"address": "aws_vpc.bad", "type": "aws_vpc", "change": {"actions": ["create"], "after": {}}}]}
    not allow with input as object.union(base, {"plan": plan})
}

test_prod_denied if {
    not allow with input as object.union(base, {"environment": "prod"})
}

test_unapproved_type_denied if {
    plan := {"resource_changes": [{"address": "aws_iam_user.bad", "type": "aws_iam_user", "change": {"actions": ["create"], "after": {"tags": {"owner": "team", "cost_center": "cc1", "environment": "sandbox"}}}}]}
    not allow with input as object.union(base, {"plan": plan})
}

test_delete_denied if {
    plan := {"resource_changes": [{"address": "aws_subnet.private", "type": "aws_subnet", "change": {"actions": ["delete"], "after": {"map_public_ip_on_launch": false, "tags": {"owner": "team", "cost_center": "cc1", "environment": "sandbox"}}}}]}
    not allow with input as object.union(base, {"plan": plan})
}

test_public_subnet_denied if {
    plan := {"resource_changes": [{"address": "aws_subnet.public", "type": "aws_subnet", "change": {"actions": ["create"], "after": {"map_public_ip_on_launch": true, "tags": {"owner": "team", "cost_center": "cc1", "environment": "sandbox"}}}}]}
    not allow with input as object.union(base, {"plan": plan})
}

test_missing_tags_denied if {
    plan := {"resource_changes": [{"address": "aws_vpc.bad", "type": "aws_vpc", "change": {"actions": ["create"], "after": {"tags": {"environment": "sandbox"}}}}]}
    not allow with input as object.union(base, {"plan": plan})
}

test_public_acr_denied if {
    plan := {"resource_changes": [{"address": "azurerm_container_registry.bad", "type": "azurerm_container_registry", "change": {"actions": ["create"], "after": {"public_network_access_enabled": true, "tags": {"owner": "team", "cost_center": "cc1", "environment": "sandbox"}}}}]}
    not allow with input as object.union(base, {"plan": plan})
}

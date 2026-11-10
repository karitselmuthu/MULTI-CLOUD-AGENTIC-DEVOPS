# Rego v1: https://www.openpolicyagent.org/docs/policy-language
# Terraform JSON plan shape: https://developer.hashicorp.com/terraform/internals/json-format#plan-representation
package devops.sandbox_plan

default allow := false

approved_types := {
    "aws_vpc", "aws_subnet", "aws_ecr_repository",
    "azurerm_resource_group", "azurerm_virtual_network",
    "azurerm_subnet", "azurerm_container_registry",
}

deny contains "environment must be sandbox" if {
    input.environment != "sandbox"
}

deny contains "plan digest must match approval" if {
    input.approval.plan_sha256 != input.plan_sha256
}

deny contains "plan digest missing" if {
    not input.plan_sha256
}

deny contains "approval missing" if {
    not input.approval.valid
}

deny contains "empty plan" if {
    count(input.plan.resource_changes) == 0
}

deny contains sprintf("unsupported action: %s", [change.address]) if {
    some change in input.plan.resource_changes
    some action in change.change.actions
    not action in {"create", "update", "no-op"}
}

deny contains sprintf("resource type is not approved: %s", [change.type]) if {
    some change in input.plan.resource_changes
    not change.type in approved_types
}

deny contains sprintf("destructive action blocked: %s", [change.address]) if {
    some change in input.plan.resource_changes
    some action in change.change.actions
    action == "delete"
}

deny contains sprintf("public address blocked: %s", [change.address]) if {
    some change in input.plan.resource_changes
    change.type == "aws_subnet"
    change.change.after.map_public_ip_on_launch == true
}

deny contains sprintf("public registry blocked: %s", [change.address]) if {
    some change in input.plan.resource_changes
    change.type == "azurerm_container_registry"
    change.change.after.public_network_access_enabled != false
}

deny contains sprintf("required tags missing: %s", [change.address]) if {
    some change in input.plan.resource_changes
    change.type != "azurerm_subnet"
    not valid_tags(object.get(change.change.after, "tags", {}))
}

valid_tags(tags) if {
    is_string(tags.owner)
    tags.owner != ""
    is_string(tags.cost_center)
    tags.cost_center != ""
    tags.environment == "sandbox"
}

allow if {
    input.environment == "sandbox"
    input.approval.valid == true
    is_string(input.plan_sha256)
    regex.match("^[a-f0-9]{64}$", input.plan_sha256)
    input.approval.plan_sha256 == input.plan_sha256
    count(input.plan.resource_changes) > 0
    count(deny) == 0
}

package devops.tools_test

import data.devops.tools.allow

test_planning_catalog_allowed if {
    allow with input as {"agent": {"role": "planning", "workflow_id": "w1"}, "workflow_id": "w1", "tool": "catalog.read"}
}

test_planning_execution_denied if {
    not allow with input as {"agent": {"role": "planning", "workflow_id": "w1"}, "workflow_id": "w1", "tool": "mock.execute", "approval_valid": true}
}

test_devops_unapproved_denied if {
    not allow with input as {"agent": {"role": "devops", "workflow_id": "w1"}, "workflow_id": "w1", "tool": "mock.execute", "environment": "sandbox", "approval_valid": false}
}

test_prod_execution_denied if {
    not allow with input as {"agent": {"role": "devops", "workflow_id": "w1"}, "workflow_id": "w1", "tool": "mock.execute", "environment": "prod", "approval_valid": true}
}

test_devops_approved_mock_allowed if {
    allow with input as {"agent": {"role": "devops", "workflow_id": "w1"}, "workflow_id": "w1", "tool": "mock.execute", "environment": "sandbox", "approval_valid": true}
}

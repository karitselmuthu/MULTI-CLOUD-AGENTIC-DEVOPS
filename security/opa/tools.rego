package devops.tools

default allow := false

allow if {
    input.agent.role == "planning"
    input.agent.workflow_id == input.workflow_id
    input.tool == "catalog.read"
}

allow if {
    input.agent.role == "devops"
    input.agent.workflow_id == input.workflow_id
    input.tool == "mock.execute"
    input.environment != "prod"
    input.approval_valid == true
}

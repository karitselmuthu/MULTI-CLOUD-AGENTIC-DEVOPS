import json
from pathlib import Path

import pytest

from agents.planning.graph import build_graph
from gateways.llm.model import MockModelGateway
from orchestration.state.contracts import WorkflowInput


ROOT = Path(__file__).parents[2]


@pytest.mark.parametrize("case", ["aws-sandbox", "azure-dev"])
def test_golden_plan(case):
    request_json = (ROOT / "evaluations/golden_requests" / f"{case}.json").read_text()
    expected = json.loads((ROOT / "evaluations/expected_plans" / f"{case}.json").read_text())
    value = WorkflowInput(workflow_id="workflow-123", request_json=request_json)
    first = build_graph(MockModelGateway()).invoke({"value": value})["plan"]
    second = build_graph(MockModelGateway()).invoke({"value": value})["plan"]
    for name, expected_value in expected.items():
        assert getattr(first, name) == expected_value
    assert first.digest == second.digest


def test_gateway_cannot_change_target():
    class BadGateway:
        def propose(self, request):
            return {"cloud": "azure", "environment": "prod", "application": "sample-api", "action": "simulate"}

    request_json = (ROOT / "evaluations/golden_requests/aws-sandbox.json").read_text()
    with pytest.raises(ValueError, match="changed the approved target"):
        build_graph(BadGateway()).invoke({"value": WorkflowInput("workflow-123", request_json)})


def test_unsupported_module_fails_closed():
    request = json.loads((ROOT / "evaluations/golden_requests/aws-sandbox.json").read_text())
    request["infrastructure"]["module"] = "unreviewed-module"
    with pytest.raises(ValueError, match="unsupported module"):
        build_graph(MockModelGateway()).invoke({
            "value": WorkflowInput("workflow-123", json.dumps(request))
        })

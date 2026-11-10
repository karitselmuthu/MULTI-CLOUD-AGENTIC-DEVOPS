# Week 2: Temporal orchestration, mock execution

Status: implementation slice 1.

## Scope

- Start each accepted request as a Temporal workflow using its persisted workflow ID.
- Recover dispatch after a worker crash between Temporal start and database acknowledgement.
- Prepare a deterministic mock plan, wait for a matching plan digest, then execute a mock action.
- Bound activity attempts and duration; expire an unapproved workflow after 24 hours.
- Support Temporal cancellation and worker replay after restart.
- Keep cloud and repository mutation absent.

## Boundaries

The approval signal is a workflow primitive for tests, not an exposed user approval API. There is no authenticated approver, change record binding, OPA decision or policy-gated executor yet. The API's database status becomes `queued` after dispatch; live Temporal status is not yet projected back into PostgreSQL. Do not use this workflow for real infrastructure or application changes.

## Acceptance checks

- Wrong plan digest cannot release execution; matching digest can.
- Workflow completes after a worker restart while waiting for approval.
- Timeout exits without execution; cancellation closes the workflow.
- Transient activity failure retries within the configured attempt limit.
- Re-dispatch after Temporal accepted a start acknowledges the existing workflow ID.

## Remaining Week 2 work

- Project Temporal state and audit transitions into the API and PostgreSQL.
- Add a governed approval endpoint after Week 4 identity and policy controls.
- Verify the full local PostgreSQL and Temporal stack in a runnable deployment.

# Local workflow recovery runbook

1. Check PostgreSQL health with the API `/health` route and inspect the workflow row and audit events.
2. Check the Temporal worker and task queue. Restart the worker; the dispatcher retries `received` requests using the workflow ID as an idempotent Temporal identifier.
3. Query `/workflows/{id}`. For `awaiting_approval`, verify the plan digest and issue a fresh scoped approval through the external approver process. Do not reuse an expired approval.
4. For a failed mock delivery, inspect the report and OPA decision before retrying. Never apply Terraform based only on the mock plan digest.
5. The file-backed `MockRecoveryStore` test checks a snapshot checksum and tenant before restore. This is not a PostgreSQL or Temporal disaster-recovery procedure.

This runbook is a local fixture. A production runbook still needs on-call ownership, backup location, recovery objectives, and a tested database plus Temporal restore exercise.

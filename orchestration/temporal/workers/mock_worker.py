"""Standalone mock worker for local Temporal development.

Source: https://docs.temporal.io/develop/python/workers
"""

import asyncio
import os

from temporalio.client import Client
from temporalio.worker import Worker

from orchestration.temporal.activities.mock import execute_mock_plan, prepare_mock_plan, verify_mock_approval
from orchestration.temporal.workflows.request import RequestWorkflow
from apps.api.database import make_session_factory
from orchestration.temporal.dispatch import TASK_QUEUE, dispatch_once



async def main() -> None:
    client = await Client.connect(os.getenv("TEMPORAL_ADDRESS", "localhost:7233"))
    sessions = make_session_factory()
    worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[RequestWorkflow],
        activities=[prepare_mock_plan, verify_mock_approval, execute_mock_plan],
    )
    async with worker:
        while True:
            await dispatch_once(client, sessions)
            await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())

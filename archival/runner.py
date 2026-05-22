from datetime import datetime
from pathlib import Path
from sqlite3 import Connection

from archival.db import save_run
from archival.jobs.base import Job, JobResult


def run_job(job: Job, conn: Connection) -> JobResult:
    started_at = datetime.now()

    result = job.run()

    result.started_at = started_at
    result.finished_at = datetime.now()

    save_run(conn, job.name, result)

    return result

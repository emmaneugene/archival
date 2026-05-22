# Archival

A CLI tool for managing archival jobs and workflows.

## Installation

```bash
pip install -e .
```

## Usage

```bash
# List available jobs
archival list

# Run a job
archival run telegram
archival run youtube
archival run articles

# View run history
archival history
archival history telegram
```

## Adding New Jobs

Create a new file in `archival/jobs/` implementing the `Job` interface:

```python
from archival.jobs.base import Job, JobResult, JobStatus

class MyJob(Job):
    name = "myjob"
    description = "Description of what this job does"

    def run(self) -> JobResult:
        # Your archival logic here
        return JobResult(
            status=JobStatus.SUCCESS,
            message="Job completed",
        )
```

Then register it in `archival/jobs/__init__.py`.

## Configuration

Place config files in the `config/` directory:
- `config/telegram-keys.json` - Telegram API credentials

## Data

Archived data is stored in the `data/` directory, organized by job type.

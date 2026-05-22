from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any


class JobStatus(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"


@dataclass
class JobResult:
    status: JobStatus
    message: str
    metadata: dict[str, Any] | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


class Job(ABC):
    name: str
    description: str

    def __init__(self, data_dir: Path, config_dir: Path):
        self.data_dir = data_dir
        self.config_dir = config_dir

    @abstractmethod
    def run(self) -> JobResult:
        """Execute the archival job."""
        pass

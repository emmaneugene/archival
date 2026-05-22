from archival.jobs.base import Job, JobResult
from archival.jobs.telegram_chats import TelegramJob
from archival.jobs.video_transcripts import YoutubeJob
from archival.jobs.pages import ArticlesJob

JOBS: dict[str, type[Job]] = {
    "telegram": TelegramJob,
    "youtube": YoutubeJob,
    "articles": ArticlesJob,
}

__all__ = ["Job", "JobResult", "JOBS"]

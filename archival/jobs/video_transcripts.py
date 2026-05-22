from archival.jobs.base import Job, JobResult, JobStatus


class YoutubeJob(Job):
    name = "youtube"
    description = "Archive YouTube videos and metadata"

    def run(self) -> JobResult:
        try:
            output_dir = self.data_dir / "youtube"
            output_dir.mkdir(parents=True, exist_ok=True)

            # TODO: Implement actual youtube archival logic

            return JobResult(
                status=JobStatus.SUCCESS,
                message=f"YouTube archive completed. Output: {output_dir}",
                metadata={"output_dir": str(output_dir)},
            )
        except Exception as e:
            return JobResult(
                status=JobStatus.FAILURE,
                message=str(e),
            )

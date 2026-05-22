from archival.jobs.base import Job, JobResult, JobStatus


class ArticlesJob(Job):
    name = "articles"
    description = "Archive web articles using monolith"

    def run(self) -> JobResult:
        try:
            output_dir = self.data_dir / "articles"
            output_dir.mkdir(parents=True, exist_ok=True)

            # TODO: Implement actual article archival logic using monolith

            return JobResult(
                status=JobStatus.SUCCESS,
                message=f"Articles archive completed. Output: {output_dir}",
                metadata={"output_dir": str(output_dir)},
            )
        except Exception as e:
            return JobResult(
                status=JobStatus.FAILURE,
                message=str(e),
            )

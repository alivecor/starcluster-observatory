"""The job class represents a job on the cluster."""
import resources


class Job:
    def __init__(self, job_id, queue, assigned_queue):
        """Constructor

        Args:
            job_id (int) - The job ID.
            queue (str) - The name of the queue this job is submitted on.
            assigned_queue (str) - The name of the queue this job is running on, or None.
        """
        self.job_id = job_id
        self.queue = queue
        self.assigned_queue = assigned_queue

    def running(self):
        """Is this job running or not."""
        return self.assigned_queue is not None

    def resources_required(self):
        """List of resources required by this job."""
        return [self.queue]

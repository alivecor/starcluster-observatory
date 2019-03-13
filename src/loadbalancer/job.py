"""The job class represents a job on the cluster."""

from datetime import datetime

class Job:
    def __init__(self, job_id, requested_queue, assigned_queue, owner, state, predecessors, submit_timestamp):
        """Constructor

        Args:
            job_id (int) - The job ID.
            requested_queue (str) - The name of the queue this job is submitted on.
            assigned_queue (str) - The name of the queue this job is running on, or None.
            owner (str) - The owner of the job.
            state (str) - The state of the running job.
            predecessors ([int]) - List of job ids this job depends on.
            submit_timestamp (int) - The unix timestamp at which this job was submitted.

        """
        self.job_id = job_id
        self.requested_queue = requested_queue
        self.assigned_queue = assigned_queue
        self.owner = owner
        self.state = state
        self.predecessors = predecessors
        self.submit_timestamp = submit_timestamp

    def running(self):
        """Is this job running or not."""
        return self.assigned_queue is not None

    def __str__(self):
        submit_date = datetime.utcfromtimestamp(self.submit_timestamp).strftime('%Y-%m-%d %H:%M:%S')
        return 'Job %d: %s on %s submitted by %s at %d' % (
            self.job_id, self.state, self.requested_queue, self.owner, submit_date)

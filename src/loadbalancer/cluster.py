"""Cluster defines the cluster state as a list/collection of nodes."""

from job import Job
from node import JobQueue
from node import Node


class Cluster:
    def __init__(self, name, nodes):
        """Constructor."""
        self.name = name
        self.nodes = nodes
        self.jobs = []

    @classmethod
    def parseFromJSON(cls, json):
        """Create cluster object from qhost output"""
        cluster_name = ''
        nodes = []
        for host_json in json:
            name = host_json['name']
            load = float(host_json['load_avg'])
            queues = host_json['queues']
            job_queues = {}
            for qname, queue_json in queues.items():
                slots = int(queue_json['slots'])
                slots_used = int(queue_json['slots_used'])
                job_queues[qname] = JobQueue(qname, slots, slots_used)
            node = Node(name, job_queues, int(load*100))
            if node.cluster_name():
                cluster_name = node.cluster_name()
            nodes.append(node)
        return Cluster(cluster_name, nodes)

    def populateJobsFromJSON(self, json):
        jobs = []
        for job_json in json:
            job_id = int(job_json['job_id'])
            requested_queue = job_json['qr_name']
            assigned_queue = job_json.get('queue_name', None)
            owner = job_json['owner']
            state = job_json['state']
            predecessors = job_json['predecessors']
            submit_timestamp = int(job_json['submission_timestamp'])
            job = Job(job_id, requested_queue, assigned_queue, owner, state, predecessors, submit_timestamp)
            jobs.append(job)
        self.jobs = jobs

    def nodes_for_queue(self, queue):
        return [n for n in self.nodes if n.total_slots(queue) > 0 and not n.is_master()]

    def jobs_on_queue(self, queue=None):
        """Get all jobs on specified queue."""
        if queue is None:
            return self.jobs
        else:
            return [j for j in self.jobs if j.requested_queue == queue]

    def pending_jobs(self, queue=None):
        """Get pending jobs on specified queue"""
        return [j for j in self.jobs_on_queue(queue) if not j.running()]

    def runnable_jobs(self, queue=None):
        """Get all pending jobs which are ready to be scheduled"""
        return [j for j in self.pending_jobs(queue) if not j.has_predecessors()]

    def available_slots(self, queue=None):
        """Get total number of available slots on specified queue."""
        return sum(n.available_slots(queue) for n in self.nodes)

    def __str__(self):
        lines = [
            'Cluster %s' % self.name,
            'Nodes:'
        ]
        lines.extend([str(node) for node in self.nodes])
        lines.append('Jobs:')
        lines.extend([str(job) for job in self.jobs])
        return '\n'.join(lines)


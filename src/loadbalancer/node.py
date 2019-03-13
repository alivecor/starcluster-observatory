"""The node class represents an aws instance in the cluster."""


class JobQueue:
    def __init__(self, name, slots, slots_used):
        self.name = name
        self.slots = slots
        self.slots_used = slots_used

    def __str__(self):
        return '%s:  %d slots, %d slots used' % (self.name, self.slots, self.slots_used)


class Node:
    def __init__(self, name, job_queues, cpu_load_pct=None, age=0):
        """Constructor

        Args:
            name (str) The name (alias) of the node.
            job_queues ({str: JobQueue}) State of queues on this node.
            cpu_load_pct (int) The current CPU load percentage.
            age (int) Age of this node in seconds.
        """
        self.name = name
        self.job_queues = job_queues
        self.cpu_load_pct = cpu_load_pct
        self.age = age

    def cluster_name(self):
        """Name of the cluster this node belongs to."""
        if '-' in self.name:
            return self.name.split('-')[0]  # By convention, node aliases are formatted as clustername-node001
        else:
            return ''

    def is_master(self):
        """Return true if this is the master node."""
        if '-' in self.name:
            return self.name.split('-')[1] == 'master'  # By convention, master node is named clustername-master
        else:
            return 'master' in self.name

    def node_index(self):
        if 'node' in self.name:
            return int(self.name.split('node')[1])
        else:
            return None

    def cpu_load_percent(self):
        """The CPU utilization % of the node."""
        return self.cpu_load_pct

    def available_slots(self, queue=None):
        """Return the number of available slots on specified queue.  If queue not specified, returns all slots."""
        queue_names = self.job_queues.keys() if queue is None else [queue]
        queues = [self.job_queues[qname] for qname in queue_names if qname in self.job_queues]
        return sum(q.slots - q.slots_used for q in queues)

    def available_queues(self):
        """Return set of queues that have open slots."""
        return frozenset([j.name for j in self.job_queues.values() if j.slots > 0])

    def total_slots(self, queue=None):
        """Return the number of available slots on specified queue.  If queue not specified, returns all slots."""
        queue_names = self.job_queues.keys() if queue is None else [queue]
        queues = [self.job_queues[qname] for qname in queue_names if qname in self.job_queues]
        return sum(q.slots for q in queues)

    def total_jobs(self):
        """Returns total number of jobs this node is running on all queues."""
        return sum([jq.slots_used for jq in self.job_queues.values()])

    def __str__(self):
        lines = [
            '%s:  age: %d  load: %d%%' % (self.name, self.age, self.cpu_load_percent()),
            'Queues:'
        ]
        lines.extend([str(q) for q in self.job_queues.values()])
        return '\n'.join(lines)

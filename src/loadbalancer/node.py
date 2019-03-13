"""The node class represents an aws instance in the cluster."""


class JobQueue:
    def __init__(self, name, slots, slots_used):
        self.name = name
        self.slots = slots
        self.slots_used = slots_used

    def __str__(self):
        return '%s:  %d slots, %d slots used' % (self.name, self.slots, self.slots_used)


class Node:
    def __init__(self, name, job_queues, cpu_load_pct=None):
        """Constructor

        Args:
            name (str) The name (alias) of the node.
            job_queues ({str: JobQueue}) State of queues on this node.
            cpu_load_pct (int) The current CPU load percentage.
        """
        self.name = name
        self.job_queues = job_queues
        self.cpu_load_pct = cpu_load_pct

    def cluster_name(self):
        """Name of the cluster this node belongs to."""
        if '-' in self.name:
            return self.name.split('-')[0]  # By convention, node aliases are formatted as clustername-node001
        else:
            return ''

    def cpu_load_pct(self):
        """The CPU utilization % of the node."""
        return self.cpu_load_pct()

    def __str__(self):
        lines = [
            self.name,
            'Queues:'
        ]
        lines.extend([str(q) for q in self.job_queues.values()])
        return '\n'.join(lines)

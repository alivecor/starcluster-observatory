"""Cluster defines the cluster state as a list/collection of nodes."""

from node import JobQueue
from node import Node


class Cluster:
    def __init__(self, name, nodes):
        """Constructor."""
        self.name = name
        self.nodes = nodes

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

    def __str__(self):
        lines = [
            'Cluster %s' % self.name,
            'Nodes:'
        ]
        lines.extend([str(node) for node in self.nodes])
        return '\n'.join(lines)


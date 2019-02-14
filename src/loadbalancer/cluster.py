"""Cluster defines the cluster state as a list/collection of nodes."""

from node import Node

class Cluster:
    def __init__(self, node_list=None, hosts_json=None):
        """Constructor.  Provide node_list or hosts_json to initialize."""
        if node_list is not None:
            self.node_list = node_list
        else:
            # process the JSON
            self.node_list = []

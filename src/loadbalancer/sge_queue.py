"""Queue defines the configuration of SGE queues on the cluster."""


class SGEQueue:
    def __init__(self, name, default_node_type, node_types, max_nodes=3):
        """Constructor.  Provide node_list or hosts_json to initialize."""
        self.name = name
        self.default_node_type = default_node_type
        self.node_types = node_types
        self.max_nodes = max_nodes

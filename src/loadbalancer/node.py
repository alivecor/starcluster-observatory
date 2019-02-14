"""The node class represents an aws instance in the cluster."""
import resources


_resources_by_node_type = {
    'p3.2xlarge': [resources.GPU],
    'p2.xlarge': [resources.GPU],
    'c5.18xlarge': [resources.MEM],
    'c5.4xlarge': [resources.CPU] * 4,
    'c5.9xlarge': [resources.CPU] * 9,
}

# The type of node to spawn to provide the requested resource
_node_type_for_resource = {
    resources.GPU: 'p3.2xlarge',
    resources.CPU: 'c5.4xlarge',
    resources.MEM: 'c5.18xlarge',
}


class Node:
    def __init__(self, node_type, alias=None):
        """Constructor

        Args:
            node_type (str) - The AWS instance type.
            alias (str, optional) - The alias of the node.
        """
        self.node_type = node_type
        self.alias = None
        self.launch_time = None

    def resources_provided(self):
        """Get list of the resources provided by this node."""
        return _resources_by_node_type[self.node_type]

    def jobs(self):
        """Get list of jobs running on this node."""
        return []

    def utilization(self):
        """The CPU utilization % of the node."""
        return 0

    def sessions(self):
        """The number of active login sessions to this node."""
        return 0

    def launch_time(self):
        """The time that the node was launched (in unix seconds), or None"""
        return None

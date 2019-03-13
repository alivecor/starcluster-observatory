import requests
import schedule
import time
from threading import Thread

from cluster import Cluster
import config

class LoadBalancer:
    """LoadBalancer polls sge on a background thread, and starts and terminates nodes to try to match load."""
    def __init__(self,
                 api_server_host,
                 api_server_port,
                 polling_interval=5 * 60):
        """Constructor.

        Args:
            api_server_host (string) - The IP address of the API server.
            api_server_port (int) - The port to connect to.
            polling_interval - Poll queue state every polling_interval seconds.
        """
        self.api_server_host = api_server_host
        self.api_server_port = api_server_port
        self.polling_interval = polling_interval
        schedule.every(self.polling_interval).seconds.do(self._poll)
        self.polling = False
        self.polling_thread = None
        # Maps host name to first timestamp (seconds) host was detected.
        self._host_launch_times = {}  # This is the only piece of information that persists between run loop evaluations.

    def start_polling(self):
        """Start polling queues and load balancing the cluster."""
        self.polling = True
        self.polling_thread = Thread(target=self._run_schedule)
        self.polling_thread.start()

    def stop(self):
        """Stop polling and load balancing."""
        self.polling = False
        self.polling_thread = None

    def _run_schedule(self):
        """Run loop for the background task scheduler thread."""
        while self.polling:
            schedule.run_pending()
            time.sleep(30)

    def _add_host(self, type):
        """Add new node of specified type to cluster."""
        add_node_results = requests.get('http://%s:%s/nodes/add?instance_type=%s' % (
            self.api_server_host, self.api_server_port, type))
        results_json = add_node_results.json()
        if results_json['status'] == 'error':
            print('Error adding new instance: %s', str(results_json), flush=True)

    def _remove_host(self, alias):
        """Removes host with specified alias."""
        add_node_results = requests.get('http://%s:%s/nodes/%s/remove' % (
            self.api_server_host, self.api_server_port, alias))
        results_json = add_node_results.json()
        if results_json['status'] == 'error':
            print('Error adding removing instance: %s', str(results_json), flush=True)

    def _qhost(self):
        """Calls qhost to get host list"""
        sge_hosts_results = requests.get('http://%s:%s/qhost' % (self.api_server_host, self.api_server_port))
        hosts_json = sge_hosts_results.json()
        if 'status' in hosts_json and hosts_json['status'] == 'error':
            print('Error calling qhost: %s', str(hosts_json), flush=True)
            return None
        return hosts_json

    def _qstat(self):
        """Calls qstat to get job list"""
        sge_jobs_results = requests.get('http://%s:%s/qstat' % (self.api_server_host, self.api_server_port))
        jobs_json = sge_jobs_results.json()
        if 'status' in jobs_json and jobs_json['status'] == 'error':
            print('Error calling qstat: %s', str(jobs_json))
            return None
        return jobs_json

    def _poll(self):
        """Internal method called periodically to poll the cluster state."""
        # Get list of hosts results from server.
        hosts_json = self._qhost()
        if hosts_json is None:
            return
        jobs_json = self._qstat()
        if jobs_json is None:
            return
        cluster = Cluster.parseFromJSON(hosts_json)
        cluster.populateJobsFromJSON(jobs_json)
        self.update_host_ages(cluster)
        print('Polled cluster:')
        print(str(cluster))
        for queue in config.queues:
            self.check_increase_capacity(cluster, queue)
        self.check_remove_idle(cluster)

    def update_host_ages(self, cluster):
        """Update inferred age of hosts"""
        host_names = [node.name for node in cluster.nodes]
        new_launch_times = {
            name: self._host_launch_times[name] if name in self._host_launch_times else time.time() for name in host_names
        }
        self._host_launch_times = new_launch_times
        for node in cluster.nodes:
            node.age = time.time() - new_launch_times[node.name]

    def check_increase_capacity(self, cluster, queue):
        """Check if we need to increase capacity for the specified queue."""
        # If we already have the maximum number of nodes allocated for this queue, return.
        if len(cluster.nodes_for_queue(queue.name)) >= queue.max_nodes:
            return
        pending_jobs = cluster.pending_jobs(queue.name)
        runnable_jobs = [j for j in pending_jobs if not j.has_predecessors()]
        if len(runnable_jobs) > 0 and cluster.available_slots(queue.name) == 0:
            print('LoadBalancer: Launching new %s in cluster %s' % (queue.default_node_type, last_node.cluster_name()), flush=True)
            self._add_host(queue.default_node_type)

    def check_remove_idle(self, cluster):
        """Check for idle nodes, remove them if needed."""
        # Ensure node is idle AND there are no more pending jobs on the node's queues.
        idle_nodes = [n for n in cluster.nodes if not n.is_master() and n.total_jobs() == 0 and n.age > (config.min_age_minutes * 60)]
        if len(idle_nodes) > 0:
            last_node = sorted(idle_nodes, key=lambda n: n.node_index())[-1]
            print('LoadBalancer: Removing idle node %s from cluster %s' % (last_node.name, last_node.cluster_name()), flush=True)
            self._remove_host(last_node.name)

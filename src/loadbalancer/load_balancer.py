import requests
import schedule
import time
from threading import Thread

from cluster import Cluster


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
        self._idle_hosts = {}  # Maps host name to first time (seconds) host was detected idle.

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
            time.sleep(1)

    def _add_host(self, type):
        """Add new node of specified type to cluster."""
        add_node_results = requests.get('http://%s:%s/nodes/add?instance_type=%s' % (
            self.api_server_host, self.api_server_port, type))
        results_json = add_node_results.json()
        if results_json['status'] == 'error':
            print('Error adding new instance: %s', str(results_json), flush=True)

    def _remove_host(self, alias):
        """Removes host with specified alias."""
        self.will_remove_host(alias)
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
        print('TODO: transform hosts and jobs into cluster datastructure')
        print('hosts_json:\n' + str(hosts_json))
        print('jobs_json:\n' + str(jobs_json))

    def check_increase_capacity(self, hosts, pending_jobs):
        """Check if we have pending jobs, increase capacity accordingly."""
        # Filter out jobs which don't have a queue.
        pending_jobs = [j for j in pending_jobs if 'qr_name' in j and j['qr_name'] != '']
        # Filter out held jobs which are dependent on other jobs.
        # TODO: check if predecessor requirements are met or not.
        pending_jobs = [j for j in pending_jobs if len(j['predecessors']) == 0]
        # Split cpu and gpu jobs.
        pending_cpu_jobs = [j for j in pending_jobs if j['qr_name'] != 'gpu.q']
        pending_gpu_jobs = [j for j in pending_jobs if j['qr_name'] == 'gpu.q']
        #print('Pending CPU jobs: %d' % len(pending_cpu_jobs))
        #print('Pending GPU jobs: %d' % len(pending_gpu_jobs))
        # Give priority to GPU jobs, since that is what is most likely used for training.
        if pending_gpu_jobs:
            print('LoadBalancer: Launching new GPU node with %d pending jobs on gpu.q' % len(pending_gpu_jobs), flush=True)
            self._add_host(self.gpu_type)
        elif pending_cpu_jobs:
            print('LoadBalancer: Launching new CPU node with %d pending cpu jobs' % len(pending_cpu_jobs), flush=True)
            self._add_host(self.gpu_type)

    def check_remove_idle(self, hosts, queued_jobs):
        """Check for idle nodes, remove them if confirmed idle for longer than our idle timeout."""
        time_now = time.time()
        idle_hosts = self._idle_hosts
        # print('Checking for idle hosts at time %.1f.' % time_now)
        # Check to see if any hosts are idle.
        host_names = set([h['name'] for h in hosts if not 'master' in ['name']])
        # Get hosts with running jobs.
        busy_hosts = set([j['queue_name'].split('@')[1] for j in queued_jobs])
        # Remove hosts from idle list which have taken on jobs.
        # print('busy_hosts :' + str(busy_hosts))
        for busy_host in busy_hosts:
            if busy_host in idle_hosts:
                del idle_hosts[busy_host]
        # Add hosts with no jobs to idle list
        idle_host_aliases = host_names.difference(busy_hosts)
        # print('idle_host_aliases :' + str(idle_host_aliases))
        for host in idle_host_aliases:
            if host not in idle_hosts:
                idle_hosts[host] = time_now
        # Remove hosts from idle list that have been removed from SGE.
        for host in idle_hosts:
            if host not in idle_host_aliases:
                del idle_hosts[host]
        # Check if any hosts have been idle longer than idle_timeout.
        hosts_to_remove = []
        idle_times = []
        for host, start_time in idle_hosts.items():
            if (time_now - start_time) > self.idle_timeout:
                hosts_to_remove.append(host)
                idle_times.append(time_now - start_time)
        if hosts_to_remove:
            # Remove the oldest idle node first.
            index = np.argmax(idle_times)
            alias = hosts_to_remove[index]
            idle_time = idle_times[index]
            # Remove one host
            print('LoadBalancer: Removing node %s which was idle for %.1f minutes' % (alias, idle_time), flush=True)
            self._remove_host(alias)

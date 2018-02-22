import numpy as np
import schedule
import sge
import starcluster
import subprocess
import time
from threading import Thread


class LoadBalancer:
    """LoadBalancer polls sge on a background thread, and starts and terminates nodes to try to match load."""
    def __init__(self,
                 cluster_name,
                 max_capacity,
                 cpu_type='c4.xlarge',
                 gpu_type='p2.xlarge',
                 idle_timeout=20 * 60,
                 polling_interval=5 * 60):
        """Constructor.

        Args:
            cluster_name (string) - The cluster name.
            max_capacity (int) - The maximum number of worker nodes allowed.
            cpu_type (string) - The default CPU instance type to add.
            gpu_type (string) - The default GPU instance type to add.
            idle_timeout - Terminate nodes if idle for more than idle_timeout seconds.
            polling_interval - Poll queue state every polling_interval seconds.
        """
        self.cluster_name = cluster_name
        self.max_capacity = max_capacity
        self.cpu_type = cpu_type
        self.gpu_type = gpu_type
        self.idle_timeout = idle_timeout
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

    def add_host(self, type):
        """Add new node of specified type to cluster."""
        try:
            starcluster.add_node(self.cluster_name, instance_type=type)
        except subprocess.CalledProcessError as e:
            print('Error adding new %s instance: %s' % (type, str(e)))

    def remove_host(self, alias):
        """Removes host with specified alias."""
        del self._idle_hosts[alias]
        try:
            starcluster.remove_node(self.cluster_name, alias)
        except subprocess.CalledProcessError as e:
            print('Error auto-removing idle host %s: %s' % (alias, str(e)))

    def _poll(self):
        """Internal method called periodically to poll the cluster state."""
        hosts = sge.qhost()
        queued_jobs, pending_jobs = sge.qstat()
        self.check_increase_capacity(hosts, pending_jobs)
        self.check_remove_idle(hosts, queued_jobs)

    def check_increase_capacity(self, hosts, pending_jobs):
        """Check if we have pending jobs, increase capacity accordingly."""
        pending_cpu_jobs = [j for j in pending_jobs if j['queue_name'] != 'gpu.q']
        pending_gpu_jobs = [j for j in pending_jobs if j['queue_name'] == 'gpu.q']
        # Give priority to GPU jobs, since that is what is most likely used for training.
        if pending_gpu_jobs:
            print('LoadBalancer: Launching new GPU node with %d pending jobs on gpu.q' % len(pending_gpu_jobs))
            self.add_host(self.gpu_type)
        elif pending_cpu_jobs:
            print('LoadBalancer: Launching new CPU node with %d pending cpu jobs' % len(pending_cpu_jobs))
            self.add_host(self.gpu_type)

    def check_remove_idle(self, hosts, queued_jobs):
        """Check for idle nodes, remove them if confirmed idle for longer than our idle timeout."""
        time_now = time.time()
        idle_hosts = self._idle_hosts
        # print('Checking for idle hosts at time %.1f.' % time_now)
        # Check to see if any hosts are idle.
        host_names = set([h['name'] for h in hosts if not 'master' in ['name']])
        # Get hosts with running jobs.
        busy_hosts = set([j['queue_name'].split('@')[1] for j in queued_jobs])
        # Remove hosts with jobs from idle list
        for busy_host in busy_hosts:
            if busy_host in idle_hosts:
                del idle_hosts[busy_host]
        # Add hosts with no jobs to idle list
        idle_host_aliases = host_names.difference(busy_hosts)
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
            print('LoadBalancer: Removing node %s which was idle for %.1f minutes' % (alias, idle_time))
            self.remove_host(alias)

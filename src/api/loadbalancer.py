import schedule
import sge
import time
from threading import Thread


class LoadBalancer:
    """LoadBalancer polls sge on a background thread, and starts terminates nodes to try to match load."""
    def __init__(self,
                 max_capacity,
                 cpu_type='c4.2xlarge',
                 gpu_type='p3.2xlarge',
                 idle_timeout=20 * 60,
                 polling_interval=60):
        """Constructor.

        Args:
            max_capacity (int) - The maximum number of worker nodes allowed.
            cpu_type (string) - The default CPU instance type to add.
            gpu_type (string) - The default GPU instance type to add.
            idle_timeout - Terminate nodes if idle for more than idle_timeout seconds.
            polling_interval - Poll queue state every polling_interval seconds.
        """
        self.max_capacity = max_capacity
        self.cpu_type = cpu_type
        self.gpu_type = gpu_type
        self.polling_interval = polling_interval
        schedule.every(self.polling_interval).seconds.do(self.check_idle)
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

    def check_idle(self):
        time_now = time.time()
        _idle_hosts = self._idle_hosts
        print('Checking for idle hosts at time %.1f.' % time_now)
        # First, check to see if any hosts are idle.
        hosts = sge.qhost()
        host_names = set([h['name'] for h in hosts if not 'master' in ['name']])
        queued_jobs, _ = sge.qstat()
        # Hosts with no jobs scheduled on them
        busy_hosts = set([j['queue_name'].split('@')[1] for j in queued_jobs])
        # Remove hosts with jobs from idle list
        for busy_host in busy_hosts:
            if busy_host in _idle_hosts:
                del _idle_hosts[busy_host]
        # Add hosts with no jobs to idle list
        idle_hosts = host_names.difference(busy_hosts)
        for host in idle_hosts:
            if host not in _idle_hosts:
                _idle_hosts[host] = time_now
        # Check if any hosts have been idle longer than idle_timeout
        hosts_to_remove = []
        for host, start_time in _idle_hosts.copy().items():
            if time_now - start_time > (args.idle_timeout * 60):
                hosts_to_remove.append(host)
                del _idle_hosts[host]
        for host in hosts_to_remove:
            try:
                starcluster.remove_node(args.cluster_name, host)
            except subprocess.CalledProcessError as e:
                print('Error auto-removing idle host %s: %s' % (host, str(e)))

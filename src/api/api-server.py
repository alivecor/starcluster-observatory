"""A simple server for directing starcluster from another ec2 instance in our subnet."""
import argparse
from flask import Flask
from flask import jsonify
from flask import request
import schedule
import subprocess
from threading import Thread
import time

import sge
import starcluster


parser = argparse.ArgumentParser(description='Run a server which exposes the starcluster and qstat APIs.', allow_abbrev=True)
parser.add_argument('--host_ip', default='0.0.0.0', type=str, help='IP address of interface to listen on.')
parser.add_argument('--port', default=6361, type=int, help='Port to listen on.')
parser.add_argument('--cluster_name', default='dev', type=str, help='Name of the cluster to manage.')
parser.add_argument('--starcluster_config', default='/etc/starcluster/config', type=str, help='Path to starcluster config file.')
parser.add_argument('--idle_timeout', default=30, type=int, help='Shut down nodes if idle longer than this (minutes).')

args = parser.parse_args()


app = Flask(__name__)


@app.route('/status')
def cluster_status():
    try:
        uptime, nodes = starcluster.get_status(args.cluster_name)
    except subprocess.CalledProcessError as e:
        return jsonify({'status': 'error', 'error': 'An error occurred while running starcluster listclusters'})
    return jsonify({
        'status': 'ok',
        'uptime': uptime,
        'nodes': nodes
    })


@app.route('/qhost')
def qhost():
    """Returns SGE execution hosts."""
    try:
        result = sge.qhost()
    except subprocess.CalledProcessError as e:
        return jsonify({
            'status': 'error',
            'error': 'An error occurred while running qhost'
        })
    return jsonify(result)


@app.route('/instances')
def instances():
    """List all AWS instances in the current cluster.  Should match up with results of /qhost, but not necessarily."""
    try:
        instances = starcluster.list_instances()
    except subprocess.CalledProcessError as e:
        return jsonify({
            'status': 'error',
            'error': 'An error occurred while running starcluster listinstances'
        })

    try:
        clusters = starcluster.list_clusters()
    except subprocess.CalledProcessError as e:
        return jsonify({
            'status': 'error',
            'error': 'An error occurred while running starcluster listclusters'
        })
    instances_by_alias = {i['alias'] : i for i in instances if 'alias' in i}
    # Find instance of our cluster.
    cluster = next((c for c in clusters if c['name'] == args.cluster_name), None)
    node_aliases = [node['alias'] for node in cluster['nodes']]
    cluster_instances = [instances_by_alias[a] for a in node_aliases]
    return jsonify(cluster_instances)


@app.route('/qstat')
def qstat():
    job_id = request.args.get('job_id')
    try:
        if job_id is None:
            queued, pending = sge.qstat()
            all_jobs = queued + pending
            result = [sge.qstat_job_details(int(job['job_id']), job['state'], job['queue_name']) for job in all_jobs]
        else:
            result = sge.qstat_job_details(int(job_id))
    except subprocess.CalledProcessError as e:
        return jsonify({
            'status': 'error',
            'error': 'An error occurred while running qstat'
        })
    return jsonify(result)


@app.route('/jobs/<jid>/cancel')
def cancel_job(jid):
    try:
        sge.qdel(int(jid))
    except subprocess.CalledProcessError as e:
        return jsonify({
        'status': 'error',
        'error': 'An error occurred while running qdel'
    })
    return jsonify({
        'status': 'ok',
    })


@app.route('/nodes/add')
def cluster_add_node():
    instance_type = request.args.get('instance_type')
    try:
         starcluster.add_node(args.cluster_name, instance_type=instance_type)
    except subprocess.CalledProcessError as e:
        return jsonify({
            'status': 'error',
            'error': 'An error occurred while running starcluster addnode'
        })
    return jsonify({
        'status': 'ok',
    })


@app.route('/nodes/<node_alias>/remove')
def cluster_remove_node(node_alias):
    try:
        starcluster.remove_node(args.cluster_name, node_alias)
    except subprocess.CalledProcessError as e:
        return jsonify({
        'status': 'error',
        'error': 'An error occurred while running starcluster removenode'
    })
    return jsonify({
        'status': 'ok',
    })


def run_schedule():
    """Run loop for the background task scheduler thread."""
    while 1:
        schedule.run_pending()
        time.sleep(1)


_idle_hosts = {}  # Maps host name to first time (seconds) host was detected idle.
def check_idle():
    time_now = time.time()
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


if __name__ == '__main__':
    schedule.every(60).seconds.do(check_idle)
    t = Thread(target=run_schedule)
    t.start()
    app.run(host=args.host_ip, port=args.port)

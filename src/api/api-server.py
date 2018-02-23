"""A simple server for directing starcluster from another ec2 instance in our subnet."""
import argparse
from flask import Flask
from flask import jsonify
from flask import request
import subprocess

import loadbalancer
import sge
import starcluster


parser = argparse.ArgumentParser(description='Run a server which exposes the starcluster and qstat APIs.')
parser.add_argument('--host_ip', default='0.0.0.0', type=str, help='IP address of interface to listen on.')
parser.add_argument('--port', default=6361, type=int, help='Port to listen on.')
parser.add_argument('--cluster_name', default='dev', type=str, help='Name of the cluster to manage.')
parser.add_argument('--starcluster_config', default='/etc/starcluster/config', type=str, help='Path to starcluster config file.')
parser.add_argument('--idle_timeout', default=120, type=int, help='Shut down nodes if idle longer than this (minutes).')
parser.add_argument('--polling_interval', default=5, type=int, help='Polling interval for load balancer (minutes).')
parser.add_argument('--max_capacity', default=16, type=int, help='Maximum number of nodes to allow.')

args = parser.parse_args()


app = Flask(__name__)

lb = loadbalancer.LoadBalancer(args.cluster_name,
                               args.max_capacity,
                               cpu_type='c4.xlarge',   # Unforunate hard-coded constants.
                               gpu_type='p3.2xlarge',  # TODO: parameterize these in config.
                               idle_timeout=args.idle_timeout * 60,
                               polling_interval=args.polling_interval * 60)


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


@app.route('/get_errors')
def get_errors():
    """Get any pending errors from starcluster background processes."""
    starcluster.subprocesses.poll()
    errors = starcluster.subprocesses.pop_errors()
    return jsonify({
        'status': 'ok',
        'errors': errors
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


@app.route('/spot_history')
def spot_prices():
    type_list = request.args.get('instance_types')
    if type_list is None:
        instance_types = ['p2.xlarge', 'p3.2xlarge']
    else:
        instance_types = type_list.split(',')
    prices = []
    try:
        for instance_type in instance_types:
            current, average, max = starcluster.spot_history(instance_type)
            prices.append(dict(
                instance_type=instance_type,
                current=current,
                average=average,
                max=max
            ))
    except subprocess.CalledProcessError as e:
        return jsonify({
            'status': 'error',
            'error': 'An error occurred while running starcluster spothistory'
        })
    return jsonify({
        'status': 'ok',
        'prices': prices
    })


if __name__ == '__main__':
    lb.start_polling()
    app.run(host=args.host_ip, port=args.port)

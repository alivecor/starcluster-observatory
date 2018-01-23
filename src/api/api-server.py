"""A simple server for directing starcluster from another ec2 instance in our subnet."""
import argparse
from flask import Flask
from flask import jsonify
from flask import request
import os
import re
import schedule
from threading import Thread
import time


parser = argparse.ArgumentParser(description='Run a server which exposes the starcluster and qstat APIs.', allow_abbrev=True)
parser.add_argument('--host_ip', default='0.0.0.0', type=str, help='IP address of interface to listen on.')
parser.add_argument('--port', default=6360, type=int, help='Port to listen on.')
parser.add_argument('--cluster', default='dev', type=int, help='Name of the cluster to manage.')
parser.add_argument('--starcluster_config', default='/etc/starcluster/config', type=int, help='Path to starcluster config file.')
parser.add_argument('--idle_timeout', default=30, type=int, help='Shut down nodes if idle longer than this many minutes.')

args = parser.parse_args()


app = Flask(__name__)

HOST_IP = args.host_ip
PORT = args.port
CLUSTER_NAME = args.cluster

STARCLUSTER_PATH = '/usr/local/bin/starcluster'


# Check queue status

def get_cluster_status(cluster_name):
    """Get uptime and  node list from cluster."""
    command = '%s listclusters %s' % (STARCLUSTER_PATH, cluster_name)
    try:
        result = subprocess.check_output([command], env=ENV, shell=True)
    except subprocess.CalledProcessError as e:
        return jsonify({'status': 'error', 'error': 'An error occurred while running starcluster listclusters'})
    lines = result.split('\n')
    uptime_line = next((l for l in lines if 'Uptime' in l), None)
    node_lines = [l for l in lines if 'compute.amazonaws.com' in l]
    uptime = uptime_line.split(',')[1].strip()
    nodes = [line.lstrip().split(' ')[0] for line in node_lines]
    return uptime, nodes


def filter_cluster_name(cluster_name):
    """Filter cluster_name argument, only allow alphanumerics and .-_"""
    return re.sub('(?!-)\W', '', cluster_name)


@app.route('/status/<cluster_name>')
def cluster_status(cluster_name):
    uptime, nodes = get_cluster_status(filter_cluster_name(cluster_name))
    return jsonify({
        'status': 'ok',
        'uptime': uptime,
        'nodes': nodes
    })


@app.route('/restart/<cluster_name>')
def cluster_restart(cluster_name):
    command = '%s restart %s' % (STARCLUSTER_PATH, filter_cluster_name(cluster_name))
    try:
        result = subprocess.check_output([command], env=ENV, shell=True)
    except subprocess.CalledProcessError as e:
        return jsonify({
            'status': 'error',
            'error': 'An error occurred while running starcluster restart'
        })
    return jsonify({
        'status': 'ok'
    })


@app.route('/qhost/<cluster_name>')
def cluster_qhost(cluster_name):
    command = '%s sshmaster %s "qhost"' % (STARCLUSTER_PATH, filter_cluster_name(cluster_name))
    try:
        result = subprocess.check_output([command], env=ENV, shell=True)
    except subprocess.CalledProcessError as e:
        return jsonify({
            'status': 'error',
            'error': 'An error occurred while running qhost'
        })
    return result


@app.route('/qstat/<cluster_name>')
def cluster_qstat(cluster_name):
    command = '%s sshmaster %s "qstat"' % (STARCLUSTER_PATH, filter_cluster_name(cluster_name))
    try:
        result = subprocess.check_output([command], env=ENV, shell=True)
    except subprocess.CalledProcessError as e:
        return jsonify({
            'status': 'error',
            'error': 'An error occurred while running qstat'
        })
    return result


@app.route('/resize/<cluster_name>')
def cluster_resize(cluster_name):
    cluster_name = filter_cluster_name(cluster_name)
    requested_size = int(request.args.get('n'))
    if requested_size < 1 or requested_size > 10:
        return jsonify({
            'status': 'error',
            'error': 'requested size %d not allowed' % requested_size
        })
    _, nodes = get_cluster_status(cluster_name)
    running_size = len(nodes)

    if requested_size > running_size:
        # Grow the cluster
        add_size = requested_size - running_size
        command = '%s addnode -n %d -b 2.2 %s' % (STARCLUSTER_PATH, add_size, cluster_name)
        try:
            result = subprocess.check_output([command], env=ENV, shell=True)
        except subprocess.CalledProcessError as e:
            return jsonify({
                'status': 'error',
                'error': 'An error occurred while running starcluster addnode'
            })
    if requested_size < running_size:
        remove_size = running_size - requested_size
        remove_nodes = nodes[-remove_size:]  # Always remove the last nodes added.
        command = '%s removenode -c --force %s %s' % (STARCLUSTER_PATH, cluster_name, ' '.join(remove_nodes))
        try:
            result = subprocess.check_output([command], env=ENV, shell=True)
        except subprocess.CalledProcessError as e:
            return jsonify({
            'status': 'error',
            'error': 'An error occurred while running starcluster removenode'
            })
    return jsonify({
        'status': 'ok',
        'old_size': running_size,
        'new_size': requested_size
    })


def run_schedule():
    """Run loop for the background task scheduler thread."""
    while 1:
        schedule.run_pending()
        time.sleep(1)


idle_nodes = {}  # Maps node name to first time node was detected idle.
def check_idle():



if __name__ == '__main__':
    schedule.every(60).seconds.do(run_every_10_seconds)
    t = Thread(target=run_schedule)
    t.start()
    app.run(host=HOST_IP, port=PORT)

"""A simple server for directing starcluster from another ec2 instance in our subnet."""
import argparse
from flask import Flask
from flask import render_template
from flask import request
import os
import re
import requests
import subprocess

import aws_static


parser = argparse.ArgumentParser(description='Run a dashboard web server exposing methods to administer StarCluster.', allow_abbrev=True)
parser.add_argument('--host_ip', default='0.0.0.0', type=str, help='IP address of interface to listen on.')
parser.add_argument('--port', default=6360, type=int, help='Port to listen on.')
parser.add_argument('--api_server_host', default='127.0.0.1', type=str, help='IP address of the backend.')
parser.add_argument('--api_server_port', default=6361, type=int, help='Port to use to connect to API server.')

args = parser.parse_args()


app = Flask(__name__)


def static_url(path):
    return os.path.join('/observatory/static/', path)


@app.route('/')
def homepage():
    # Get cluster status
    return nodes_tab()


@app.route('/jobs_tab.html')
def jobs_tab():
    search_query = request.args.get('search')
    # Get nodes from backend service
    result = requests.get('http://%s:%s/qstat' % (args.api_server_host, args.api_server_port))
    jobs = result.json()
    pending_jobs = [j for j in jobs if j['state'] == 'pending']
    running_jobs = [j for j in jobs if j['state'] == 'running']
    return render_template('jobs.html',
                           static_url=static_url,
                           jobs=jobs,
                           pending_jobs=len(pending_jobs),
                           running_jobs=len(running_jobs))


@app.route('/nodes_tab.html')
def nodes_tab():
    search_query = request.args.get('search')
    # Get hosts from backend service
    total_cost = 0.0
    sge_hosts_results = requests.get('http://%s:%s/qhost' % (args.api_server_host, args.api_server_port))
    hosts = sge_hosts_results.json()

    instances_results = aws_instances = requests.get('http://%s:%s/instances' % (args.api_server_host, args.api_server_port))
    instances_by_alias = {i['alias'] : i for i in instances_results.json() if 'alias' in i}
    nodes = []
    for host in hosts:
        host_dict = host.copy()
        if host['name'] in instances_by_alias:
            instance = instances_by_alias[host['name']]
            host_dict['public_ip'] = instance['public_ip']
            host_dict['state'] = instance['state']
            host_dict['type'] = instance['type']
            host_dict['uptime'] = instance['uptime']
            if instance['type'] in aws_static.ondemand_instance_cost:
                total_cost += aws_static.ondemand_instance_cost[instance['type']]
        nodes.append(host_dict)

    return render_template('nodes.html',
                           static_url=static_url,
                           hosts=nodes,
                           host_count=len(nodes),
                           total_cost=total_cost)


@app.route('/add_node')
def add_node():
    node_type = request.args.get('instance_type')
    # Add a node
    return ''


@app.route('/remove_node')
def remove_node():
    # Remove specified node
    return ''


@app.route('/cancel_job')
def cancel_job():
    # Cancel the specified job
    return ''


if __name__ == '__main__':
    app.run(
        host=args.host_ip,
        port=args.port
    )

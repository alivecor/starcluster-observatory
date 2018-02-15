"""A simple server for directing starcluster from another ec2 instance in our subnet."""
import argparse
import datetime
from flask import Flask
from flask import redirect
from flask import render_template
from flask import request
import os
import pytz
import re
import requests
import subprocess

import aws_static


parser = argparse.ArgumentParser(description='Run a dashboard web server exposing methods to administer StarCluster.')
parser.add_argument('--host_ip', default='0.0.0.0', type=str, help='IP address of interface to listen on.')
parser.add_argument('--port', default=6360, type=int, help='Port to listen on.')
parser.add_argument('--api_server_host', default='127.0.0.1', type=str, help='IP address of the backend.')
parser.add_argument('--api_server_port', default=6361, type=int, help='Port to use to connect to API server.')
parser.add_argument('--instance_types', default='p2.xlarge,p3.2xlarge', type=str, help='Instance types user is allowed to launch.')
args = parser.parse_args()

# TODO: make timezone a parameter or infer from region.
timezone = pytz.timezone('America/Los_Angeles')

app = Flask(__name__)

url_prefix = '/observatory'
def static_url(path):
    return os.path.join(url_prefix, 'static', path)


@app.route('/')
def homepage():
    # Get cluster status
    return nodes_tab()


def get_jobs():
    """Get all queued jobs from backend."""
    result = requests.get('http://%s:%s/qstat' % (args.api_server_host, args.api_server_port))
    jobs = []
    if result:
        jobs = result.json()
    for job in jobs:
        if 'submission_timestamp' in job:
            timestamp = int(job['submission_timestamp'])
            dt = datetime.datetime.fromtimestamp(timestamp, tz=timezone)
            job['submission_time'] = dt.strftime('%Y-%m-%d %I:%M:%S %p')
    return jobs


@app.route('/jobs_tab.html')
def jobs_tab():
    """Render jobs tab with navigation."""
    jobs = get_jobs()
    pending_jobs = [j for j in jobs if j['state'] == 'pending']
    running_jobs = [j for j in jobs if j['state'] == 'running']
    return render_template('jobs.html',
                           static_url=static_url,
                           jobs=jobs,
                           pending_jobs=len(pending_jobs),
                           running_jobs=len(running_jobs))


@app.route('/jobs_content.html')
def jobs_content():
    """Render jobs tab content only, no navigation."""
    jobs = get_jobs()
    pending_jobs = [j for j in jobs if j['state'] == 'pending']
    running_jobs = [j for j in jobs if j['state'] == 'running']
    return render_template('jobs_content.html',
                           static_url=static_url,
                           jobs=jobs,
                           pending_jobs=len(pending_jobs),
                           running_jobs=len(running_jobs))


def get_nodes_and_cost():
    """Get list of nodes and total cost from backend."""
    total_cost = 0.0
    sge_hosts_results = requests.get('http://%s:%s/qhost' % (args.api_server_host, args.api_server_port))
    hosts_by_name = {h['name'] : h for h in sge_hosts_results.json() if 'name' in h}

    instances_results = requests.get('http://%s:%s/instances' % (args.api_server_host, args.api_server_port))
    instances = instances_results.json()

    nodes = []
    for instance in instances:
        name = instance['name']
        state = instance['state']
        if name in hosts_by_name:
            sge_host = hosts_by_name[name]
            host_dict = sge_host.copy()
        else:
            # If an instance is visible in starcluster listclusters, but not qhost, then it is probably booting up.
            # (or failed to join SGE)
            host_dict = {}
            state = 'pending'
        host_dict['public_ip'] = instance['public_ip']
        host_dict['state'] = state
        host_dict['type'] = instance['type']
        host_dict['uptime'] = instance['uptime']
        if instance['type'] in aws_static.ondemand_instance_cost:
            total_cost += aws_static.ondemand_instance_cost[instance['type']]
        nodes.append(host_dict)
    return nodes, total_cost


@app.route('/nodes_tab.html')
def nodes_tab():
    """Render nodes tab."""
    nodes, total_cost = get_nodes_and_cost()
    return render_template('nodes.html',
                           static_url=static_url,
                           hosts=nodes,
                           host_count=len(nodes),
                           total_cost=total_cost)


@app.route('/nodes_content.html')
def nodes_content():
    """Render nodes list content only no navigation."""
    nodes, total_cost = get_nodes_and_cost()
    return render_template('nodes_content.html',
                           static_url=static_url,
                           hosts=nodes,
                           host_count=len(nodes),
                           total_cost=total_cost)


@app.route('/nodes_alerts.html')
def nodes_alerts():
    """Render alerts for nodes page."""
    alerts = [dict(
        message= 'test alert: an error happened'
    )]
    return render_template('alerts.html', alerts=alerts)


@app.route('/add_node')
def add_node():
    instance_type = request.args.get('instance_type')
    # Add a node
    request_url = 'http://%s:%s/nodes/add' % (args.api_server_host, args.api_server_port)
    if instance_type:
        request_url = request_url + '?instance_type=%s' % instance_type
    add_result = requests.get(request_url)
    return redirect(os.path.join(url_prefix, 'nodes_content.html'), code=302)


@app.route('/remove_node')
def remove_node():
    alias = request.args.get('alias')
    remove_result = requests.get('http://%s:%s/nodes/%s/remove' % (args.api_server_host, args.api_server_port, alias))
    # Remove specified node
    return redirect(os.path.join(url_prefix, 'nodes_content.html'), code=302)


@app.route('/launch_popover')
def launch_popover():
    """Returns HTML content to populate the body of launch new instance popover."""
    prices_results = requests.get('http://%s:%s/spot_history?instance_types=%s' % (
        args.api_server_host, args.api_server_port, args.instance_types
    ))
    results = prices_results.json()
    prices = results['prices']
    first = True
    for price in prices:
        price['first'] = first
        if first:
            first = False
        # Add to price dict the on-demand cost and configuration.
        instance_type = price['instance_type']
        if instance_type in aws_static.ondemand_instance_cost:
            price['on_demand'] = aws_static.ondemand_instance_cost[instance_type]
        if instance_type in aws_static.instance_types:
            price['configuration'] = aws_static.instance_types[instance_type]
    return render_template('launch_popover.html', prices=prices)


@app.route('/cancel_job')
def cancel_job():
    # Cancel the specified job
    jid = request.args.get('jid')
    cancel_result = requests.get('http://%s:%s/jobs/%s/cancel' % (args.api_server_host, args.api_server_port, jid))
    return redirect(os.path.join(url_prefix, 'jobs_content.html'), code=302)


if __name__ == '__main__':
    app.run(
        host=args.host_ip,
        port=args.port
    )

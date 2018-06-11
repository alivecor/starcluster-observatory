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

from alert_queue import *
import aws_static


parser = argparse.ArgumentParser(description='Run a dashboard web server exposing methods to administer StarCluster.')
parser.add_argument('--host_ip', default='0.0.0.0', type=str, help='IP address of interface to listen on.')
parser.add_argument('--port', default=6360, type=int, help='Port to listen on.')
parser.add_argument('--api_server_host', default='127.0.0.1', type=str, help='IP address of the backend.')
parser.add_argument('--api_server_port', default=6361, type=int, help='Port to use to connect to API server.')
parser.add_argument('--instance_types', default='c4.large,p2.xlarge,p3.2xlarge', type=str, help='Instance types user is allowed to launch.')
parser.add_argument('--zones', type=str, help='Availability zones user is allowed to launch in.')
parser.add_argument('--subnets', type=str, help='Subnets in VPC, for use with zones.')
args = parser.parse_args()

# TODO: make timezone a parameter or infer from region.
timezone = pytz.timezone('America/Los_Angeles')

app = Flask(__name__)

alert_queue = AlertQueue()


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
    # Get host list from SGE.
    sge_hosts_results = requests.get('http://%s:%s/qhost' % (args.api_server_host, args.api_server_port))
    hosts_by_name = {h['name'] : h for h in sge_hosts_results.json() if 'name' in h}

    # Get instance list from starcluster, because SGE host list doesn't show failed or pending nodes.
    instances_results = requests.get('http://%s:%s/instances' % (args.api_server_host, args.api_server_port))
    instances = instances_results.json()

    # Get job list from SGE, so we can show which jobs are running on each host.
    jobs = get_jobs()
    running_jobs = [j for j in jobs if j['state'] == 'running']
    jobs_by_host = {}
    for job in running_jobs:
        job_host = job['queue_name'].split('@')[-1]
        job_id = job['job_id']
        if job_host in jobs_by_host:
            jobs_by_host[job_host].append(job_id)
        else:
            jobs_by_host[job_host] = [job_id]

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
        if name in jobs_by_host:
            host_dict['job_ids'] = ','.join([str(jid) for jid in jobs_by_host[name]])
            host_dict['disable_terminate'] = True  # Disable termination if node running jobs.
        else:
            host_dict['job_ids'] = ''
        host_dict['public_ip'] = instance['public_ip']
        host_dict['state'] = state
        host_dict['type'] = instance['type']
        host_dict['uptime'] = instance['uptime']
        if 'load_avg' in host_dict:
            try:
                load_pct = float(host_dict['load_avg']) * 100
                host_dict['load_avg'] = int(load_pct)
            except ValueError:
                host_dict['load_avg'] = '-'
        if not instance['spot_request'] is None:
            prices_results = requests.get('http://%s:%s/spot_history?instance_types=%s' % (
                args.api_server_host, args.api_server_port, instance['type']
            ))
            results = prices_results.json()
            cost = float(results['prices'][0]['current'])
            host_dict['cost'] = '$%.2f' % cost
            total_cost += cost
        elif instance['type'] in aws_static.ondemand_instance_cost:
            cost = aws_static.ondemand_instance_cost[instance['type']]
            host_dict['cost'] = '$%.2f' % cost
            total_cost += cost
        nodes.append(host_dict)
    return nodes, total_cost


def check_errors():
    """Check API server for list of errors, create alerts for all pending errors."""
    get_errors_response = requests.get('http://%s:%s/get_errors' % (args.api_server_host, args.api_server_port))
    get_errors_json = get_errors_response.json()
    errors = get_errors_json['errors']
    for error in errors:
        stderr = error['error']
        lines = stderr.split('\n')
        # Find first line containing ERROR, or first line
        error_text = lines[0]
        for line in lines:
            if 'ERROR' in line:
                error_text = line
                break
        # Add it to alert queue as an error
        alert_queue.add_alert(Alert.ERROR, error_text, '', 300)


@app.route('/nodes_tab.html')
def nodes_tab():
    """Render nodes tab."""
    nodes, total_cost = get_nodes_and_cost()
    return render_template('nodes.html',
                           static_url=static_url,
                           hosts=nodes,
                           host_count=len(nodes),
                           total_cost='%.2f' % total_cost)


@app.route('/nodes_content.html')
def nodes_content():
    """Render nodes list content only no navigation."""
    nodes, total_cost = get_nodes_and_cost()
    return render_template('nodes_content.html',
                           static_url=static_url,
                           hosts=nodes,
                           host_count=len(nodes),
                           total_cost='%.2f' % total_cost)


@app.route('/nodes_alerts')
def nodes_alerts():
    """Render alerts for nodes page."""
    check_errors()
    alerts = alert_queue.get_alerts()
    return render_template('alerts.html', alerts=alerts)


@app.route('/add_node')
def add_node():
    instance_type = request.args.get('instance_type')
    spot_bid = request.args.get('spot_bid')
    zone = request.args.get('zone')
    subnet = request.args.get('subnet')
    # Add a node
    request_url = 'http://%s:%s/nodes/add' % (args.api_server_host, args.api_server_port)
    if instance_type:
        request_url = request_url + '?instance_type=%s' % instance_type
        # For now, bid the on-demand instance price.
        # TODO: allow user to specify bid or bidding policy.
        if (not spot_bid is None) and (instance_type in aws_static.ondemand_instance_cost):
            bid_price = aws_static.ondemand_instance_cost[instance_type]
            request_url = request_url + '&spot_bid=%s' % bid_price
    if zone:
        request_url = request_url + '?zone=%s' % zone
    if subnet:
        request_url = request_url + '?subnet=%s' % subnet
    add_result = requests.get(request_url)
    alert_queue.add_alert(Alert.INFO, 'Instance Launching', instance_type, 60)
    return redirect(os.path.join(url_prefix, 'nodes_content.html'), code=302)


@app.route('/remove_node')
def remove_node():
    alias = request.args.get('alias')
    remove_result = requests.get('http://%s:%s/nodes/%s/remove' % (args.api_server_host, args.api_server_port, alias))
    # Remove specified node
    alert_queue.add_alert(Alert.INFO, 'Shutting Down', alias, 60)
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
    zones = []
    if not args.zones is None:
        zones = args.zones.split(',')
    return render_template('launch_popover.html', prices=prices, zones=zones)


@app.route('/cancel_job')
def cancel_job():
    # Cancel the specified job
    jid = request.args.get('jid')
    cancel_result = requests.get('http://%s:%s/jobs/%s/cancel' % (args.api_server_host, args.api_server_port, jid))
    return redirect(os.path.join(url_prefix, 'jobs_content.html'), code=302)


@app.route('/clear_alert')
def clear_alert():
    """Close the specified alert.  Returns the updated content of the alerts window."""
    alert_id = request.args.get('alert_id')
    alert_queue.remove_alert(alert_id)
    return nodes_alerts()


if __name__ == '__main__':
    app.run(
        host=args.host_ip,
        port=args.port
    )

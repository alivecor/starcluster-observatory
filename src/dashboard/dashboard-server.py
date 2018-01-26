"""A simple server for directing starcluster from another ec2 instance in our subnet."""
import argparse
from flask import Flask
from flask import render_template
from flask import request
import os
import re
import subprocess


parser = argparse.ArgumentParser(description='Run a dashboard web server exposing methods to administer StarCluster.', allow_abbrev=True)
parser.add_argument('--host_ip', default='0.0.0.0', type=str, help='IP address of interface to listen on.')
parser.add_argument('--port', default=6360, type=int, help='Port to listen on.')
parser.add_argument('--api_server_host', default='127.0.0.1', type=str, help='IP address of the backend.')
parser.add_argument('--api_server_port', default=6361, type=int, help='Port to use to connect to API server.')

args = parser.parse_args()


app = Flask(__name__)


@app.route('/')
def homepage():
    # Get cluster status
    return render_template('layout.html')


@app.route('/jobs_tab')
def jobs_tab():
    # Render jobs tab HTML
    return 'Jobs'


@app.route('/nodes_tab')
def nodes_tab():
    # Render nodes tab HTML
    return 'Nodes'


@app.route('/add_node')
def add_node():
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
        host=HOST_IP,
        port=PORT
    )

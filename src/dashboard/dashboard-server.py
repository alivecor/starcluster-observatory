"""A simple server for directing starcluster from another ec2 instance in our subnet."""
import argparse
from flask import Flask
from flask import jsonify
from flask import request
import os
import re
import subprocess


app = Flask(__name__)

HOST_IP= '0.0.0.0'
PORT= 6360
CLUSTER_NAME= 'gpu'
STARCLUSTER_PATH= '/usr/local/bin/starcluster'
ENV= dict(os.environ)
ENV['HOME'] = '/home/sgeadmin'


app.run(
    host=HOST_IP,
    port=PORT
)

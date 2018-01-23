"""Wrapper for the starcluster command."""
import os
import re
import subprocess


STARCLUSTER_PATH = '/usr/local/bin/starcluster'
CONFIG_PATH = '/etc/starcluster/config'


def _starcluster_command():
    return '%s -c %s' % (STARCLUSTER_PATH, CONFIG_PATH)


def _filter_cluster_name(cluster_name):
    """Filter cluster_name argument, only allow alphanumerics and .-_"""
    return re.sub('(?!-)\W', '', cluster_name)


def get_status(cluster_name, config_path=None):
    """Get uptime and node list from cluster."""
    command = _starcluster_command() + ' listclusters ' + _filter_cluster_name(cluster_name)
    result = subprocess.check_output([command], shell=True)
    lines = result.split('\n')
    uptime_line = next((l for l in lines if 'Uptime' in l), None)
    node_lines = [l for l in lines if 'compute.amazonaws.com' in l]
    uptime = uptime_line.split(',')[1].strip()
    nodes = [line.lstrip().split(' ')[0] for line in node_lines]
    return uptime, nodes


def add_node(cluster_name, instance_type=None):
    """Adds a node to the specified cluster."""
    i_flag = ''
    if instance_type:
        i_flag = '-I ' + instance_type
    command = _starcluster_command() + ' addnode ' + i_flag + ' ' + _filter_cluster_name(cluster_name)
    subprocess.check_output([command], shell=True)


def remove_node(cluster_name, node_alias):
    """Removes the specified node from cluster."""
    command = _starcluster_command() + ' removenode -c -f -a ' + node_alias + ' ' + _filter_cluster_name(cluster_name)
    subprocess.check_output([command], shell=True)

"""Wrapper for the starcluster command."""
import re
import subprocess
import subprocess_queue


STARCLUSTER_PATH = '/usr/local/bin/starcluster'
CONFIG_PATH = '/etc/starcluster/config'


subprocess_q = subprocess_queue.SubprocessQueue()


def _starcluster_command():
    return '%s -c %s' % (STARCLUSTER_PATH, CONFIG_PATH)


def _is_indented(text):
    return text.startswith(' ') or text.startswith('\t')


def _filter_cluster_name(cluster_name):
    """Filter cluster_name argument, only allow alphanumerics and .-_"""
    return re.sub('(?!-)\W', '', cluster_name)


def _parse_cluster(cluster_name, listclusters_output):
    """Parse cluster details from listclusters_output."""
    cluster_attributes = {
        'name': cluster_name
    }
    lines = listclusters_output.split('\n')
    for i, line in enumerate(lines):
        components = line.split(': ')
        if line.startswith('Cluster nodes:'):
            # Add cluster node list
            li = i+1
            nodes = []
            while _is_indented(lines[li]):
                components = lines[li].strip().split(' ')
                spot_request = None
                if len(components) == 6 and components[4].endswith('spot'):
                    spot_request = components[5][:-1]
                nodes.append({
                    'alias': components[0],
                    'state': components[1],
                    'instance_id': components[2],
                    'hostname': components[3],
                    'spot_request': spot_request
                })
                li += 1
            cluster_attributes['nodes'] = nodes
        elif len(components) == 2:
            # Add cluster attribute to response dict
            cluster_attributes[components[0]] = components[1].strip()
    return cluster_attributes


def _parse_instance(instance_output):
    """Parse AWS instance details from listinstances output."""
    instance_attributes = {}
    lines = instance_output.split('\n')
    for line in lines:
        components = line.split(': ')
        if line.startswith('tags:'):
            # Parse instance tags
            tags_line = components[1].strip()
            tags = tags_line.split(', ')
            for tag in tags:
                kv = tag.split('=')
                if len(kv) == 2:
                    instance_attributes[kv[0].lower()] = kv[1].strip()
        elif len(components) == 2:
            # Add instance attribute to response dict
            instance_attributes[components[0]] = components[1].strip()
    return instance_attributes


def get_status(cluster_name):
    """Get uptime and node list from cluster."""
    command = _starcluster_command() + ' listclusters ' + _filter_cluster_name(cluster_name)
    result = subprocess.check_output([command], shell=True)
    lines = result.decode('utf8').split('\n')
    uptime_line = next((l for l in lines if 'Uptime' in l), None)
    node_lines = [l for l in lines if 'compute.amazonaws.com' in l]
    uptime = uptime_line.split(',')[1].strip()
    nodes = [line.lstrip().split(' ')[0] for line in node_lines]
    return uptime, nodes


def list_clusters():
    """List all clusters, including their instance lists."""
    command = _starcluster_command() + ' listclusters'
    result = subprocess.check_output([command], shell=True)
    # listclusters output adds ----------------------------- as a header to the description of each cluster.
    sections = re.compile('---*').split(result.decode('utf8'))
    clusters = []
    for i in range(1, len(sections), 2):
        cluster_name = sections[i].split(' ')[0].strip()
        cluster_attributes = sections[i+1]
        clusters.append(_parse_cluster(cluster_name, cluster_attributes))
    return clusters


def list_instances():
    """List all running instances.

    Returns:
        [{}] - The list of running instances.
    """
    command = _starcluster_command() + ' listinstances'
    result = subprocess.check_output([command], shell=True)
    sections = result.decode('utf8').strip().split('\n\n')
    instances = []
    for section in sections:
        instances.append(_parse_instance(section))
    return instances


def spot_history(instance_type):
    """Get spot bid history for the specified instance type.

    Args:
        instance_type (string) - The instance type i.e. p2.xlarge

    Returns:
        current, average, max (string, string, string) prices in USD.
    """
    command = _starcluster_command() + ' spothistory ' + instance_type
    result = subprocess.check_output([command], shell=True)
    lines = result.decode('utf8').strip().split('\n')
    current = ''
    average = ''
    max = ''
    for line in lines:
        if 'Current price:' in line:
            current = line.split('$')[-1]
        elif 'Max price:' in line:
            max = line.split('$')[-1]
        elif 'Average price:' in line:
            average = line.split('$')[-1]
    return current, average, max


def add_node(cluster_name, instance_type=None, ami=None, spot_bid=None, zone=None, subnet=None):
    """Adds a node to the specified cluster.
    Note: Launching a new node node may take several minutes, but add_node returns
    immediately after launching the subprocess and does not wait.

    Args:
        cluster_name (string) - The name of the cluster
        instance_type (string) - The type of instance i.e. p3.2xlarge.
        ami (string) - The id of the amazon machine image to launch.
        spot_bid (string) - If specified, launch a spot instance at the this bid price.  Otherwise, launch an on-demand instance.
        zone (string) - The availability zone to add the node to, i.e. us-west-2a
        subnet (string) - For use with --zone in a VPC - the VPC subnet for the specified availability zone.
    """
    command_args = [STARCLUSTER_PATH, '-c', CONFIG_PATH, 'addnode']
    if not instance_type is None:
        command_args.append('-I')
        command_args.append(instance_type)
    if not ami is None:
        command_args.append('-i')
        command_args.append(ami)
    if not spot_bid is None:
        command_args.append('-b')
        command_args.append(spot_bid)
    if not zone is None:
        command_args.append('-z')
        command_args.append(zone)
    if not subnet is None:
        command_args.append('-s')
        command_args.append(subnet)
    command_args.append(_filter_cluster_name(cluster_name))
    # print('Detaching: ' + str(command_args))
    subprocess_q.run_command(command_args, 'add %s' % instance_type)


def remove_node(cluster_name, node_alias):
    """Removes the specified node from cluster.
    Note: Terminating a new node node may take several minutes, but remove_node returns
    immediately after launching the subprocess and does not wait.

    Args:
        cluster_name (string) - The name of the cluster
        node_alias (string) - The alias of the node to remove
    """
    command_args = [STARCLUSTER_PATH, '-c', CONFIG_PATH, 'removenode', '--confirm', '-f', '-a', node_alias, _filter_cluster_name(cluster_name)]
    # print('Detaching: ' + str(command_args))
    subprocess_q.run_command(command_args, 'remove node %s' % node_alias)

"""Wrapper for SGE commands to queue state."""
import os
import subprocess
import xml.etree.ElementTree

QSTAT_PATH = '/opt/sge6/bin/linux-x64/qstat'
QHOST_PATH = '/opt/sge6/bin/linux-x64/qhost'
QDEL_PATH = '/opt/sge6/bin/linux-x64/qdel'


ENV = dict(os.environ)
ENV['HOME'] = '/home/sgeadmin'
ENV['SGE_CELL'] = 'default'
ENV['SGE_EXECD_PORT'] = '63232'
ENV['SGE_QMASTER_PORT'] = '63231'
ENV['SGE_ROOT'] = '/opt/sge6'
ENV['SGE_CLUSTER_NAME'] = 'starcluster'


def _text_or_none(root, tag):
    """Returns the text value of the child element with tag, or None."""
    elem = root.find(tag)
    return None if elem is None else elem.text


def _parse_job_list(job_list_element):
    """Parses a job_list element, which is (confusingly) is a single entry in a job list."""
    def text_or_none(tag):
        elem = job_list_element.find(tag)
        return None if elem is None else elem.text
    return {
        'job_id': int(job_list_element.find('JB_job_number').text),
        'state': job_list_element.get('state'),
        'name': job_list_element.find('JB_name').text,
        'owner': job_list_element.find('JB_owner').text,
        'state_code': job_list_element.find('state').text,
        'start_time': _text_or_none(job_list_element, 'JAT_start_time'),
        'submission_time': _text_or_none(job_list_element, 'JB_submission_time'),
        'queue_name': job_list_element.find('queue_name').text
    }


def qstat():
    command = '%s -u "*" -xml' % QSTAT_PATH
    result_xml = subprocess.check_output([command], env=ENV, shell=True)
    root_element = xml.etree.ElementTree.fromstring(result_xml)
    queue_info_element = root_element.find('queue_info')  # Queued Jobs
    job_info_element = root_element.find('job_info')  # Pending Jobs
    queued_jobs = [_parse_job_list(job_list) for job_list in queue_info_element]
    pending_jobs = [_parse_job_list(job_list) for job_list in job_info_element]
    return queued_jobs, pending_jobs


def qdel(jid):
    """Cancel a running job."""
    command = '%s -j %d' % (QDEL_PATH, jid)
    subprocess.check_output([command], env=ENV, shell=True)


def qstat_job_details(jid, state=None, queue_name=None):
    """Get detailed state of a running job."""
    command = '%s -j %d -xml' % (QSTAT_PATH, jid)
    result_xml = subprocess.check_output([command], env=ENV, shell=True)
    root_element = xml.etree.ElementTree.fromstring(result_xml)
    job_info_element = root_element[0][0]
    job_mail_list = job_info_element.find('JB_mail_list')[0]
    stdout_path_list = job_info_element.find('JB_stdout_path_list')
    stderr_path_list = job_info_element.find('JB_stderr_path_list')
    hard_queue_list = job_info_element.find('JB_hard_queue_list')
    if hard_queue_list is not None:
        destination_ident_list = hard_queue_list.find('destin_ident_list')
        qr_name = destination_ident_list[0]
    else:
        qr_name = None
    predecessors = []
    predecessor_list = job_info_element.find('JB_jid_predecessor_list')
    if predecessor_list is not None:
        job_predecessors = predecessor_list.find('job_predecessors')
        if job_predecessors is not None:
            for predecessor in job_predecessors:
                predecessors.append(int(predecessor.text))
    job_details = {
        'job_id': int(job_info_element.find('JB_job_number').text),
        'owner': job_info_element.find('JB_owner').text,
        'name': job_info_element.find('JB_job_name').text,
        'executable': job_info_element.find('JB_script_file').text,
        'qr_name': qr_name.text if qr_name is not None else '',
        'predecessors': predecessors,
        'stdout_path': _text_or_none(stdout_path_list[0], 'PN_path') if stdout_path_list else '',
        'stderr_path': _text_or_none(stderr_path_list[0], 'PN_path') if stderr_path_list else '',
        'priority': job_info_element.find('JB_priority').text,
        'submission_timestamp': job_info_element.find('JB_submission_time').text
    }
    if state:
        job_details['state'] = state
    if queue_name:
        job_details['queue_name'] = queue_name
    # Get job args
    job_args = []
    job_arg_list = job_info_element.find('JB_job_args')
    if job_arg_list:
        for e in job_arg_list:
            job_args.append(e[0].text)
    job_details['job_args'] = job_args
    # Get environment
    env = {}
    job_env_list = job_info_element.find('JB_env_list')
    for e in job_env_list:
        variable_name = e[0].text
        if len(e) > 1:
            variable_value = e[1].text
        else:
            variable_value = ''
        env[variable_name] = variable_value
    job_details['env'] = env
    return job_details


def qhost():
    """Get list of hosts in grid and status."""
    command = '%s -xml' % QHOST_PATH
    result_xml = subprocess.check_output([command], env=ENV, shell=True)
    hosts_element = xml.etree.ElementTree.fromstring(result_xml)
    hosts = []
    for host_element in hosts_element:
        if host_element.get('name') == 'global':
            continue
        host = {
            'name': host_element.get('name')
        }
        for host_value in host_element:
            host[host_value.get('name')] = host_value.text
        hosts.append(host)
    return hosts

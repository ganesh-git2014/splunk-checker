'''_
@author: Curtis Yu
@contact: cuyu@splunk.com
@since: 3/8/16
'''
import logging
import sys
from multiprocessing import Pool, Manager
from xml.sax import saxutils
import xml.etree.ElementTree as ElementTree
# import default
import os
import time

path_prepend = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'lib')
sys.path.append(path_prepend)

from cluster_checker import ClusterChecker
from kvstore_helper import KVStoreHelper
from logger import setup_logger

SCHEME = """<scheme>
    <title>splunk checker</title>
    <description>splunk health checker</description>
    <use_external_validation>false</use_external_validation>
    <streaming_mode>xml</streaming_mode>

    <endpoint>
        <args>
            <arg name="name">
                <title>Splunk URI</title>
                <description>E.g. https://systest-auto-master:1901</description>
            </arg>
            <arg name="cluster_id">
                <title>cluster ID</title>
                <description>
                   A label for all splunk instances of the same cluster.
                </description>
            </arg>
            <arg name="role">
                <title>Role</title>
                <description>
                   Splunk role.
                </description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
            </arg>
            <arg name="username">
                <title>Username</title>
                <description>
                   Splunk username.
                </description>
            </arg>
            <arg name="password">
                <title>Password</title>
                <description>
                   Splunk password.
                </description>
            </arg>
        </args>
    </endpoint>
</scheme>
"""


def init_stream():
    sys.stdout.write("<stream>")


def fini_stream():
    sys.stdout.write("</stream>")


def send_data(buf, source, sourcetype):
    sys.stdout.write("<event><source>{0}</source><sourcetype>{1}</sourcetype><data>".format(source, sourcetype))
    sys.stdout.write(saxutils.escape(buf))
    sys.stdout.write("</data></event>")


def do_scheme():
    print SCHEME


def start_check(cluster_info, queue):
    # Init checker.
    enable_shcluster = True if cluster_info['enable_shcluster'] == 'True' else False
    enable_cluster = True if cluster_info['enable_cluster'] == 'True' else False
    checker = ClusterChecker(cluster_info['cluster_id'], enable_shcluster, enable_cluster,
                             int(cluster_info['search_factor']), int(cluster_info['replication_factor']))
    for peer_info in cluster_info['peers']:
        checker.add_peer(peer_info['splunk_uri'], peer_info['role'], peer_info['username'], peer_info['password'])

    # Start checking.
    results, warning_messages = checker.check_all_items(return_event=True)

    # Send events.
    for item in checker.check_points:
        if results:
            queue.put((results[item], 'check_stats', item,))
            queue.put((warning_messages[item], 'warning_msg', item,))
        else:
            queue.put(('Exception occurs when checking cluster {0}.'.format(cluster_info['cluster_id']), 'warning_msg',
                       item,))


def run():
    setup_logger()
    # Read the settings
    config_xml = sys.stdin.read()
    config_parsed = ElementTree.fromstring(config_xml)
    session_key = config_parsed.findall('.//session_key')[0].text
    server_uri = config_parsed.findall('.//server_uri')[0].text
    helper = KVStoreHelper(session_key)
    # Wait until mangodb starts.
    for i in xrange(10):
        try:
            cluster_info_list = helper.get_cluster_info(
                os.path.join(server_uri, 'servicesNS/nobody/splunk-checker/storage/collections/data/clusterinfo'))
        except:
            time.sleep(10)
        else:
            break
    else:
        raise Exception('Failed to get cluster info from kvstore.')

    manager = Manager()
    queue = manager.Queue()
    pool = Pool(processes=len(cluster_info_list))
    async_results = dict()

    for cluster_info in cluster_info_list:
        async_results[cluster_info['cluster_id']] = pool.apply_async(start_check, (cluster_info, queue,))

    for cluster_info in cluster_info_list:
        result = async_results[cluster_info['cluster_id']].get()
        if result:
            logging.root.error(
                'Exception occurs when checking cluster {0}: {1}'.format(cluster_info['cluster_id'], result))

    init_stream()
    while not queue.empty():
        send_data(*queue.get())
    fini_stream()


if __name__ == '__main__':
    if len(sys.argv) > 1:
        if sys.argv[1] == "--scheme":
            # Send the scheme will override the xml file defined under default/data/ui/manager/
            do_scheme()
        elif sys.argv[1] == "--test":
            print 'No tests for the scheme present'
        else:
            print 'Weird arguments provided'
    else:
        run()
    sys.exit(0)

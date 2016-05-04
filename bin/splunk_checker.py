'''_
@author: Curtis Yu
@contact: cuyu@splunk.com
@since: 3/8/16
'''
import sys
import threading
from xml.sax import saxutils
import xml.etree.ElementTree as ElementTree
# import default
import os
import time

path_prepend = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'lib')
sys.path.append(path_prepend)

from cluster_checker import ClusterChecker
from kvstore_helper import KVStoreHelper

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


class CheckThread(threading.Thread):
    def __init__(self, cluster_info):
        threading.Thread.__init__(self)
        self.cluster_info = cluster_info

    def run(self):
        # Init checker.
        enable_shcluster = True if self.cluster_info['enable_shcluster'] == 'True' else False
        enable_cluster = True if self.cluster_info['enable_cluster'] == 'True' else False
        checker = ClusterChecker(self.cluster_info['cluster_id'], enable_shcluster, enable_cluster,
                                 int(self.cluster_info['search_factor']), int(self.cluster_info['replication_factor']))
        for peer_info in self.cluster_info['peers']:
            checker.add_peer(peer_info['splunk_uri'], peer_info['role'], peer_info['username'], peer_info['password'])

        # Start checking.
        results, warning_messages = checker.check_all_items(return_event=True)

        # Send events.
        init_stream()
        for item in checker.check_points:
            if results:
                send_data(results[item], 'check_stats', item)
                send_data(warning_messages[item], 'warning_msg', item)
            else:
                send_data('Exception occurs when checking this cluster.', 'warning_msg', item)
        fini_stream()


def run():
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

    checker_list = []
    for cluster_info in cluster_info_list:
        CheckThread(cluster_info).run()


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

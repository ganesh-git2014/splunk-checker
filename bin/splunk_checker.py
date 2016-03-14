'''_
@author: Curtis Yu
@contact: cuyu@splunk.com
@since: 3/8/16
'''
import json
import sys
from xml.sax import saxutils
import xml.etree.ElementTree as ElementTree
# import default
import os

# Why cannot import from lib (as package) directly?

path_prepend = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'lib')
sys.path.append(path_prepend)

from cluster_checker import ClusterChecker
from constant import CHECK_ITEM

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


def run():
    # Read the settings
    config_xml = sys.stdin.read()
    # config_parsed = ElementTree.fromstring(config_xml)
    # for element in config_parsed.findall('.//param'):
    #     if element.attrib['name'] == 'folder':
    #         if element.text is not None:
    #             folder_path = element.text

    checker1 = ClusterChecker('env1')
    checker1.add_peer('https://systest-auto-master:1901', 'master', 'admin', 'changed')
    checker1.add_peer('https://systest-auto-sh1:1901', 'searchhead', 'admin', 'changed')
    checker1.add_peer('https://systest-auto-idx1:1901', 'indexer', 'admin', 'changed')
    checker1.add_peer('https://systest-auto-fwd1:1901', 'forwarder', 'admin', 'changed')
    result, warning_messages = checker1.check_all_items()

    checker2 = ClusterChecker('env2')
    checker2.add_peer('https://qa-systest-04.sv.splunk.com:1901', 'master', 'admin', 'changed')
    checker2.add_peer('https://qa-systest-05.sv.splunk.com:1900', 'indexer', 'admin', 'changed')
    checker2.add_peer('https://qa-systest-01.sv.splunk.com:1900', 'searchhead', 'admin', 'changed')
    result2, warning_messages2 = checker2.check_all_items()
    init_stream()
    send_data(checker1.transform_event(result), 'check_stats', 'check_stats')
    for item in CHECK_ITEM:
        send_data(checker1.transform_event(warning_messages[item]), 'warning_msg', item)
    send_data(checker2.transform_event(result2), 'check_stats', 'check_stats')
    for item in CHECK_ITEM:
        send_data(checker2.transform_event(warning_messages2[item]), 'warning_msg', item)
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

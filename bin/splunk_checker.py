'''_
@author: Curtis Yu
@contact: cuyu@splunk.com
@since: 3/8/16
'''
import json
import sys
import xml
import xml.etree.ElementTree as ElementTree
# import default
import os

# Why cannot import from lib (as package) directly?
path_prepend = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'lib')
sys.path.append(path_prepend)

from cluster_checker import ClusterChecker

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


def send_data(buf, sourcetype):
    sys.stdout.write("<event><sourcetype>{0}</sourcetype><data>".format(sourcetype))
    sys.stdout.write(xml.sax.saxutils.escape(buf))
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

    checker = ClusterChecker()
    checker.add_peer('https://systest-auto-master:1901', 'master', 'admin', 'changed')
    checker.add_peer('https://systest-auto-sh1:1901', 'searchhead', 'admin', 'changed')
    checker.add_peer('https://systest-auto-idx1:1901', 'indexer', 'admin', 'changed')
    checker.add_peer('https://systest-auto-fwd1:1901', 'forwarder', 'admin', 'changed')
    result, msg = checker.check_all_items()
    init_stream()
    send_data(json.dumps(result), 'check_stats')
    send_data(json.dumps(msg), 'warning_msg')
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

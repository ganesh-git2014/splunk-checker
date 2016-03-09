'''_
@author: Curtis Yu
@contact: cuyu@splunk.com
@since: 3/8/16
'''
import json
import sys
import xml
import xml.etree.ElementTree as ElementTree

from lib.cluster_checker import ClusterChecker

SCHEME = """<scheme>
    <title>splunk checker</title>
    <description>splunk health checker</description>
    <use_external_validation>true</use_external_validation>
    <streaming_mode>xml</streaming_mode>

    <endpoint>
        <args>
            <arg name="name">
                <title>Cluster name</title>
                <description>
                   Should be unique.
                </description>
            </arg>

            <arg name="folder">
                <title>Code Folder</title>
                <description>Input the folder path you want to analyze:</description>
            </arg>
        </args>
    </endpoint>
</scheme>
"""


def init_stream():
    sys.stdout.write("<stream>")


def fini_stream():
    sys.stdout.write("</stream>")


def send_data(buf):
    sys.stdout.write("<event><data>")
    sys.stdout.write(xml.sax.saxutils.escape(buf))
    sys.stdout.write("</data></event>")


def do_scheme():
    print SCHEME


def run():
    # Read the settings
    config_xml = sys.stdin.read()
    config_parsed = ElementTree.fromstring(config_xml)
    for element in config_parsed.findall('.//param'):
        if element.attrib['name'] == 'folder':
            if element.text is not None:
                folder_path = element.text

    checker = ClusterChecker()
    result = checker.check_all_items()
    init_stream()
    send_data(json.dumps(result))
    fini_stream()


if __name__ == '__main__':
    if len(sys.argv) > 1:
        if sys.argv[1] == "--scheme":
            do_scheme()
        elif sys.argv[1] == "--test":
            print 'No tests for the scheme present'
        else:
            print 'Weird arguments provided'
    else:
        run()
    sys.exit(0)

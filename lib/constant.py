'''_
@author: Curtis Yu
@contact: cuyu@splunk.com
@since: 3/8/16
'''


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


SPLUNK_ROLE = frozenset([
    'master',
    'searchhead',
    'indexer',
    'forwarder'
])

CHECK_ITEM = frozenset([
    'SPLUNK_STATUS',
    'SSL',
    'LICENSE',
    'CLUSTER',
    'SHCLUSTER'
])

'''_
@author: Curtis Yu
@contact: cuyu@splunk.com
@since: 3/8/16
'''
from checker import Checker, catch_http_exception
from conf_helper import ConfHelper


class ForwarderChecker(Checker):
    def __init__(self, splunk_uri, username='admin', password='changeme'):
        super(ForwarderChecker, self).__init__(splunk_uri, username, password)

    @catch_http_exception
    def check_ssl(self):
        result = super(ForwarderChecker, self).check_ssl()
        helper = ConfHelper(self)
        conf_content = helper.get_conf('outputs')
        result['outputs'] = dict()
        for stanza in conf_content.keys():
            if stanza.startswith('tcpout'):
                result['outputs'][stanza] = conf_content[stanza]
        return result

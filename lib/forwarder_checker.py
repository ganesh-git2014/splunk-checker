'''_
@author: Curtis Yu
@contact: cuyu@splunk.com
@since: 3/8/16
'''
from checker import Checker, catch_http_exception
from conf_helper import ConfHelper


class ForwarderChecker(Checker):

    @catch_http_exception
    def check_ssl(self):
        result = super(ForwarderChecker, self).check_ssl()
        helper = ConfHelper(self.splunk_uri, self._session_key)
        conf_content = helper.get_conf('outputs')
        result['outputs'] = dict()
        for stanza in conf_content.keys():
            if stanza.startswith('tcpout'):
                result['outputs'][stanza] = conf_content[stanza]
        return result

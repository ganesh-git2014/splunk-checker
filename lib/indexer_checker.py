'''_
@author: Curtis Yu
@contact: cuyu@splunk.com
@since: 3/8/16
'''
from checker import Checker, catch_http_exception
from conf_helper import ConfHelper


class IndexerChecker(Checker):
    def __init__(self, splunk_uri, username='admin', password='changeme'):
        super(IndexerChecker, self).__init__(splunk_uri, username, password)

    @catch_http_exception
    def check_ssl(self):
        result = super(IndexerChecker, self).check_ssl()
        helper = ConfHelper(self)
        result['inputs'] = dict()
        result['inputs']['SSL'] = helper.get_stanza('inputs', 'SSL')
        return result

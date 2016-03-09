'''_
@author: Curtis Yu
@contact: cuyu@splunk.com
@since: 3/8/16
'''
from lib.checker import Checker


class MasterChecker(Checker):
    def check_cluster(self):
        result = dict()
        parsed_response = self._request_get('/services/cluster/config')
        result = self._select_dict(parsed_response['entry'][0]['content'],
                                   ['search_factor', 'replication_factor', 'site'])
        return result

'''_
@author: Curtis Yu
@contact: cuyu@splunk.com
@since: 3/8/16
'''
from checker import Checker, catch_http_exception


class MasterChecker(Checker):
    def __init__(self, splunk_uri, username='admin', password='changeme'):
        super(MasterChecker, self).__init__(splunk_uri, username, password)

    @catch_http_exception
    def check_cluster(self):
        parsed_response = self.request_get('/services/cluster/config')
        result = self._select_dict(parsed_response['entry'][0]['content'],
                                   ['search_factor', 'replication_factor', 'site'])

        parsed_response = self.request_get('/services/cluster/master/peers')
        result['peers'] = []
        for entry in parsed_response['entry']:
            result['peers'].append(self._select_dict(entry['content'],
                                                     ['bucket_count', 'bucket_count_by_index', 'active_bundle_id',
                                                      'primary_count', 'search_state_counter', 'label']))
        return result

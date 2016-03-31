'''_
@author: Curtis Yu
@contact: cuyu@splunk.com
@since: 3/8/16
'''
from checker import Checker, catch_http_exception


class SearchHeadChecker(Checker):
    @catch_http_exception
    def check_shcluster(self):
        result = dict()
        parsed_response = self.request_get('/services/shcluster/status')

        result['captain'] = self._select_dict(parsed_response['entry'][0]['content']['captain'],
                                              ['dynamic_captain', 'id', 'mgmt_uri'])

        result['peers'] = parsed_response['entry'][0]['content']['peers']

        return result

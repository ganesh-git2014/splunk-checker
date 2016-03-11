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
        parsed_response = self._request_get('/services/shcluster/member/members')

        parsed_response['entry'][0]['content']

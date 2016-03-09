'''_
@author: Curtis Yu
@contact: cuyu@splunk.com
@since: 3/8/16
'''
import requests
from lib.checker import Checker


class SearchHeadChecker(Checker):

    def check_shcluster(self):
        result = dict()
        try:
            parsed_response = self._request_get('/services/shcluster/member/members')
        except:
            return result
        return True, parsed_response['entry']

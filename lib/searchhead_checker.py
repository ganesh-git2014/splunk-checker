'''_
@author: Curtis Yu
@contact: cuyu@splunk.com
@since: 3/8/16
'''
import requests
from lib.checker import Checker


class SearchHeadChecker(Checker):

    def check_shc_status(self):
        uri = self.splunk_uri + '/services/shcluster/member/members'
        response = requests.get(uri, headers=self._header, params={'output_mode': 'json'}, verify=False)
        if response.status_code != 200:
            return False, response.content
        parsed_response = response.json()
        return True, parsed_response['entry']

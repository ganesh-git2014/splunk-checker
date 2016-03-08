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
        response = requests.get(uri, verify=False)

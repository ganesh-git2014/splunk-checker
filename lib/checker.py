'''_
@author: Curtis Yu
@contact: cuyu@splunk.com
@since: 3/8/16
'''
import requests
import xml.etree.ElementTree as ElementTree

from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


class Checker(object):
    def __init__(self, splunk_uri, username='admin', password='changeme'):
        """
        :param splunk_uri: Specify the splunk as servername:mgmt_port or URI:mgmt_port
        """
        self.splunk_uri = splunk_uri
        self.username = username
        self.password = password
        self._session_key = self._password2sessionkey()

    def _password2sessionkey(self):
        """
        Get a session key from the auth system
        """
        uri = self.splunk_uri + '/services/auth/login'
        body = {'username': self.username, 'password': self.password}
        response = requests.post(uri, data=body, verify=False)

        if response.status_code != 200:
            raise Exception('getSessionKey - unable to login; check credentials')

        root = ElementTree.fromstring(response.content)
        session_key = root.findtext('sessionKey')

        return session_key

    def check_splunk_status(self):
        try:
            self._password2sessionkey()
        except:
            # TODO: check the difference between status down and wrong password
            return False
        else:
            return True

    def check_ssl(self):
        pass

    def check_conf_files(self):
        pass

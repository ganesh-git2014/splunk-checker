'''_
@author: Curtis Yu
@contact: cuyu@splunk.com
@since: 3/8/16
'''
import requests
import time
import xml.etree.ElementTree as ElementTree

from requests.packages.urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


class Checker(object):
    """
    The base class for splunk checkers
    """
    def __init__(self, splunk_uri, username='admin', password='changeme'):
        """
        :param splunk_uri: Specify the splunk as servername:mgmt_port or URI:mgmt_port
        """
        self.splunk_uri = splunk_uri
        self.username = username
        self.password = password
        self._session_key = self._password2sessionkey()
        self._header = {'Authorization': 'Splunk %s' % self._session_key}

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
            # TODO: check the difference between status down and wrong credential
            return False
        else:
            return True

    def check_ssl(self):
        pass

    def check_conf_files(self):
        pass

    def check_license(self):
        """
        :return: URI of license master if the peer is a slave, otherwise return the license info.
        """
        # Fixme: What if it did not enable license master?
        # Assume the splunk is license slave first.
        uri = self.splunk_uri + '/services/licenser/localslave'
        response = requests.get(uri, headers=self._header, params={'output_mode': 'json'}, verify=False)
        assert response.status_code == 200
        parsed_response = response.json()
        # Fixme: What if more than one license master is enabled?
        license_master = parsed_response['entry'][0]['content']['master_uri']
        if license_master != 'self':
            return True, license_master
        else:
            # Assume the splunk is a license master now.
            uri = self.splunk_uri + '/services/licenser/licenses'
            response = requests.get(uri, headers=self._header, params={'output_mode': 'json'}, verify=False)
            parsed_response = response.json()
            flag_expired = True
            flag_exceed = True
            for msg in parsed_response['entry']:
                if msg['content']['expiration_time'] > time.time():
                    flag_expired = False

            uri = self.splunk_uri + '/services/licenser/usage/license_usage'
            response = requests.get(uri, headers=self._header, params={'output_mode': 'json'}, verify=False)
            parsed_response = response.json()
            if parsed_response['entry'][0]['slave_usage_bytes'] < parsed_response['entry'][0]['quota']:
                flag_exceed = False

            if flag_expired:
                return False, 'All licenses are expired.'

            if flag_exceed:
                return False, 'The license usage is exceed quota.'

            return True, None

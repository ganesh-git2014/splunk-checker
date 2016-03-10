'''_
@author: Curtis Yu
@contact: cuyu@splunk.com
@since: 3/8/16
'''
import requests
import xml.etree.ElementTree as ElementTree

from requests.packages.urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


def catch_http_exception(check_method):
    """
    This is a decorator to catch HTTPException for the wrapped function.
    """
    def wrap(*args):
        try:
            result = check_method(*args)
        except HTTPException, e:
            result = e.messages

        return result
    return wrap


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
        # TODO: handle http exception here.
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

    def _request_get(self, endpoint):
        assert endpoint.startswith('/')
        uri = self.splunk_uri + endpoint
        response = requests.get(uri, headers=self._header, params={'output_mode': 'json'}, verify=False)
        parsed_response = response.json()
        if response.status_code == 200:
            return parsed_response
        else:
            raise HTTPException(response)

    def check_splunk_status(self):
        try:
            self._password2sessionkey()
        except:
            # TODO: check the difference between status down and wrong credential
            return 'Down'
        else:
            return 'Up'

    @catch_http_exception
    def check_ssl(self):
        pass

    @catch_http_exception
    def check_conf_files(self):
        pass

    @catch_http_exception
    def check_license(self):
        """
        :return: URI of license master if the peer is a slave, otherwise return the license info.
        """
        # Fixme: What if it did not enable license master?
        result = dict()
        # Assume the splunk is license slave first.
        parsed_response = self._request_get('/services/licenser/localslave')
        # Fixme: What if more than one license master is enabled?
        license_master = parsed_response['entry'][0]['content']['master_uri']
        result['license_master'] = license_master

        # Assume the splunk is a license master now.
        if license_master == 'self':
            result['licenses'] = dict()
            parsed_response = self._request_get('/services/licenser/licenses')

            # The following content are what we want to reserve from the endpoint.
            for msg in parsed_response['entry']:
                if msg['content']['status'] == 'VALID':
                    result['licenses'][msg['content']['guid']] = \
                        self._select_dict(msg['content'], ['expiration_time', 'label', 'quota', 'type'])

            # Acquire the total license usage
            parsed_response = self._request_get('/services/licenser/usage/license_usage')
            result['usage'] = self._select_dict(parsed_response['entry'][0]['content'], ['quota', 'slaves_usage_bytes'])

        return result

    @staticmethod
    def _select_dict(dict_obj, select_keys):
        """
        Reserve the key value pairs using the given key list, and filter others.
        E.g. _select_dict({'a': 1, 'b': 2, 'c': 3}, ['b', 'c'])
        will return {'b': 2, 'c': 3}
        """
        return {key: dict_obj[key] for key in select_keys}


class HTTPException(Exception):
    def __init__(self, response):
        """
        :param messages: is a list of messages.
        """
        self.messages = response.json()
        # This key value is used for ClusterChecker._check_http_exception to identify weather
        # the check result is a http exception or a normal result.
        self.messages['is_http_exception'] = True
        self.messages['status_code'] = response.status_code
        self.messages['url'] = response.url

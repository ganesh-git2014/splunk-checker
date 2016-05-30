'''_
@author: Curtis Yu
@contact: cuyu@splunk.com
@since: 3/8/16
'''
import requests
import xml.etree.ElementTree as ElementTree

# from requests.packages.urllib3.exceptions import InsecureRequestWarning
#
# requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
from requests.exceptions import Timeout

from conf_helper import ConfHelper
from errors import HTTPException
from logger import Logging


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


from json import JSONEncoder


def _default(self, obj):
    return str(obj)


# Fixme: hack the JSONEncoder default method to avoid raising TypeError.
JSONEncoder.default = _default


class ExtensibleEntry(object):
    """
    Use this class to solve `index out of range` issue for parsed_response of request.
    With this class, you can acquire the result from a empty list like below:
        >>> entry = ExtensibleEntry([])
        >>> print entry[0]['content']['label']
        >>> []
    """

    def __init__(self, entries):
        """
        :param entries: a list object.
        """
        self._entries = entries

    def __getitem__(self, item):
        if item < len(self._entries):
            return self._entries[item]
        else:
            return ExtensibleEntry([])

    def __str__(self):
        return str(self._entries)

    def __iter__(self):
        return self._entries.__iter__()


class Checker(Logging):
    """
    The base class for splunk checkers
    """

    def __init__(self, splunk_uri, username='admin', password='changeme'):
        """
        :param splunk_uri: Specify the splunk as servername:mgmt_port or URI:mgmt_port
        """
        super(Checker, self).__init__()
        self.splunk_uri = splunk_uri
        self.username = username
        self.password = password
        try:
            self._session_key = self._password2sessionkey()
        except:
            self.logger.warning('Cannot get session key from `{0}`'.format(splunk_uri))
            self._session_key = None
        self._header = {'Authorization': 'Splunk %s' % self._session_key}
        # Init requests.Session here so that we can reuse the connections.
        self._session = requests.Session()

    def _password2sessionkey(self):
        """
        Get a session key from the auth system
        """
        uri = self.splunk_uri + '/services/auth/login'
        body = {'username': self.username, 'password': self.password}
        response = requests.post(uri, data=body, verify=False, timeout=30)

        if response.status_code != 200:
            raise Exception('getSessionKey - unable to login; check credentials')

        root = ElementTree.fromstring(response.content)
        session_key = root.findtext('sessionKey')

        return session_key

    def request_get(self, endpoint):
        if self._session_key is None:
            raise HTTPException('Skip')
        assert endpoint.startswith('/')
        uri = self.splunk_uri + endpoint
        try:
            response = self._session.get(uri, headers=self._header, params={'output_mode': 'json'}, verify=False,
                                         timeout=30)
        except Timeout, e:
            self.logger.error('HTTP read timeout at `{0}`'.format(self.splunk_uri + '/' + endpoint))
            raise HTTPException('ReadTimeout', e)
        parsed_response = response.json()
        if response.status_code == 200:
            # Replace the entry list to extensible one.
            parsed_response['entry'] = ExtensibleEntry(parsed_response['entry'])
            return parsed_response
        else:
            self.logger.error(
                'HTTP status code is {0} at `{1}`'.format(response.status_code, self.splunk_uri + '/' + endpoint))
            raise HTTPException('Response', response)

    def check_splunk_status(self):
        result = dict()
        if not self._session_key:
            # TODO: check the difference between status down and wrong credential
            result['status'] = 'Down'
            result['server_info'] = None
        else:
            result['status'] = 'Up'
            try:
                parsed_response = self.request_get('/services/server/info')
            except:
                result['server_info'] = None
            else:
                result['server_info'] = self._select_dict(parsed_response['entry'][0]['content'],
                                                          ['build', 'guid', 'numberOfVirtualCores', 'physicalMemoryMB',
                                                           'version'])
        return result

    @catch_http_exception
    def check_ssl(self):
        result = dict()
        helper = ConfHelper(self)
        result['server'] = dict()
        result['server']['sslConfig'] = helper.get_stanza('server', 'sslConfig')
        return result

    @catch_http_exception
    def check_conf_files(self):
        """
        Only check some critical conf files.
        """
        pass

    @catch_http_exception
    def check_resource_usage(self):
        result = dict()
        parsed_response = self.request_get('/services/server/status/partitions-space')
        result['disk_space'] = self._select_dict(parsed_response['entry'][0]['content'], ['available', 'capacity'])

        parsed_response = self.request_get('/services/server/status/resource-usage//hostwide')
        result['host_resource_usage'] = self._select_dict(parsed_response['entry'][0]['content'],
                                                          ['cpu_count', 'cpu_idle_pct', 'mem', 'mem_used'])

        parsed_response = self.request_get('/services/server/status/resource-usage//iostats')
        result['iostats'] = self._select_dict(parsed_response['entry'][0]['content'],
                                              ['reads_kb_ps', 'reads_ps', 'writes_kb_ps', 'writes_ps'])

        parsed_response = self.request_get('/services/server/status/resource-usage//splunk-processes')
        result['process_resource_usage'] = []
        for entry in parsed_response['entry']:
            result['process_resource_usage'].append(
                self._select_dict(entry['content'], ['mem_used', 'process_type']))

        return result

    @catch_http_exception
    def check_license(self):
        """
        :return: URI of license master if the peer is a slave, otherwise return the license info.
        """
        # Fixme: What if it did not enable license master?
        result = dict()
        # Assume the splunk is license slave first.
        parsed_response = self.request_get('/services/licenser/localslave')
        # Fixme: What if more than one license master is enabled?
        license_master = parsed_response['entry'][0]['content']['master_uri']
        result['license_master'] = license_master

        # Assume the splunk is a license master now.
        if license_master == 'self':
            result['licenses'] = dict()
            parsed_response = self.request_get('/services/licenser/licenses')

            # The following content are what we want to reserve from the endpoint.
            for msg in parsed_response['entry']:
                if msg['content']['status'] == 'VALID':
                    result['licenses'][msg['content']['guid']] = \
                        self._select_dict(msg['content'], ['expiration_time', 'label', 'quota', 'type'])

            # Acquire the total license usage
            parsed_response = self.request_get('/services/licenser/usage/license_usage')
            result['usage'] = self._select_dict(parsed_response['entry'][0]['content'], ['quota', 'slaves_usage_bytes'])

        return result

    def _select_dict(self, dict_obj, select_keys):
        """
        Reserve the key value pairs using the given key list, and filter others.
        E.g. _select_dict({'a': 1, 'b': 2, 'c': 3}, ['b', 'c'])
        will return {'b': 2, 'c': 3}
        """
        try:
            return {key: dict_obj[key] for key in select_keys}
        except IndexError:
            self.logger.error("Cannot select keys from dict @{0}".format(self.splunk_uri))


if __name__ == '__main__':
    entries = [{'content': {'label': 1}}]
    result = ExtensibleEntry(entries)
    print result[1]['content']
    for i in result[1]['content']:
        print i
    import json

    print json.dumps({'a': result[1]})

'''_
@author: Curtis Yu
@contact: cuyu@splunk.com
@since: 3/29/16
'''

import requests

from errors import HTTPException


class ConfHelper(object):
    """
    This class is used to acquire conf settings from '/services/configs/conf-{confname}'.
    """

    def __init__(self, splunk_uri, session_key):
        self._splunk_uri = splunk_uri
        self._session_key = session_key
        self._header = {'Authorization': 'Splunk %s' % self._session_key}

    def get_conf(self, conf_name):
        """
        :param conf_name:
        :return: a dict where each sub-dict is a stanza
        """
        if not self._session_key:
            raise HTTPException('SKIP')

        endpoint = '{splunk_uri}/services/configs/conf-{conf_name}?output_mode=json&count=-1'.format(
            splunk_uri=self._splunk_uri, conf_name=conf_name)
        r = requests.get(endpoint, headers=self._header, verify=False)
        if r.status_code != 200:
            raise HTTPException(r)

        parsed_response = r.json()
        conf_content = dict()
        for stanza_info in parsed_response['entry']:
            conf_content[stanza_info['name']] = stanza_info['content']
        return conf_content

    def get_stanza(self, conf_name, stanza):
        if not self._session_key:
            raise HTTPException('SKIP')

        endpoint = '{splunk_uri}/services/configs/conf-{conf_name}/{stanza}?output_mode=json&count=-1'.format(
            splunk_uri=self._splunk_uri, conf_name=conf_name, stanza=stanza)
        r = requests.get(endpoint, headers=self._header, verify=False)
        if r.status_code != 200:
            raise HTTPException(r)

        parsed_response = r.json()
        return parsed_response['entry'][0]['content']


if __name__ == '__main__':
    from lib.checker import Checker

    splunk_uri = 'https://systest-auto-idx2:1901'
    checker = Checker('https://systest-auto-idx2:1901', 'admin', 'changed')
    helper = ConfHelper(splunk_uri, checker._session_key)
    helper.get_conf('outputs')
    helper.get_stanza('outputs', 'tcpout')

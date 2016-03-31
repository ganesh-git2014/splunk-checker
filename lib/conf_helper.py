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

    def __init__(self, checker):
        self._checker = checker

    def get_conf(self, conf_name):
        """
        :param conf_name:
        :return: a dict where each sub-dict is a stanza
        """
        endpoint = '/services/configs/conf-{conf_name}?count=-1'.format(conf_name=conf_name)
        parsed_response = self._checker.request_get(endpoint)

        conf_content = dict()
        for stanza_info in parsed_response['entry']:
            conf_content[stanza_info['name']] = stanza_info['content']
        return conf_content

    def get_stanza(self, conf_name, stanza):
        endpoint = '/services/configs/conf-{conf_name}/{stanza}?count=-1'.format(
            conf_name=conf_name, stanza=stanza)
        parsed_response = self._checker.request_get(endpoint)

        return parsed_response['entry'][0]['content']


if __name__ == '__main__':
    from lib.checker import Checker

    splunk_uri = 'https://systest-auto-idx2:1901'
    checker = Checker('https://systest-auto-idx2:1901', 'admin', 'changed')
    helper = ConfHelper(checker)
    helper.get_conf('outputs')
    helper.get_stanza('outputs', 'tcpout')

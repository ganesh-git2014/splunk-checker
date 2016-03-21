'''_
@author: Curtis Yu
@contact: cuyu@splunk.com
@since: 12/29/15
'''
import json
import os
import requests


class KVStoreHelper(object):
    def __init__(self, session_key):
        self._session_key = session_key
        self._header = {'Authorization': 'Splunk %s' % self._session_key}
        self._json_header = {'Authorization': 'Splunk %s' % self._session_key, 'Content-Type': 'application/json'}

    def update_cluster_info(self, endpoint, cluster_info):
        content = self._find_kvpair_by_id(endpoint, cluster_info['id'])
        if content:
            _key = content['_key']
            new_endpoint = os.path.join(endpoint, _key)
            content.pop('_key')
            content.pop('_user')
            splunk_uri = cluster_info['cluster'].keys()[0]
            content['cluster'][splunk_uri] = cluster_info['cluster'][splunk_uri]
            data = json.dumps(content)
        else:
            new_endpoint = endpoint
            data = json.dumps(cluster_info)
        r = requests.post(new_endpoint, data=data, headers=self._json_header, verify=False)
        assert r.status_code in (201, 200)

    def get_cluster_info(self, endpoint):
        """
        Return the value according to the key.
        Return None if not found.
        """
        r = requests.get(endpoint, headers=self._header, verify=False)
        assert r.status_code == 200
        parsed_response = json.loads(r.content)
        for content in parsed_response:
            content.pop('_key')
            content.pop('_user')
        return parsed_response

    def _find_kvpair_by_id(self, endpoint, id):
        """
        Read and check the value in kvstore is single value.
        Return empty dict if not found.
        """
        r = requests.get(endpoint, headers=self._header, verify=False)
        assert r.status_code == 200
        parsed_response = json.loads(r.content)
        _key = ''
        content = {}
        for kvpair in parsed_response:
            if id == kvpair['id']:
                assert _key == '', 'multi values correspond to the specific cluster id: {key}'.format(key=id)
                _key = kvpair['_key']
                content = kvpair
        return content

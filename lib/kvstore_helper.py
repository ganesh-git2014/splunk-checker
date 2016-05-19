import json
import os
import requests


class KVStoreHelper(object):
    def __init__(self, session_key):
        self._session_key = session_key
        self._header = {'Authorization': 'Splunk %s' % self._session_key}
        self._json_header = {'Authorization': 'Splunk %s' % self._session_key, 'Content-Type': 'application/json'}

    def update_cluster_info(self, endpoint, cluster_info):
        content = self._find_kvpair_by_id(endpoint, cluster_info['cluster_id'])
        if content:
            _key = content['_key']
            new_endpoint = os.path.join(endpoint, _key)
            content.pop('_key')
            content.pop('_user')
            peer_info = cluster_info['peers'][0]
            splunk_uri = peer_info['splunk_uri']
            for i in range(len(content['peers'])):
                if content['peers'][i]['splunk_uri'] == splunk_uri:
                    content['peers'][i] = peer_info
                    break
            else:
                content['peers'].append(peer_info)
            data = json.dumps(content)
        else:
            new_endpoint = endpoint
            data = json.dumps(cluster_info)
        data = data.replace('.', "[dot]")
        r = requests.post(new_endpoint, data=data, headers=self._json_header, verify=False)
        assert r.status_code in (201, 200)

    def _get_info_from_endpoint(self, endpoint):
        r = requests.get(endpoint, headers=self._header, verify=False)
        assert r.status_code == 200
        response_content = r.content.replace("[dot]", ".")
        parsed_response = json.loads(response_content)
        for content in parsed_response:
            content.pop('_key')
            content.pop('_user')
        return parsed_response

    def get_cluster_info(self, endpoint):
        """
        Return the value according to the key.
        Return None if not found.
        """
        return self._get_info_from_endpoint(endpoint)

    def _find_kvpair_by_id(self, endpoint, id):
        """
        Read and check the value in kvstore is single value.
        Return empty dict if not found.
        """
        r = requests.get(endpoint, headers=self._header, verify=False)
        assert r.status_code == 200
        parsed_response = json.loads(r.content.replace("[dot]", "."))
        _key = ''
        content = {}
        for kvpair in parsed_response:
            if id == kvpair['cluster_id']:
                assert _key == '', 'multi values correspond to the specific cluster id: {key}'.format(key=id)
                _key = kvpair['_key']
                content = kvpair
        return content

    # TODO: delete the progress item from kvstore when all progresses are finished.
    def update_upgrade_progress(self, endpoint, progress):
        """
        :param endpoint: kvstore endpoint.
        :param progress: a {Progress} object.
        :return: None
        """
        content = self._find_kvpair_by_id(endpoint, progress.cluster_id)
        if content:
            _key = content['_key']
            new_endpoint = os.path.join(endpoint, _key)
            content.pop('_key')
            content.pop('_user')
            content['name'] = progress.name
            content['progress'] = progress.progress
            data = json.dumps(content)
        else:
            new_endpoint = endpoint
            data = progress.json()
        # Replace the "." with "[dot]", will replace back when getting from kvstore.
        data = data.replace('.', "[dot]")
        r = requests.post(new_endpoint, data=data, headers=self._json_header, verify=False)
        assert r.status_code in (201, 200)

    def get_upgrade_progress(self, endpoint):
        return self._get_info_from_endpoint(endpoint)

    def delete_upgrade_progress(self, endpoint, progress):
        content = self._find_kvpair_by_id(endpoint, progress.cluster_id)
        if not content:
            return
        _key = content['_key']
        delete_endpoint = os.path.join(endpoint, _key)
        r = requests.delete(delete_endpoint, headers=self._json_header, verify=False)
        assert r.status_code in (201, 200)

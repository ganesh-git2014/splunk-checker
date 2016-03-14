'''_
@author: Curtis Yu
@contact: cuyu@splunk.com
@since: 3/8/16
'''
import time
import json
from constant import SPLUNK_ROLE, CHECK_ITEM
from forwarder_checker import ForwarderChecker
from indexer_checker import IndexerChecker
from master_checker import MasterChecker
from searchhead_checker import SearchHeadChecker


class ClusterChecker(object):
    def __init__(self, cluster_id):
        # TODO: Consider multi-site cluster.
        # (May: 1. Create multi ClusterChecker instances, and add a multi-site check from outside;
        #       2. Handle the multi-site here.)
        self.master_checker = None
        self.searchhead_checkers = []
        self.indexer_checkers = []
        self.forwarder_checkers = []
        self.search_factor = None
        self.replication_factor = None
        self.enable_ssl = False
        self.enable_shc = True
        self.cluster_id = cluster_id

    @property
    def all_checkers(self):
        return self.searchhead_checkers + self.indexer_checkers + self.forwarder_checkers + [self.master_checker]

    def set_search_factor(self, search_factor):
        self.search_factor = search_factor

    def set_replication_factor(self, replication_factor):
        self.replication_factor = replication_factor

    def add_peer(self, splunk_uri, role, username='admin', password='changeme'):
        role = role.lower()
        assert role in SPLUNK_ROLE

        if role == 'master':
            self.master_checker = MasterChecker(splunk_uri, username, password)
        elif role == 'searchhead':
            self.searchhead_checkers.append(SearchHeadChecker(splunk_uri, username, password))
        elif role == 'indexer':
            self.indexer_checkers.append(IndexerChecker(splunk_uri, username, password))
        elif role == 'forwarder':
            self.forwarder_checkers.append(ForwarderChecker(splunk_uri, username, password))

    def check_all_items(self):
        # TODO: can check the selected items.
        """
        Check all the items for each peer in the cluster.
        :return: A dict of each item and corresponding result.
        """
        check_result = dict()
        warning_msg = dict()

        for item in CHECK_ITEM:
            check_result[item] = self._map_check_method(item)()
            exception_msg = self._check_http_exception(check_result[item])
            if exception_msg:
                warning_msg[item] = exception_msg
            else:
                warning_msg[item] = self._map_generate_message_method(item)(check_result[item])

        return check_result, warning_msg

    def transform_event(self, result):
        """
        Transform result to string.
        """
        print_msg = ""
        print_msg += 'cluster_id={0} '.format(self.cluster_id)
        print_msg += 'info={0}'.format(json.dumps(result))
        return print_msg

    def _map_check_method(self, item):
        assert item in CHECK_ITEM
        method_map = {'SPLUNK_STATUS': self.check_splunk_status,
                      'SSL': self.check_ssl,
                      'LICENSE': self.check_license,
                      'CLUSTER': self.check_cluster,
                      'SHCLUSTER': self.check_shcluster}
        return method_map[item]

    def _map_generate_message_method(self, item):
        assert item in CHECK_ITEM
        method_map = {'SPLUNK_STATUS': self._generate_splunk_status_message,
                      'SSL': self._generate_ssl_message,
                      'LICENSE': self._generate_license_message,
                      'CLUSTER': self._generate_cluster_message,
                      'SHCLUSTER': self._generate_shcluster_message}
        return method_map[item]

    def check_splunk_status(self):
        check_result = dict()
        for checker in self.all_checkers:
            check_result[checker.splunk_uri] = checker.check_splunk_status()

        return check_result

    def check_license(self):
        check_result = dict()
        for checker in self.all_checkers:
            check_result[checker.splunk_uri] = checker.check_license()

        return check_result

    def check_cluster(self):
        check_result = dict()
        check_result[self.master_checker.splunk_uri] = self.master_checker.check_cluster()

        return check_result

    def check_ssl(self):
        pass

    def check_shcluster(self):
        check_result = dict()
        for checker in self.searchhead_checkers:
            check_result[checker.splunk_uri] = checker.check_shcluster()

        return check_result

    def _generate_splunk_status_message(self, check_result):
        """
        Transform the concrete result into a rough True or False.
        The return result contains the warning messages(should be a list), if the message list is empty, that means the
        check item is [OK], otherwise it has some problems.
        """
        msg_list = []
        for uri in check_result.keys():
            if check_result[uri] == 'Down':
                msg_list.append('[{0}] is down!'.format(uri))
        return msg_list

    def _generate_license_message(self, check_result):
        # Start license check.
        msg_list = []
        all_peer_uri = []
        for checker in self.all_checkers:
            all_peer_uri.append(checker.splunk_uri)
        for uri in check_result.keys():
            if check_result[uri]['license_master'] != 'self':
                # Check if the license master is one peer of the cluster.
                if check_result[uri]['license_master'] not in all_peer_uri:
                    msg_list.append('The license master of [{0}] is not in the cluster'.format(uri))
            else:
                # Check if all licenses are expired.
                now = time.time()
                # Set the threshold to 1 day.
                th_time = 3600 * 24
                for license in check_result[uri]['licenses'].values():
                    if license['expiration_time'] - int(now) > th_time:
                        break
                else:
                    msg_list.append('All the licenses have expired.(Or will expire soon.)')
                # Check if the license usage is hitting the limit.
                # Set the threshold to about 1 GB
                th_quota = 100000
                if check_result[uri]['usage']['quota'] - check_result[uri]['usage']['slaves_usage_bytes'] < th_quota:
                    msg_list.append('The usage of the license is hitting the quota.')

        return msg_list

    def _generate_cluster_message(self, check_result):
        msg_list = []
        # Check replication factor
        if check_result[self.master_checker.splunk_uri]['replication_factor'] != self.replication_factor:
            msg_list.append('Replication factor [{0}] is different from defined [{1}].'.format(
                check_result[self.master_checker.splunk_uri]['replication_factor'],
                self.replication_factor))
        # Check search factor
        if check_result[self.master_checker.splunk_uri]['search_factor'] != self.search_factor:
            msg_list.append('Search factor [{0}] is different from defined [{1}].'.format(
                check_result[self.master_checker.splunk_uri]['search_factor'], self.search_factor))

        return msg_list

    def _generate_ssl_message(self):
        pass

    def _generate_shcluster_message(self):
        pass

    def _check_http_exception(self, check_result):
        """
        Check if there is http exception messages among the check result.
        """
        for result in check_result.values():
            # Fixme: The check method here is not very good.
            if 'is_http_exception' in result and result['is_http_exception'] is True:
                warning_messages = []
                for msg in result['messages']:
                    warning_messages.append(
                        'Http exception occurred at [{url}], warning messages: [{msg}]'.format(url=result['url'],
                                                                                               msg=msg['text']))
                return warning_messages
        else:
            return None


if __name__ == '__main__':
    checker1 = ClusterChecker('env1')
    checker1.add_peer('https://systest-auto-master:1901', 'master', 'admin', 'changed')
    checker1.add_peer('https://systest-auto-sh1:1901', 'searchhead', 'admin', 'changed')
    checker1.add_peer('https://systest-auto-idx1:1901', 'indexer', 'admin', 'changed')
    checker1.add_peer('https://systest-auto-fwd1:1901', 'forwarder', 'admin', 'changed')

    result, warning_msg = checker1.check_all_items()

    print result

'''_
@author: Curtis Yu
@contact: cuyu@splunk.com
@since: 3/8/16
'''
import time
import json
from constant import SPLUNK_ROLE, CHECK_ITEM, Severity
from forwarder_checker import ForwarderChecker
from indexer_checker import IndexerChecker
from master_checker import MasterChecker
from searchhead_checker import SearchHeadChecker


class ClusterChecker(object):
    def __init__(self, cluster_id, enable_shcluster=True, enable_cluster=True, search_factor=1, replication_factor=1,
                 enable_ssl=False):
        # TODO: Consider multi-site cluster.
        # (May: 1. Create multi ClusterChecker instances, and add a multi-site check from outside;
        #       2. Handle the multi-site here.)
        self.master_checker = None
        self.searchhead_checkers = []
        self.indexer_checkers = []
        self.forwarder_checkers = []
        self.search_factor = search_factor
        self.replication_factor = replication_factor
        self.enable_cluster = enable_cluster
        self.enable_ssl = enable_ssl
        self.enable_shcluster = enable_shcluster
        self.cluster_id = cluster_id
        # Set the check items at the end of init function.
        self.check_points = self._set_check_points()

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

    def _set_check_points(self):
        check_items = list(CHECK_ITEM)
        if not self.enable_cluster:
            check_items.remove('CLUSTER')
        if not self.enable_shcluster:
            check_items.remove('SHCLUSTER')
        if not self.enable_ssl:
            check_items.remove('SSL')
        return check_items

    def check_all_items(self, return_event=False):
        # TODO: can check the selected items.
        """
        Check all the items for each peer in the cluster.
        :return: Two dict of each item and corresponding result. If return_event=True, will transform the results into
        two lists of event string to return.
        """
        check_results = dict()
        warning_msg = dict()

        for item in self.check_points:
            check_results[item] = self._map_check_method(item)()
            exception_msg = self._check_http_exception(check_results[item])
            if exception_msg:
                warning_msg[item] = exception_msg
            else:
                warning_msg[item] = self._map_generate_message_method(item)(check_results[item])

        if return_event:
            return self.transform_event(check_results, warning_msg)
        else:
            return check_results, warning_msg

    def transform_event(self, check_results, warning_msg):
        """
        Transform check result to event string.
        """
        check_results_events = dict()
        warning_msg_events = dict()
        for item in self.check_points:
            event = dict()
            event['cluster_id'] = self.cluster_id
            event['info'.format(item)] = check_results[item]
            check_results_events[item] = json.dumps(event)
            event = dict()
            event['cluster_id'] = self.cluster_id
            event['info'.format(item)] = warning_msg[item]
            warning_msg_events[item] = json.dumps(event)
        return check_results_events, warning_msg_events

    def _map_check_method(self, item):
        assert item in CHECK_ITEM
        method_map = {'SPLUNK_STATUS': self.check_splunk_status,
                      'SSL': self.check_ssl,
                      'LICENSE': self.check_license,
                      'CLUSTER': self.check_cluster,
                      'SHCLUSTER': self.check_shcluster,
                      'DISK_SPACE': self.check_disk_space}
        return method_map[item]

    def _map_generate_message_method(self, item):
        assert item in CHECK_ITEM
        method_map = {'SPLUNK_STATUS': self._generate_splunk_status_message,
                      'SSL': self._generate_ssl_message,
                      'LICENSE': self._generate_license_message,
                      'CLUSTER': self._generate_cluster_message,
                      'SHCLUSTER': self._generate_shcluster_message,
                      'DISK_SPACE': self._generate_disk_space_message}
        return method_map[item]

    def check_splunk_status(self):
        check_results = []
        for checker in self.all_checkers:
            tmp_result = checker.check_splunk_status()
            tmp_result['splunk_uri'] = checker.splunk_uri
            check_results.append(tmp_result)

        return check_results

    def check_disk_space(self):
        check_results = []
        for checker in self.all_checkers:
            tmp_result = checker.check_disk_space()
            tmp_result['splunk_uri'] = checker.splunk_uri
            check_results.append(tmp_result)

        return check_results

    def _generate_disk_space_message(self, check_results):
        msg_list = []
        th_space = 4000
        for result in check_results:
            if float(result['disk_space']['available']) < th_space:
                self._add_warning_message(msg_list,
                                          'The disk space is not enough on [{0}]! Only {1}Mb avaliable.'.format(
                                              result['splunk_uri'], result['disk_space']['available']), Severity.SEVERE)
        return msg_list

    def check_license(self):
        check_results = []
        for checker in self.all_checkers:
            tmp_result = checker.check_license()
            tmp_result['splunk_uri'] = checker.splunk_uri
            check_results.append(tmp_result)

        return check_results

    def check_cluster(self):
        check_results = []
        tmp_result = self.master_checker.check_cluster()
        tmp_result['splunk_uri'] = self.master_checker.splunk_uri
        check_results.append(tmp_result)

        return check_results

    def check_ssl(self):
        pass

    def check_shcluster(self):
        check_results = []
        for checker in self.searchhead_checkers:
            tmp_result = checker.check_shcluster()
            tmp_result['splunk_uri'] = checker.splunk_uri
            check_results.append(tmp_result)

        return check_results

    def _generate_splunk_status_message(self, check_results):
        """
        Transform the concrete result into a rough True or False.
        The return result contains the warning messages(should be a list), if the message list is empty, that means the
        check item is [OK], otherwise it has some problems.
        """
        msg_list = []
        for result in check_results:
            if result['status'] == 'Down':
                self._add_warning_message(msg_list, '[{0}] is down!'.format(result['splunk_uri']), Severity.SEVERE)
        return msg_list

    def _generate_license_message(self, check_results):
        # Start license check.
        msg_list = []
        all_peer_uri = []
        for checker in self.all_checkers:
            all_peer_uri.append(checker.splunk_uri)
        for result in check_results:
            if result['license_master'] != 'self':
                # Check if the license master is one peer of the cluster.
                if result['license_master'] not in all_peer_uri:
                    self._add_warning_message(msg_list, 'The license master of [{0}] is not in the cluster'.format(
                        result['splunk_uri']), Severity.ELEVATED)
            else:
                # Check if all licenses are expired.
                now = time.time()
                # Set the threshold to 1 day.
                th_time = 3600 * 24
                for license in result['licenses'].values():
                    if license['expiration_time'] - int(now) > th_time:
                        break
                else:
                    self._add_warning_message(msg_list,
                                              'All the licenses have expired(Or will expire soon) on [{0}]'.format(
                                                  result['splunk_uri']), Severity.SEVERE)
                # Check if the license usage is hitting the limit.
                # Set the threshold to about 1 GB
                th_quota = 100000
                if result['usage']['quota'] - result['usage']['slaves_usage_bytes'] < th_quota:
                    self._add_warning_message(msg_list,
                                              'The usage of the license is hitting the quota on [{0}].'.format(
                                                  result['splunk_uri']), Severity.ELEVATED)

        return msg_list

    def _generate_cluster_message(self, check_results):
        msg_list = []
        # Check replication factor
        # todo: support multi-site cluster
        if check_results[0]['replication_factor'] != self.replication_factor:
            self._add_warning_message(msg_list, 'Replication factor [{0}] is different from defined [{1}].'.format(
                check_results[0]['replication_factor'],
                self.replication_factor), Severity.SEVERE)
        # Check search factor
        if check_results[0]['search_factor'] != self.search_factor:
            self._add_warning_message(msg_list, 'Search factor [{0}] is different from defined [{1}].'.format(
                check_results[0]['search_factor'], self.search_factor), Severity.SEVERE)

        return msg_list

    def _generate_ssl_message(self):
        pass

    def _generate_shcluster_message(self, check_results):
        msg_list = []
        if len(check_results) < 3:
            self._add_warning_message(msg_list,
                                      'The check is skipped due to: The number of search head in SHC should be more than 3.',
                                      Severity.UNKNOWN)
            return msg_list
        # Check the captain id is the same from all search heads(so that in the same bundle)
        captain_id = check_results[0]['captain']['id']
        for result in check_results:
            if result['captain']['id'] != captain_id:
                self._add_warning_message(msg_list, 'The captain id is not consistent!', Severity.SEVERE)
                break

        return msg_list

    def _check_http_exception(self, check_results):
        """
        Check if there is http exception messages among the check result.
        """
        for result in check_results:
            # Fixme: The check method here is not very good.
            if 'is_http_exception' in result and result['is_http_exception'] is True:
                warning_messages = []
                for msg in result['messages']:
                    self._add_warning_message(warning_messages,
                                              'Http exception occurred at [{url}], warning messages: [{msg}]'.format(
                                                  url=result['url'], msg=msg['text']), Severity.UNKNOWN)
                return warning_messages
        else:
            return None

    def _add_warning_message(self, message_list, message, severity):
        """
        Add the warning msg to the msg list.
        :param message_list: the msg list
        :param message: the warning msg
        :param severity: the severity of the warning msg
        :return: None
        """
        message_list.append({'message': message, 'severity': severity})

    def _find_result_by_splunk_uri(self, result_list, splunk_uri):
        for result in result_list:
            if result['splunk_uri'] == splunk_uri:
                return result


if __name__ == '__main__':
    checker1 = ClusterChecker('env1')
    checker1.add_peer('https://systest-auto-master:1901', 'master', 'admin', 'changed')
    checker1.add_peer('https://systest-auto-sh1:1901', 'searchhead', 'admin', 'changed')
    checker1.add_peer('https://systest-auto-sh2:1901', 'searchhead', 'admin', 'changed')
    checker1.add_peer('https://systest-auto-idx1:1901', 'indexer', 'admin', 'changed')
    checker1.add_peer('https://systest-auto-fwd1:1901', 'forwarder', 'admin', 'changed')

    check_result, warning_msg = checker1.check_all_items(False)

    print check_result

'''_
@author: Curtis Yu
@contact: cuyu@splunk.com
@since: 3/8/16
'''
import time
from lib.constant import SPLUNK_ROLE, CheckItem
from lib.forwarder_checker import ForwarderChecker
from lib.indexer_checker import IndexerChecker
from lib.master_checker import MasterChecker
from lib.searchhead_checker import SearchHeadChecker


class ClusterChecker(object):
    def __init__(self):
        self.master_checker = None
        self.searchhead_checkers = []
        self.indexer_checkers = []
        self.forwarder_checkers = []
        self.search_factor = None
        self.replicate_factor = None
        self.enable_ssl = False

    @property
    def all_checkers(self):
        return self.searchhead_checkers + self.indexer_checkers + self.forwarder_checkers + [self.master_checker]

    def set_search_factor(self, search_factor):
        self.search_factor = search_factor

    def set_replicate_factor(self, replicate_factor):
        self.replicate_factor = replicate_factor

    def add_peer(self, splunk_uri, role, username='admin', password='changeme'):
        role = role.lower()
        assert role in SPLUNK_ROLE

        if role == 'master':
            assert self.master_checker is None
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
        check_result[CheckItem.SPLUNK_STATUS] = self.check_splunk_status()
        check_result[CheckItem.SSL] = self.check_ssl
        check_result[CheckItem.LICENSE] = self.check_license()
        check_result[CheckItem.SEARCH_FACTOR] = self.check_search_factor()
        check_result[CheckItem.REPLICATE_FACTOR] = self.check_replicate_factor()
        check_result[CheckItem.SHC_STATUS] = self.searchhead_checkers[0].check_shc_status()

        warning_msg = self._generate_warning_messages(check_result)

        return check_result, warning_msg

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

    def check_search_factor(self):
        pass

    def check_replicate_factor(self):
        pass

    def check_ssl(self):
        pass

    def _generate_warning_messages(self, check_result):
        """
        Transform the concrete result into a rough True or False.
        The return result contains the warning messages(should be a list), if the message list is empty, that means the
        check item is [OK], otherwise it has some problems.
        """
        simple_result = dict()
        for item in check_result.keys():
            if item == CheckItem.SPLUNK_STATUS:
                msg_list = []
                for uri in check_result[item].keys():
                    if check_result[item][uri] == 'Down':
                        msg_list.append(uri + 'is down!')

                simple_result[item] = msg_list

            elif item == CheckItem.LICENSE:
                msg_list = []
                all_peer_uri = []
                for checker in self.all_checkers:
                    all_peer_uri.append(checker.splunk_uri)
                for uri in check_result[item].keys():
                    if check_result[item][uri]['license_master'] != 'self':
                        # Check if the license master is one peer of the cluster.
                        if check_result[item][uri]['license_master'] not in all_peer_uri:
                            msg_list.append('The license master of [{0}] is not in the cluster'.format(uri))
                    else:
                        # Check if all licenses are expired.
                        now = time.time()
                        # Set the threshold to 1 day.
                        th_time = 3600 * 24
                        for license in check_result[item][uri]['licenses'].values():
                            if license['expiration_time'] - int(now) > th_time:
                                break
                        else:
                            msg_list.append('All the licenses have expired.(Or will expire soon.)')

                        # Check if the license usage is hitting the limit.
                        # Set the threshold to about 1 GB
                        th_quota = 100000
                        if check_result[item][uri]['usage']['quota'] - check_result[item][uri]['usage'][
                            'slaves_usage_bytes'] < th_quota:
                            msg_list.append('The usage of the license is hitting the quota.')

                simple_result[item] = msg_list

            elif item == CheckItem.SEARCH_FACTOR:
                msg_list = []

        return simple_result


if __name__ == '__main__':
    checker1 = ClusterChecker()
    checker1.add_peer('https://systest-auto-master:1901', 'master', 'admin', 'changed')
    checker1.add_peer('https://systest-auto-sh1:1901', 'searchhead', 'admin', 'changed')
    checker1.add_peer('https://systest-auto-idx1:1901', 'indexer', 'admin', 'changed')
    checker1.add_peer('https://systest-auto-fwd1:1901', 'forwarder', 'admin', 'changed')

    result = checker1.check_all_items()
    # result = checker1.check_license()

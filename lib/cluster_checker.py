'''_
@author: Curtis Yu
@contact: cuyu@splunk.com
@since: 3/8/16
'''
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
        """
        Check all the items for each peer in the cluster.
        :return: A dict of each item and corresponding result.
        """
        check_result = dict()
        check_result['splunk_status'] = self.check_splunk_status()
        check_result['ssl'] = self.check_ssl
        check_result['license'] = self.check_license()
        check_result['search_factor'] = self.check_search_factor()
        check_result['replicate_factor'] = self.check_replicate_factor()
        check_result['shc'] = self.searchhead_checkers[0].check_shc_status()

        return check_result

    def check_splunk_status(self):
        check_result = dict()
        for checker in self.all_checkers:
            check_result[checker.splunk_uri] = checker.check_splunk_status()

        return check_result

    def check_license(self):
        pass

    def check_search_factor(self):
        pass

    def check_replicate_factor(self):
        pass

    def check_ssl(self):
        pass

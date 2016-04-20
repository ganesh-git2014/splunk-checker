'''_
@author: Curtis Yu
@contact: cuyu@splunk.com
@since: 4/1/16
'''
import sys
import threading
import json
from multiprocessing.pool import ThreadPool

from optparse import OptionParser

import os
# Helmut 1.2.1
import time
from helmut.splunk import SSHSplunk
from helmut.splunk.windowsssh import WindowsSSHSplunk
from helmut.ssh.connection import SSHConnection
from helmut.splunk.dynamic import SplunkFactory

path_prepend = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'lib')
sys.path.append(path_prepend)
from kvstore_helper import KVStoreHelper


def get_binary_path(self_, binary):
    """

    :type self_: SSHSplunk instance
    """
    if binary.startswith(self_._splunk_home):
        return binary

    if os.path.isabs(binary):
        return binary

    return self_._splunk_home + '/bin/' + binary


# FIXME: 1.hack the splunk_home to support cross platform.
WindowsSSHSplunk.get_binary_path = get_binary_path
SSHSplunk.get_binary_path = get_binary_path


def install_from_archive(self_, archive_path, uninstall_existing=True):
    archive_path = archive_path.replace('/', '\\')
    directory = self_.splunk_home.replace('/', '\\')
    if (uninstall_existing == True):
        self_.uninstall()
    else:  # It stops existing splunk & installs new splunk from the arhive on top of the existing one.
        self_._stop_splunk_if_needed()

    self_._install_from_msi_via_ssh(archive_path, directory, uninstall_existing)
    self_.logger.info('Splunk has been installed.')
    self_.start()


# FIXME: 2.hack the archive_path to support cross platform.
WindowsSSHSplunk.install_from_archive = install_from_archive


class Progress(object):
    InProgress = "InProgress"

    def __init__(self, cluster_id, name):
        """
        :param cluster_id: cluster_id
        :param name: progress name, e.g. 'starting'
        """
        self.cluster_id = cluster_id
        self.name = name
        self.progress = dict()

    def add_watch_object(self, object_name):
        self.progress[object_name] = self.InProgress

    def update_watch_object(self, object_name, status):
        self.progress[object_name] = status

    def json(self):
        result = dict()
        result['cluster_id'] = self.cluster_id
        result['name'] = self.name
        result['progress'] = self.progress
        return json.dumps(result)


class SplunkCluster(object):
    def __init__(self, cluster_id):
        self.cluster_id = cluster_id
        self.master_list = []
        self.other_peer_list = []

    def stop_cluster(self):
        progress = Progress(self.cluster_id, 'stop_cluster')
        for splunk in self.master_list:
            progress.add_watch_object(splunk.name)
            post_progress(progress)
            splunk.stop()
            progress.update_watch_object(splunk.name, 0)
            post_progress(progress)

        num_peer = len(self.other_peer_list)
        if num_peer == 0:
            return
        pool = ThreadPool(processes=num_peer)
        for splunk in self.other_peer_list:
            async_result = pool.apply_async(splunk.stop)
            progress.add_watch_object(splunk.name)
            _thread = self.ProgressThread(progress, splunk.name, async_result)
            _thread.start()

        self._wait_for_all_progress_done(progress)

    def start_cluster(self):
        progress = Progress(self.cluster_id, 'start_cluster')
        for splunk in self.master_list:
            progress.add_watch_object(splunk.name)
            post_progress(progress)
            self.start_wrapper(splunk)
            progress.update_watch_object(splunk.name, 0)
            post_progress(progress)

        num_peer = len(self.other_peer_list)
        if num_peer == 0:
            return
        pool = ThreadPool(processes=num_peer)

        for splunk in self.other_peer_list:
            async_result = pool.apply_async(self.start_wrapper, (splunk,))
            progress.add_watch_object(splunk.name)
            _thread = self.ProgressThread(progress, splunk.name, async_result)
            _thread.start()

        self._wait_for_all_progress_done(progress)

    @staticmethod
    def start_wrapper(splunk):
        # Replace the helmut start method to support more arguments.
        splunk.execute("start --accept-license --answer-yes")

    def upgrade_cluster(self, branch, build, package_type):
        progress = Progress(self.cluster_id, 'upgrade_cluster')
        # Upgrade master first.
        for splunk in self.master_list:
            progress.add_watch_object(splunk.name)
            post_progress(progress)
            splunk.migrate_nightly(branch=branch, build=build, package_type=package_type)
            progress.update_watch_object(splunk.name, 0)
            post_progress(progress)

        num_peer = len(self.other_peer_list)
        if num_peer == 0:
            return
        pool = ThreadPool(processes=num_peer)
        for splunk in self.other_peer_list:
            async_result = pool.apply_async(self.upgrade_wrapper, (splunk, branch, build, package_type))
            progress.add_watch_object(splunk.name)
            _thread = self.ProgressThread(progress, splunk.name, async_result)
            _thread.start()

        self._wait_for_all_progress_done(progress)

    @staticmethod
    def upgrade_wrapper(splunk, branch, build, package_type):
        """
        Wrap the upgrade method so that it can have these inputs by sequence.
        """
        splunk.migrate_nightly(branch=branch, build=build, package_type=package_type)

    def _wait_for_all_progress_done(self, progress, interval=1):
        while True:
            post_progress(progress)
            for item in progress.progress.values():
                if item == Progress.InProgress:
                    break
            else:
                # This break will break the outside loop!
                break
            time.sleep(interval)

    def add_peer(self, splunk_home, role, host, user, password):
        """
        :param splunk_home: installed splunk absolute path
        :param host: ip address or hostname of the remote machine
        :param role: splunk role (e.g. master/indexer)
        :param user: username of the remote machine
        :param password: password of the remote machine
        :return: None
        """
        # Fixme: does it need to set `domain` for Windows?
        # TODO: make connection also multi threaded.
        conn = SSHConnection(host=str(host), user=str(user), password=str(password), domain='')
        splunk = SplunkFactory().getSplunk(str(splunk_home), name=conn.host, connection=conn)
        splunk._splunk_home = splunk_home

        role = role.lower()
        if role == 'master':
            self.master_list.append(splunk)
        else:
            self.other_peer_list.append(splunk)

    class ProgressThread(threading.Thread):
        def __init__(self, progress, name, async_result):
            """
            Used to check the progress of async results.
            :param progress: a dict present each splunk operation progress
            :param name: splunk instance name
            :param async_result: async result
            """
            threading.Thread.__init__(self)
            self.progress = progress
            self.name = name
            self.result = async_result

        def run(self):
            self.progress.update_watch_object(self.name, self.result.get())


global SESSION_KEY, SERVER_URI


def post_progress(progress):
    """
    Used to post the progress to the KVStore.
    :param progress: a {Progress} object.
    """
    helper = KVStoreHelper(SESSION_KEY)
    helper.update_upgrade_progress(
        os.path.join(SERVER_URI, 'servicesNS/nobody/splunk-checker/storage/collections/data/upgrade_progress'),
        progress)


def get_cluster_info(server_uri, session_key, cluster_id):
    """
    Get the cluster info from kvstore.
    """
    helper = KVStoreHelper(session_key)
    try:
        cluster_info_list = helper.get_cluster_info(
            os.path.join(server_uri, 'servicesNS/nobody/splunk-checker/storage/collections/data/clusterinfo'))
    except:
        raise Exception('Failed to get cluster info from kvstore.')

    for cluster_info in cluster_info_list:
        if cluster_info['cluster_id'] == cluster_id:
            return cluster_info


def test_single_instance():
    """
    Only for test.
    """
    conn = SSHConnection(host='10.66.130.3',
                         user='Administrator',
                         password='QWE123asd',
                         domain='')
    splunk_home = 'c:/splunk'
    splunk = SplunkFactory().getSplunk(str(splunk_home), connection=conn)
    splunk.username = 'admin'
    splunk.password = 'changed'
    # Replace the auto generated splunk_home due to cross platform issue.
    splunk._splunk_home = splunk_home

    branch = 'current'
    build = None
    package_type = 'splunk'
    splunk.install_nightly(branch=branch, build=build, package_type=package_type)


if __name__ == '__main__':
    global SESSION_KEY, SERVER_URI
    parser = OptionParser()
    (options, args) = parser.parse_args()
    _SPLUNK_PYTHON_PATH = args[0]
    PATH_LIST = _SPLUNK_PYTHON_PATH.split(':')
    # This step is necessary in order to load splunk packages
    for path in PATH_LIST:
        sys.path.append(path)

    SERVER_URI, SESSION_KEY, cluster_id, branch, build, package_type = args[1:]
    if branch == 'current':
        branch = None
    if build == 'latest':
        build = None
    if package_type == 'splunk':
        package_type = None

    # Init SplunkCluster.
    cluster_info = get_cluster_info(SERVER_URI, SESSION_KEY, cluster_id)
    cluster = SplunkCluster(cluster_id)
    for peer_info in cluster_info['peers']:
        cluster.add_peer(peer_info['splunk_home'], peer_info['role'], peer_info['host'], peer_info['host_username'],
                         peer_info['host_password'])

    cluster.stop_cluster()
    # cluster.upgrade_cluster(branch, build, package_type)
    cluster.start_cluster()

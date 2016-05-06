'''_
@author: Curtis Yu
@contact: cuyu@splunk.com
@since: 4/1/16
'''
import logging
import sys
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
from helmut.log import Logging

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
    Done = "Done"

    def __init__(self, cluster_id, name):
        """
        :param cluster_id: cluster_id
        :param name: progress name, e.g. 'starting'
        """
        self.cluster_id = cluster_id
        self.name = name
        self.progress = dict()

    def set_progress_name(self, name):
        # Will also reset all the progress.
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


class SplunkCluster(Logging):
    def __init__(self, cluster_id):
        # Use helmut logging system.
        super(SplunkCluster, self).__init__()
        self.cluster_id = cluster_id
        self.master_list = []
        self.other_peer_list = []
        self.progress = Progress(cluster_id, 'initializing_cluster')
        self._post_progress()

    def _post_progress(self, delete_progress=False):
        post_progress(self.progress, delete_progress)

    def _init_progress(self, progress_name):
        self.progress.set_progress_name(progress_name)
        for splunk in self.master_list:
            self.progress.add_watch_object(splunk.name)
        for splunk in self.other_peer_list:
            self.progress.add_watch_object(splunk.name)
        self._post_progress()

    def stop_cluster(self):
        self._init_progress('stopping_cluster')
        for splunk in self.master_list:
            self.stop_wrapper(splunk)
            self._post_progress()

        num_peer = len(self.other_peer_list)
        if num_peer == 0:
            return
        pool = ThreadPool(processes=num_peer)

        for splunk in self.other_peer_list:
            async_result = pool.apply_async(self.stop_wrapper, (splunk,))

        self._wait_for_all_progress_done()

    def stop_wrapper(self, splunk):
        self.logger.info("{0} is stopping.".format(splunk.name))
        splunk.stop()
        self.logger.info("{0} has stopped.".format(splunk.name))
        self.progress.update_watch_object(splunk.name, Progress.Done)

    def start_cluster(self):
        self._init_progress('starting_cluster')
        for splunk in self.master_list:
            self.start_wrapper(splunk)
            self._post_progress()

        num_peer = len(self.other_peer_list)
        if num_peer == 0:
            return
        pool = ThreadPool(processes=num_peer)

        for splunk in self.other_peer_list:
            async_result = pool.apply_async(self.start_wrapper, (splunk,))

        self._wait_for_all_progress_done()
        # Delete the progress so it means the whole upgrade operation is done.
        self._post_progress(delete_progress=True)

    def start_wrapper(self, splunk):
        self.logger.info("{0} is starting.".format(splunk.name))
        splunk.execute("start --accept-license --answer-yes")
        self.logger.info("{0} has started.".format(splunk.name))
        self.progress.update_watch_object(splunk.name, Progress.Done)

    def upgrade_cluster(self, branch, build, package_type):
        self._init_progress('upgrading_cluster')

        all_splunk_list = self.other_peer_list + self.master_list
        num_peer = len(all_splunk_list)
        pool = ThreadPool(processes=num_peer)

        for splunk in all_splunk_list:
            async_result = pool.apply_async(self.upgrade_wrapper, (splunk, branch, build, package_type,))

        self._wait_for_all_progress_done()

    def upgrade_wrapper(self, splunk, branch, build, package_type):
        """
        Wrap the upgrade method so that it can have these inputs by sequence.
        """
        self.logger.info("{0} is upgrading.".format(splunk.name))
        splunk.migrate_nightly(branch=branch, build=build, package_type=package_type)
        self.logger.info("{0} has upgraded successfully.".format(splunk.name))
        self.progress.update_watch_object(splunk.name, Progress.Done)

    def _wait_for_all_progress_done(self, interval=0.5):
        progress = self.progress
        last_progress_json = ''
        while True:
            # Post progress if the progress has updated.
            if last_progress_json != progress.json():
                last_progress_json = progress.json()
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
        try:
            conn = SSHConnection(host=str(host), user=str(user), password=str(password), domain='')
        except Exception, e:
            self.logger.error("SSH connect failed on {host}".format(host=host), exc_info=True)
            raise e

        splunk = SplunkFactory().getSplunk(str(splunk_home), name=conn.host, connection=conn)
        splunk._splunk_home = splunk_home

        role = role.lower()
        if role == 'master':
            self.master_list.append(splunk)
        else:
            self.other_peer_list.append(splunk)


global SESSION_KEY, SERVER_URI


def post_progress(progress, delete_progress=False):
    """
    Used to post the progress to the KVStore.
    :param progress: a {Progress} object.
    :param delete_progress: will delete the item from kvstore if is {True}.
    """
    helper = KVStoreHelper(SESSION_KEY)
    endpoint = os.path.join(SERVER_URI, 'servicesNS/nobody/splunk-checker/storage/collections/data/upgrade_progress')
    if delete_progress:
        helper.delete_upgrade_progress(endpoint, progress)
    else:
        helper.update_upgrade_progress(endpoint, progress)


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


# TODO: handle exceptions. (e.g. ssh connection failed)
# TODO: handle ssh execute command `hang` problem.
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

    # Reset the logging level to INFO.
    logging.root.setLevel(logging.INFO)

    # Init SplunkCluster.
    cluster_info = get_cluster_info(SERVER_URI, SESSION_KEY, cluster_id)
    cluster = SplunkCluster(cluster_id)
    try:
        for peer_info in cluster_info['peers']:
            cluster.add_peer(peer_info['splunk_home'], peer_info['role'], peer_info['host'], peer_info['host_username'],
                             peer_info['host_password'])
    except Exception, e:
        post_progress(cluster.progress, delete_progress=True)
        raise e

    cluster.stop_cluster()
    cluster.upgrade_cluster(branch, build, package_type)
    cluster.start_cluster()

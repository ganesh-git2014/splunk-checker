'''_
@author: Curtis Yu
@contact: cuyu@splunk.com
@since: 6/22/16
'''
import os

import rack
from helmut.splunk import SSHSplunk
from helmut.splunk.windowsssh import WindowsSSHSplunk


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
    # Transform the relative archive_path to absolute path.
    if archive_path.startswith('\\'):
        code, stdout, stderr = self_.connection.execute('cygpath -w -p /')
        cygwin_home = stdout.strip()
        archive_path = cygwin_home + archive_path

    directory = self_.splunk_home.replace('/', '\\')
    if (uninstall_existing == True):
        self_.uninstall()
    else:  # It stops existing splunk & installs new splunk from the arhive on top of the existing one.
        self_._stop_splunk_if_needed()

    # Change the seps in splunk home temporarily for executing cmd in self._install_from_msi_via_ssh
    self_._splunk_home = self_.splunk_home.replace('/', '\\')
    self_._install_from_msi_via_ssh(archive_path, directory, uninstall_existing)
    self_._splunk_home = self_.splunk_home.replace('\\', '/')
    self_.logger.info('Splunk has been installed.')
    self_.start()


# FIXME: 2.hack the archive_path to support cross platform.
WindowsSSHSplunk.install_from_archive = install_from_archive


def test_on_windows():
    hosts = ['sys-sh-master.splunk.local', 'sys-sh-sh1.splunk.local', 'sys-sh-sh2.splunk.local',
             'sys-sh-sh3.splunk.local', 'sys-sh-idx1.splunk.local', 'sys-sh-idx2.splunk.local',
             'sys-sh-idx3.splunk.local', 'sys-sh-idx4.splunk.local', 'sys-sh-idx5.splunk.local',
             'sys-sh-deployer.splunk.local', 'sys-sh-fwd1.splunk.local', 'sys-sh-fwd2.splunk.local']
    # Helmut will uninstall splunk first if already exit on the path.
    splunks = rack.install.splunk_instances(hosts, 'c:/splunk', 'Administrator', 'QWE123asd',
                                            url='http://health.sv.splunk.com:8080/current/splunk-7.0.0-03c0d2c2f134-x64-release.msi')
    master = splunks[0]
    search_heads = splunks[1:4]
    indexers = splunks[4:-3]
    deployer = splunks[-3]
    forwarders = splunks[-2:]
    rack.configure.search_head_cluster(captain=search_heads[0], members=search_heads[1:], deployer=deployer,
                                       replication_factor=2)
    rack.configure.index_cluster(master=master, peers=indexers, search_heads=search_heads, replication_factor=3,
                                 search_factor=2)
    rack.configure.license_master(master=master, slaves=splunks[1:],
                                  license_path='/Users/CYu/Code/splunk/splunk-checker/bin/50TB-1.lic')


def test_on_linux():
    hosts = ['systest-auto-master', 'systest-auto-sh1', 'systest-auto-sh2', 'systest-auto-sh3', 'systest-auto-idx1',
             'systest-auto-idx2', 'systest-auto-idx3', 'systest-auto-idx4', 'systest-auto-idx5',
             'systest-auto-deployer', 'systest-auto-fwd1', 'systest-auto-fwd2']
    # Helmut will uninstall splunk first if already exit on the path.
    splunks = rack.install.splunk_instances(hosts, '/root/splunk', 'root', 'sp1unk',
                                            url='http://health.sv.splunk.com:8080/current/splunk-7.0.0-03c0d2c2f134-Linux-x86_64.tgz')
    master = splunks[0]
    search_heads = splunks[1:4]
    indexers = splunks[4:-3]
    deployer = splunks[-3]
    forwarders = splunks[-2:]
    rack.configure.search_head_cluster(captain=search_heads[0], members=search_heads[1:], deployer=deployer,
                                       replication_factor=2)
    rack.configure.index_cluster(master=master, peers=indexers, search_heads=search_heads, replication_factor=3,
                                 search_factor=2)
    rack.configure.license_master(master=master, slaves=splunks[1:],
                                  license_path='/Users/CYu/Code/splunk/splunk-checker/bin/50TB-1.lic')


if __name__ == '__main__':
    test_on_windows()

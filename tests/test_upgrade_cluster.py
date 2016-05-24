'''_
@author: Curtis Yu
@contact: cuyu@splunk.com
@since: 4/6/16
'''
import os
import subprocess

from lib.checker import Checker

if __name__ == '__main__':
    cluster_id = 'systest-linux-sh'
    branch = 'honeybuzz'
    build = 'latest'
    package_type = 'splunk'

    checker = Checker('https://health.sv.splunk.com:8089', 'admin', 'changed')
    session_key = checker._password2sessionkey()

    # Use another subprocess to make the upgrade happen.
    # TODO: remove the hard code python path.
    _NEW_PYTHON_PATH = '/usr/local/Cellar/python/2.7.11/bin/python'
    _SPLUNK_PYTHON_PATH = '/Applications/splunk/lib/python2.7/site-packages:/usr/local/Cellar/python/2.7.11/bin/python'
    CACHED_BUILDS_SERVER = 'http://health.sv.splunk.com:8080'

    os.environ['PYTHONPATH'] = _NEW_PYTHON_PATH
    file_dir = os.path.dirname(os.path.abspath(__file__))
    my_process = os.path.join(file_dir.replace('tests', 'bin'), 'upgrade_cluster.py')

    # Pass the splunk python path as a argument of the subprocess.
    p = subprocess.Popen(
        [os.environ['PYTHONPATH'], my_process, _SPLUNK_PYTHON_PATH, CACHED_BUILDS_SERVER, 'https://health.sv.splunk.com:8089',
         session_key, cluster_id, branch, build, package_type],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    output = p.communicate()[0]
    print output

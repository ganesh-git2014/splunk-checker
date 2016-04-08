'''_
@author: Curtis Yu
@contact: cuyu@splunk.com
@since: 4/6/16
'''
import ConfigParser
import subprocess

from splunk import admin
from splunk import rest
import os


# import default


def read_conf_item(conf_name, stanza, item):
    cf = ConfigParser.ConfigParser()
    cf.optionxform = str
    current_path = os.path.dirname(os.path.abspath(__file__))
    f = open(os.path.join(current_path.replace('/bin', '/default'), conf_name + '.conf'), 'r')
    cf.readfp(f)
    kv_pairs = cf.items(stanza)
    for pair in kv_pairs:
        if pair[0] == item:
            return pair[1]


class StoreCluster(admin.MConfigHandler):
    def setup(self):
        if self.requestedAction == admin.ACTION_CREATE:
            self.supportedArgs.addReqArg('cluster_id')
            self.supportedArgs.addReqArg('branch')
            self.supportedArgs.addReqArg('build')
            self.supportedArgs.addReqArg('package_type')
        return

    def handleList(self, confInfo):
        pass

    def handleCreate(self, confInfo):
        post_data = self.callerArgs.data
        cluster_id = post_data['cluster_id'][0]
        branch = post_data['branch'][0]
        build = post_data['build'][0]
        package_type = post_data['package_type'][0]

        # Use another subprocess to make the upgrade happen.
        _NEW_PYTHON_PATH = read_conf_item('cluster_upgrade', 'general', 'pythonPath')
        _SPLUNK_PYTHON_PATH = os.environ['PYTHONPATH']

        os.environ['PYTHONPATH'] = _NEW_PYTHON_PATH
        my_process = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'upgrade_cluster.py')

        # Pass the splunk python path as a argument of the subprocess.
        p = subprocess.Popen(
            [os.environ['PYTHONPATH'], my_process, _SPLUNK_PYTHON_PATH, rest.makeSplunkdUri(), self.getSessionKey(),
             cluster_id, branch, build, package_type],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        output = p.communicate()[0]
        confInfo['upgrade']['progress'] = '[Done]'
        # if output == '':
        #     confInfo['upgrade']['progress'] = 'Success'
        # else:
        #     confInfo['upgrade']['progress'] = 'Failed'


if __name__ == "__main__":
    admin.init(StoreCluster, admin.CONTEXT_APP_AND_USER)

'''_
@author: Curtis Yu
@contact: cuyu@splunk.com
@since: 3/16/16
'''
import json
from splunk import admin
from splunk import rest
import os

path_prepend = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'lib')
sys.path.append(path_prepend)
from kvstore_helper import KVStoreHelper

# import default


class StoreCluster(admin.MConfigHandler):
    def setup(self):
        if self.requestedAction == admin.ACTION_CREATE:
            self.supportedArgs.addReqArg('cluster_id')
            self.supportedArgs.addReqArg('enable_cluster')
            self.supportedArgs.addReqArg('enable_shcluster')
            self.supportedArgs.addReqArg('replication_factor')
            self.supportedArgs.addReqArg('search_factor')
            self.supportedArgs.addReqArg('splunk_uri')
            self.supportedArgs.addReqArg('username')
            self.supportedArgs.addReqArg('password')
            self.supportedArgs.addReqArg('role')
            self.supportedArgs.addReqArg('splunk_home')
            self.supportedArgs.addReqArg('host')
            self.supportedArgs.addReqArg('host_username')
            self.supportedArgs.addReqArg('host_password')
        return

    # def handleEdit(self, confInfo):
    #     # cluster_info = self.callerArgs.data
    #     # session_key = self.getSessionKey()
    #     # splunkd_uri = rest.makeSplunkdUri()
    #     confInfo["hello"]["a"] = "helloa"

    def handleList(self, confInfo):
        helper = KVStoreHelper(self.getSessionKey())
        uri = rest.makeSplunkdUri()
        content = helper.get_cluster_info(uri + 'servicesNS/nobody/splunk-checker/storage/collections/data/clusterinfo')
        # TODO: transform to confInfo
        for cluster_info in content:
            confInfo[cluster_info['cluster_id']]['cluster_info'] = json.dumps(cluster_info)

    def handleCreate(self, confInfo):
        post_data = self.callerArgs.data
        cluster_id = post_data['cluster_id'][0]
        splunk_info = dict()
        cluster_info = dict()
        for item in post_data.keys():
            if item != 'cluster_id':
                confInfo[cluster_id][item] = post_data[item][0]
        cluster_items = ['cluster_id', 'enable_cluster', 'enable_shcluster', 'replication_factor', 'search_factor']
        for item in post_data.keys():
            if item in cluster_items:
                cluster_info[item] = post_data[item][0]
            else:
                splunk_info[item] = post_data[item][0]

        cluster_info['peers'] = []
        cluster_info['peers'].append(splunk_info)
        helper = KVStoreHelper(self.getSessionKey())
        uri = rest.makeSplunkdUri()
        helper.update_cluster_info(uri + 'servicesNS/nobody/splunk-checker/storage/collections/data/clusterinfo',
                                   cluster_info)


if __name__ == "__main__":
    admin.init(StoreCluster, admin.CONTEXT_APP_AND_USER)

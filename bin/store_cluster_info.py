'''_
@author: Curtis Yu
@contact: cuyu@splunk.com
@since: 3/16/16
'''
from splunk import admin
from splunk import rest
# import default


class StoreCluster(admin.MConfigHandler):
    def setup(self):
        pass

    def handleEdit(self, confInfo):
        cluster_info = self.callerArgs.data
        session_key = self.getSessionKey()
        splunkd_uri = rest.makeSplunkdUri()
        confInfo["hello"]["a"] = "helloa"

    def handleList(self, confInfo):
        confInfo["hello"]["b"] = "helloa"

    def handleCreate(self, confInfo):
        confInfo["hello"]["c"] = "helloa"
        pass

if __name__ == "__main__":
    admin.init(StoreCluster, admin.CONTEXT_APP_AND_USER)

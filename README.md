# Splunk Checker
This app is used to check cluster health status.

## User Guide

### How to use
It's easy to use:

1. Install the app to splunk
2. Configure the cluster environments you want to check through configuration page (e.g. <http://localhost:8000/en-US/app/splunk-checker/configuration>)
3. Wait for some time until next check execution (The default interval is 10min)
4. Find check results from overview page (e.g. <http://localhost:8000/en-US/app/splunk-checker/overview>)

### The severity of warning messages
We define 3 different kind of severity, from most severe to least severe: `severe`, `elevated`, `low`. The `low` is defined as nearly normal here, so if a check item comes with no warning messages is also expressed as `low`. Besides, we define a severity as `unknown` for those skipped check items.

## Dev Guide

### The implementation of the app
The following splunk features are used to implement the app:

- Use modular input to execute the python script regularly
- Use kvstore to store the cluster infomation (e.g. <https://localhost:8089/servicesNS/nobody/splunk-checker/storage/collections/data/clusterinfo>)
- Use the `index=splunk_checker` to store all the collected infomation from all the clusters
- Use `restmap.conf` and `web.conf` to make a mapping from web site to REST (e.g. <http://localhost:8000/en-US/splunkd/__raw/servicesNS/nobody/splunk-checker/splunk_checker/store_cluster_info> mapped to <https://localhost:8089/servicesNS/nobody/splunk-checker/splunk_checker/store_cluster_info>)
- Customized xml and html page

### How to add a check item
1. In the `lib/constant.py`, add the item name to `CHECK_TIEM`;
2. In the `lib/cluster_checker.py`, add the 'check\_\*method' and corresponding '\_generate\_*_message method' to the class (The former one is used to acquire the infomation from splunk REST and the latter one is used to transform the infomation into warning messages);
3. In the `lib/cluster_checker.py`, register the methods created in step 2 to the `_map_check_method` and `_map_generate_message_method`;

If the REST info acquired by each splunk checker class(e.g. `IndexerChecker`) is not enough, you may need to add more methods to acquire more info.

---

**For example**, I'd like to add a check item to check the disk space of each vm from splunk. So I'll do the following changes:

First of all, we must add the new check item to `CHECK_ITEM` in the `constant.py`.

	CHECK_ITEM = frozenset([
    	'SPLUNK_STATUS',
    	'DISK_SPACE',
    	'SSL',
    	'LICENSE',
    	'CLUSTER',
    	'SHCLUSTER'
	])

As the disk space info has not been acquired from any methods, so we add a `check_disk_space` to the `checker` class:

	@catch_http_exception
    def check_disk_space(self):
        result = dict()
        parsed_response = self._request_get('/services/server/status/partitions-space')
        result['disk_space'] = self._select_dict(parsed_response['entry'][0]['content'], ['available', 'capacity'])
        return result

Then, create a `check_disk_space` method in the `ClusterChecker` class:

	    def check_disk_space(self):
        	check_results = []
        	for checker in self.all_checkers:
            	tmp_result = checker.check_disk_space()
            	tmp_result['splunk_uri'] = checker.splunk_uri
            	check_results.append(tmp_result)

        	return check_results

Corresponding to the `check_disk_space` method, add the following method to generate warning messages.

    def _generate_disk_space_message(self, check_results):
        msg_list = []
        th_space = 4000
        for result in check_results:
            if float(result['disk_space']['available']) < th_space:
                self._add_warning_message(msg_list,
                                          'The disk space is not enough on [{0}]! Only {1}Mb avaliable.'.format(
                                              result['splunk_uri'], result['disk_space']['available']), Severity.SEVERE)

At last, in `_map_check_method` and `_map_generate_message_method`, register the new added methods to the method map.
	
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

Restart splunk, and the new check item will be found in the coming events.

## TODO List

- Support for multi-site cluster
- Support for more roles: e.g. deployer, deployment server
- We assume all the search head in the same SHC, but there's more complex situation
- ~~Check for ssl~~
- Check for normal conf settings
- Can delete/edit cluster info from configuration page
- ~~Add severity of each warning message~~
- Add more dashboards for display
- Control splunk through REST (e.g. restart all splunk in a cluster)
- Check concurrent search number
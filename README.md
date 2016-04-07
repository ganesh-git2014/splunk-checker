# Splunk Checker
This app is used to check cluster health status.
## What it can do
- Check splunk stats over several clusters
- Give warning messages for each check item
- Upgrade cluster to specific version, build

## User Guide

### How to use
It's easy to use:

1. Install the app to splunk
2. Configure the cluster environments you want to check through configuration page (e.g. <http://localhost:8000/en-US/app/splunk-checker/configuration>)
3. Wait for some time until next check execution (The default interval is 10min)
4. Find check results from overview page (e.g. <http://localhost:8000/en-US/app/splunk-checker/overview>)

### The check points
For now, these check points are supported for checking (The stats of each check point can be find using SPL: `index=splunk_checker source=check_stats`):

- **SPLUNK_STATUS** 
	- Check if all splunk are in status 'Up'
- **CLUSTER**
	- Check if replication factor is same as defined
	- Check if search factor is same as defined
	- Check if active bundle id is the same for all peers
- **SHCLUSTER**
	- Check if the number of search heads is more than 3
	- Check if the captain is the same one from all search heads
- **LICENSE**
	- Check if the license master is in the cluster (for license slave)
	- Check if all licenses are about to expire (for license master)
	- Check if the license usage is hitting the quota (for license master)
- **RESOURCE_USAGE**
	- Check if disk space is enough
	- Check if memory usage is too high
	- Check if CPU usage is too high
- **SSL**
	- Check if default certificate is used in server.conf
	- Check if ssl is configured in inputs.conf (for indexers)
	- Check if ssl is configured in outputs.conf (for forwarders)

### The skipped check points
For the following circumstances[^1] the corresponding check points will not be checked:

- shcluster is disabled (default is enabled): **SHCLUSTER** will not be checked
- cluster is disabled (default is enabled): **CLUSTER** will not be checked
- ssl is enabled (default is disabled): **SSL** will not be checked

[^1]:The above settings are configured when setting the cluster environment.

### The severity of warning messages
We define 3 different kind of severity, from most severe to least severe: `severe`, `elevated`, `low`. The `low` is defined as nearly normal here, so if a check item comes with no warning messages is also expressed as `low`. Besides, we define a severity as `unknown` for those skipped check items.

### Prerequisites for upgrading cluster
**What should you do**: Change the `pythonPath` item in `cluster_upgrade.conf` file to the specific path.

**Reason**: Because splunk do not support install python package to its own python interpreter, we use a subprocess to enable another outside python interpreter. So you need to specify the python interpreter and make sure that interpreter has `helmut` installed. (Maybe just copy the `helmut` package to the splunk python path also works! Not try yet.)

**About version**: We suggest at least `python 2.7.9` and `helmut 1.2.1`. (In earlier `helmut`, splunk installing on Windows did not use *msi* package.)

## Dev Guide

### The implementation of the app
The following splunk features are used to implement the app:

- Use modular input to execute the python script regularly
- Use kvstore to store the cluster infomation (e.g. <https://localhost:8089/servicesNS/nobody/splunk-checker/storage/collections/data/clusterinfo>)
- Use the `index=splunk_checker` to store all the collected infomation from all the clusters
- Use `restmap.conf` and `web.conf` to make a mapping from web site to REST (e.g. <http://localhost:8000/en-US/splunkd/__raw/servicesNS/nobody/splunk-checker/splunk_checker/store_cluster_info> mapped to <https://localhost:8089/servicesNS/nobody/splunk-checker/splunk_checker/store_cluster_info>)
- Customized xml and html page
- Use python subprocess so that we can use outside python interpreter and packages in our script (Can also implenmented by custom search command in new version of splunk now)

### How to add a check item
1. In the `lib/constant.py`, add the item name to `CHECK_TIEM`;
2. In the `lib/cluster_checker.py`, add the 'check\_\*method' and corresponding '\_generate\_*_message method' to the class (The former one is used to acquire the infomation from splunk REST and the latter one is used to transform the infomation into warning messages);
3. In the `lib/cluster_checker.py`, register the methods created in step 2 to the `_map_check_method` and `_map_generate_message_method`;

If the REST info acquired by each splunk checker class(e.g. `IndexerChecker`) is not enough, you may need to add more methods to acquire more info.

---

**For example**, I'd like to add a check item to check the disk space of each vm from splunk. So I'll do the following changes:

First of all, we must add the new check item to `CHECK_ITEM` in the `constant.py`.

```python
	CHECK_ITEM = frozenset([
    	'SPLUNK_STATUS',
    	'DISK_SPACE',
    	'SSL',
    	'LICENSE',
    	'CLUSTER',
    	'SHCLUSTER'
	])
```

As the disk space info has not been acquired from any methods, so we add a `check_disk_space` to the `checker` class:

```python
	@catch_http_exception
    def check_disk_space(self):
        result = dict()
        parsed_response = self._request_get('/services/server/status/partitions-space')
        result['disk_space'] = self._select_dict(parsed_response['entry'][0]['content'], ['available', 'capacity'])
        return result
```

Then, create a `check_disk_space` method in the `ClusterChecker` class:

```python
	    def check_disk_space(self):
        	check_results = []
        	for checker in self.all_checkers:
            	tmp_result = checker.check_disk_space()
            	tmp_result['splunk_uri'] = checker.splunk_uri
            	check_results.append(tmp_result)

        	return check_results
```

Corresponding to the `check_disk_space` method, add the following method to generate warning messages.

```python
    def _generate_disk_space_message(self, check_results):
        msg_list = []
        th_space = 4000
        for result in check_results:
            if float(result['disk_space']['available']) < th_space:
                self._add_warning_message(msg_list,
                                          'The disk space is not enough on [{0}]! Only {1}Mb avaliable.'.format(
                                              result['splunk_uri'], result['disk_space']['available']), Severity.SEVERE)                                                                                         ```

At last, in `_map_check_method` and `_map_generate_message_method`, register the new added methods to the method map.
	
```python 	
	def _map_check_method(self, item):
        assert item in CHECK_ITEM
        method_map = {'SPLUNK_STATUS': self.check_splunk_status,
                      'SSL': self.check_ssl,
                      'LICENSE': self.check_license,
                      'CLUSTER': self.check_cluster,
                      'SHCLUSTER': self.check_shcluster,
                      'DISK_SPACE': self.check_disk_space}
        return method_map[ite
  
    def _map_generate_message_method(self, item):
        assert item in CHECK_ITEM
        method_map = {'SPLUNK_STATUS': self._generate_splunk_status_message,
                      'SSL': self._generate_ssl_message,
                      'LICENSE': self._generate_license_message,
                      'CLUSTER': self._generate_cluster_message,
                      'SHCLUSTER': self._generate_shcluster_message,
                      'DISK_SPACE': self._generate_disk_space_message}
        return method_map[item]
```

Restart splunk, and the new check item will be found in the coming events.

## Limits
- This app can only support installed on Linux OS. (Some `/` need to be replaced with `\` on Windows)

## TODO List

- Support for multi-site cluster
- Support for more roles: e.g. deployer, deployment server
- We assume all the search head in the same SHC, but there's more complex situation
- ~~Check for ssl~~
- Check for normal conf settings
- Can delete/edit cluster info from configuration page
- ~~Rearrange configuration page layout~~
- ~~Add severity of each warning message~~
- ~~Add more dashboards for display~~
- Control splunk through REST (e.g. restart all splunk in a cluster)
- Check concurrent search number
- Add a process progress bar for cluster upgrade
- Auto fill the splunk home & host in configuration page
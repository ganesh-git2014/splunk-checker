# Splunk Checker
This app is used to check cluster health status.

## User Guide
It's easy to use:

1. Install the app to splunk
2. Configure the cluster environments you want to check through configuration page (e.g. <http://localhost:8000/en-US/app/splunk-checker/configuration>)
3. Wait for some time until next check execution (The default interval is 10min)
4. Find check results from overview page (e.g. <http://localhost:8000/en-US/app/splunk-checker/overview>)

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

## TODO List

- Support for multi-site cluster
- Support for more roles: e.g. deployer, deployment server
- We assume all the search head in the same SHC, but there's more complex situation
- Check for ssl
- Check for normal conf settings
- Can delete/edit cluster info from configuration page
- Add severity of each warning message
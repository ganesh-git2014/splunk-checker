
## Dev Guide

### The composition of the app

### How to add a check item
1. In the `lib/constant.py`, add the item name to `CHECK_TIEM`;
2. In the `lib/cluster_checker.py`, add the 'check_* method' and corresponding '_generate_*_message method' to the class (The former one is used to acquire the infomation from splunk REST and the latter one is used to transform the infomation into warning messages);
3. In the `lib/cluster_checker.py`, register the methods created in step 2 to the `_map_check_method` and `_map_generate_message_method`;

If the default REST info acquired by each splunk checker class(e.g. `IndexerChecker`) is not enough, you may need to add more methods to acquire more info.

## TODO List

- Support for multi-site cluster
- We assume all the search head in the same SHC, but there's more complex situation
- Check for ssl
- Check for normal conf settings
- Can delete/edit cluster info from configuration page
'''_
@author: Curtis Yu
@contact: cuyu@splunk.com
@since: 3/8/16
'''
from lib.checker import Checker
from lib.constant import bcolors
from lib.master_checker import MasterChecker
from lib.searchhead_checker import SearchHeadChecker


def test_check_splunk_status():
    checker_master = MasterChecker('https://systest-auto-master:1901', 'admin', 'changed')
    print 'Checking splunk status:'
    if checker_master.check_splunk_status():
        print bcolors.OKGREEN + '[Up]' + bcolors.ENDC
    else:
        print bcolors.FAIL + '[Down]' + bcolors.ENDC


def test_check_shc_status():
    checker_sh = SearchHeadChecker('https://systest-auto-sh1:1901', 'admin', 'changed')
    print 'Checking shc status:'
    checker_sh.check_shc_status()


def test_check_license():
    checker = Checker('https://systest-auto-master:1901', 'admin', 'changed')
    print 'Checking license:'
    checker.check_license()


if __name__ == '__main__':
    test_check_license()

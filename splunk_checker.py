'''_
@author: Curtis Yu
@contact: cuyu@splunk.com
@since: 3/8/16
'''
from lib.checker import Checker
from lib.constant import bcolors

if __name__ == '__main__':
    checker_master = Checker('https://systest-auto-master:1901', 'admin', 'changed')
    print 'Checking splunk status:'
    if checker_master.check_splunk_status():
        print bcolors.OKGREEN + '[Up]' + bcolors.ENDC
    else:
        print bcolors.FAIL + '[Down]' + bcolors.ENDC

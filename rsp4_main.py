#!/bin/env python
###################################################################
# script: fretta_sanity.py
# Clean boot and lxc and calvados launch
###################################################################

"""
   TAG_MAP:
        title:          Fretta Coherent Scale_Stress
        descr:          Testsuite for Scale_Stress on ncs5500
        platform:       NCS5508
        min-sw-ver:     06.02.02
        test-phase:     dev-test
        modular-pkg:    coherent
        test-type:      functionality
        test-component: ['coherent']
        sw-component: 
        topology:       Fretta-Two-Router-Dynamic
        tgn-type:       spirent
        link-type:      100G,150 and 200
        customer:       not-applicable
        cdets-attribute: fretta-coherent
        run_time:   10hrs
        projects:   DevTest
"""


from ats import tcl
from ats import aetest
from ats.atslog.utils import banner
from ats.results import *
import re
import pdb
import logging
import os
import pprint
import sth
import collections
from IPython import embed
import itertools 
from time import sleep
from xtgn_lib.stclib import Spirent, g_stc_handles
from pprint import pprint
from xNetworkEvents import *
from xTopology import routers, tgns
from xFretta_lib import *
from xCommon_lib import *
#from Fretta_pmfc_Scripts.Coh_Libs.Pkt_Libs import *
#from Fretta_pmfc_Scripts.Coh_Libs.DWDM_Libs import *
#from Fretta_pmfc_Scripts.Coh_Libs.MacSec_Libs import *
#from Fretta_pmfc_Scripts.Coh_Libs.utils import *
from Fretta_pmfc_Scripts.rsp4_dpfga.rsp4_lib import *
from Fretta_pmfc_Scripts.rsp4_dpfga.utils import *
from fwd_scripts.fwd_config import *
from XVerification import *
#from autoparser import pyparse
from xNetworkEvents import *

global event
event = Events()

tcl.eval('package require Mpexpr')

class ConfigError(Exception):
    """raised if any config failed"""

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
#the default severity is debug
log = XLog(level=logging.DEBUG)

def get_test_topo(test_topo):
    global g_topo_data
    global response
    global r1_ping_ip
    global r2_ping_ip
    global config1
    global config2
    global r1_IMS
    global r2_IMS
    global r1_PE1_slot
    global r1_slot
    global r2_slot
    global PE1_config
    global r1_pe1_ping_ip
    global r2_pe2_ping_ip
    global r1_process
    global r2_process
    response = collections.OrderedDict()
    
    g_topo_data = {}
    g_topo_data['R1'] = test_topo['R1']
    g_topo_data['R2'] = test_topo['R2']
    g_topo_data['R1a'] = test_topo['R1a']
    g_topo_data['R2a'] = test_topo['R2a']
    config1 = test_topo['config1']
    config2 = test_topo['config2']
    r1_ping_ip = test_topo['r1_ping_ip']
    r2_ping_ip = test_topo['r2_ping_ip']
    r1_IMS = test_topo['r1_IMS']
    r2_IMS = test_topo['r2_IMS']
    r1_PE1_slot = test_topo['r1_PE1_slot']
    r1_slot = test_topo['r1_slot']
    r2_slot = test_topo['r2_slot']
    PE1_config = test_topo['PE1_config']
    r1_pe1_ping_ip = test_topo['r1_pe1_ping_ip']
    r2_pe2_ping_ip = test_topo['r2_pe2_ping_ip']
    r1_process = test_topo['r1_process']
    r2_process = test_topo['r2_process']

global GV
GV = {}

def verify_show_logging_context(rtr):
    """ Verify show logging and show context. Raise Exception in faliure"""

    success = True

    try:
        rtr.execute('show logging')
        log.info("Show logging execution passed")
    except Exception as err:
        log.info(err)
        log.error('show logging execution failed')
        log.error("Exception type: {}".format(str(err)))
        wait_time = 300
        log.info("waiting for {}s, suspecting connection timedout"
                  .format(wait_time))
        time.sleep(wait_time)
        success = False

    command = r'''show logging | include \"CPUHOG|MALLOCFAIL|Traceback'''
    command += r'''|_ERROR|abnormally|FATAL\"'''
    logging_out = rtr.execute(command)
    ptrn = "(CPUHOG.*)|(MALLOCFAIL.*)|(Traceback.*)|(_ERROR.*)|(abnormally.*)|(FATAL.*)|(restart.*)"
    flag = 0
    for line in logging_out.split('\r\n'):
        matchObj = re.search("show logging.*", line, re.I)
        if matchObj:
            continue
        matchObj = re.search(".*UTC", line, re.I)
        if matchObj:
            continue
        matchObj = re.search("0\/RP[0|1]\/CPU0.*#", line, re.I)
        if matchObj:
            continue
        matchObj = re.search(ptrn, line, re.I)
        if matchObj:
            match = re.search(r'L2-CFM-5-CCM_ERROR_CCMS_MISSED', line, re.I)
            if not match:
                flag += 1
    if flag:
        msg = "Observed error messages in show logging. "
        log.error(msg)
        processes = set()
        for line in logging_out.split('\r\n'):
            matchObj = re.search(r'\(PID\=(\d+)\).*Traceback.*', line, re.I)
            if matchObj:
                processes.add(matchObj.group(1))
        for pid in processes:
            rtr.execute("show processes %s" % pid)
            rtr.execute("show dll pid %s" % pid)

        success = False
    else:
        msg = "No error messages observed in show logging"
        log.info(msg)

    try:
        pyRes = rtr.verify('show context location all', parse_only = 'yes', parser_type = 'textfsm')

        pids = list()
        if 'pid' in pyRes:
            pids = pyRes['pid'].keys()
            crashnames = list()
            for pid in pids:
                crashnames.append(pyRes['pid'][pid]['name'])

            msg = ('Cores/crashes %s Found. ' % crashnames)
            log.error(msg)
            success = False
        else:
            log.info("No Crashes Found")
    except:
        msg = ('Failed to parse show context in the router %s ' % rtr)
        log.error(msg)
        success = False

    try:
        rtr.transmit('admin\r')
        rtr.receive('sysadmin-vm.*')
        rtr.execute('terminal length 0')

        pyRes = rtr.verify('show context location all', parse_only = 'yes', parser_type = 'textfsm')

        pids = list()
        if 'pid' in pyRes:
            pids = pyRes['pid'].keys()
            crashnames = list()
            for pid in pids:
                crashnames.append(pyRes['pid'][pid]['name'])

            msg = ('Cores/crashes %s Found. ' % crashnames)
            log.error(msg)
            success = False
        else:
            log.info("No Crashes Found")

        rtr.execute("clear context location all")

        rtr.transmit('exit\r')
        if not rtr.receive(r'RP/0/RP[0-1].*\#', timeout = 5):
            log.error('Router is not in xr prompt')
            success = False
    except:
        msg = ('Failed to parse show context in the router %s ' % rtr)
        log.error(msg)
        success = False

    try:
        rtr.execute("clear logging")
        rtr.execute("clear context location all")
        log.info("Clear logging and context passed")
    except:
        msg = ("Clear logging and context failed. ")
        log.error(msg)
        success = False

    return success


def Verifylc(rtr, lc='all'):
    flag = 0
    for i in range(1,4):
        sleep(60)
        rtr.transmit('admin\r')
        rtr.expect(r'#', timeout=5)
        output = rtr.execute('show platform location %s' % lc)
        rtr.transmit("exit")
        if re.search("OPERATIONAL",output):
            log.info("LC is operational")
            return True
    log.info("Lc is not operational after waiting 240 secs")
    return False

    # plat = {}
    # xr_pattern = "([A-Z0-9\/]+)\s+[A-Z\(\)\s]+\s+[A-Z]+\s+([A-Z]+\s[A-Za-z]+)\s+([0-9\.]+)"
    # for i in range(1, 3):
    #     sleep(60)
    #     output = rtr.execute('show platform vm')
    #     for line in output.split('\n'):
    #         matchObj = re.search('\-\-\-\-', line, re.I)
    #         if matchObj:
    #             continue
    #         if re.search(xr_pattern, line):
    #             matchObj = re.search(xr_pattern, line)
    #             loc = matchObj.group(1)
    #             status = matchObj.group(2)
    #             ip_addr = matchObj.group(3)
    #             if loc == lc and status == 'FINAL Band':
    #                 plat[loc] = {'status': status, 'ip_addr': ip_addr}
    #                 break
    # if plat[lc]['status'] == 'FINAL Band':
    #     log.info("LC is in operational state")
    #     return True
    # else:
    #     log.info("Verifying the LC vm")
    #     lc = lc.replace('/CPU0', '')
    #     rtr.transmit('admin\r')
    #     rtr.expect(r'#', timeout=5)
    #     output = rtr.transmit('show vm location %s' % lc)
    #     pattern = "[a-zA-Z]+\-[a-zA-Z]+\s*[a-zA-Z]+"
    #     for line in output.split('\n'):
    #         matchObj = re.search('\-\-\-\-', line, re.I)
    #         if matchObj:
    #             continue
    #         if re.search(pattern, line):
    #             matchObj = re.search(pattern, line).grou()
    #             status = matchObj.split(' ')[-1]
    #         else:
    #             status = ""
    #         if status == 'running':
    #             log.info("VM is up and running")
    #             rtr.transmit('exit\r')
    #             return True
    #         else:
    #             log.info("VM is in down state")
    #             rtr.transmit('exit\r')
    #             return False


class common_setup(aetest.CommonSetup):

    
    """
    TAG_MAP:
        title:          Fretta PM FC COMMON SETUP
        descr:          Testsuite for Fretta PM FC NCS5500
        platform:       NCS5500
        min-sw-ver:     6.1.0
        test-phase:     sanity-test
        modular-pkg:    fretta-platform
        test-type:      functionality
        test-component: ['ipv4-fwd','ipv6-fwd']
        sw-component:   fretta-l3fib
        topology:       tgen-fretta-fretta-tgen
        tgn-type:       spirent
        link-type:      100G
        customer:       all
        cdets-attribute: auto-fwd-ip
        run_time:   90
        projects:   DevTest
    """
    
    global testCaseName
    testCaseName=''
    @aetest.subsection
    def connect_to_Fretta(self):
        """ common setup subsection: connecting devices """
        global g_topo_data

        log.info(banner("Common Setup: Connection to devices"))
        
        #self.script_args['testStep'] = 1
        get_test_topo(self.script_args)

        rtr1_name = g_topo_data['R1']
        rtr1 = routers[rtr1_name]
        rtr2_name = g_topo_data['R2']
        rtr2 = routers[rtr2_name]

        # Step 1
        self.script_args['testStep'] = 1
        log.info(banner("STEP %s: Device Connection" %
                        (self.script_args['testStep'])))

        # Create instance of device R1
        device_uut = self.script_args['R1']
        self.script_args['uut'] = self.script_args[
            'testbed'].devices[device_uut]

        tcl.eval('set csccon_default(clear_config_inconsistancy) 0')
        self.script_args['uut'].connect()
        log.info("STEP %s: Device Connection Passed" %
                 (self.script_args['testStep']))
        rtr1.execute("terminal length 500")
        rtr1.execute("terminal width 500")
        response["Clear logging buffer \[confirm\] \[y\/n\] \:"] = "econ_sendline y;exp_continue"
        rtr1.execute("clear logging", reply=response)
        rtr1.execute("clear context", reply=response)
        #pdb.set_trace()
        #rtr1.admin("show platform")

        self.script_args['testStep'] = 2
        log.info(banner("STEP %s: Device Connection" %
                        (self.script_args['testStep'])))

        device_uut_r2 = self.script_args['R2']
        self.script_args['uut_r2'] = self.script_args[
            'testbed'].devices[device_uut_r2]
        tcl.eval('set csccon_default(clear_config_inconsistancy) 0')
        self.script_args['uut_r2'].connect()
        log.info("STEP %s: Device Connection Passed" %
                 (self.script_args['testStep']))
        rtr2.execute("terminal length 500")
        rtr2.execute("terminal width 500")
        response["Clear logging buffer \[confirm\] \[y\/n\] \:"] = "econ_sendline y;exp_continue"
        rtr2.execute("clear logging", reply=response)
        rtr2.execute("clear context", reply=response)



class ping_testcase(aetest.Testcase):
    '''
    TAG_MAP:
       title: ConfigUnconfig
       descr: This test case covers Config & Rollback.
       platform: NCS5500
       min-sw-ver: 6.1.0
       test-phase: dev-test
       modular-pkg: fretta-platform
       test-type: functionality
       test-component: ['coherent']
       sw-component: fretta-coherent
       topology: tgen-fretta-fretta-tgen
       tgn-type: spirent
       link-type: 100G
       customer: all
       cdets-attribute:  auto-fwd-ip
    '''
    execution_group = 'ipv4' 

    """ This is user Testcases section """
    @aetest.setup
    def prepare_for_subtest(self):
        """ Testcase Setup section """
        log.info(banner(" Aetest Testcase Execution "))

    @aetest.test
    def Shut_NoShut(self):
        global g_topo_data,g_test_data
        global GV

        rtr1_name=g_topo_data['R1']
        rtr1=routers[rtr1_name]
        rtr1.execute("terminal length 500")
        rtr1.execute("terminal width 500")

        rtr2_name = g_topo_data['R2']
        rtr2 = routers[rtr2_name]
        rtr2.execute("terminal length 500")
        rtr2.execute("terminal width 500")

        cmds_r1 = []
        for int_list in config1:
            cmds_r1 = cmds_r1 + ['interface {}'.format(int_list[0]),
                           'no shut',
                           'ipv4 add {} 255.255.255.0'.format(int_list[1])]
        rtr1.config(cmds_r1)

        cmds_r2 = []
        for int_list in config2:
            cmds_r2 = cmds_r2 + ['interface {}'.format(int_list[0]),
                                 'no shut',
                                 'ipv4 add {} 255.255.255.0'.format(int_list[1])]
        rtr2.config(cmds_r2)

        log.info("Pinging on router 1")
        for ip in r1_ping_ip:
            result = rtr1.execute("ping %s" % ip)
            match = re.search(r'Success rate is (?P<rate>\d+) percent', result)
            success_rate = match.group('rate')
            log.info('Ping {} with success rate of {}%'.format(ip, success_rate, ))
        log.info("Pinging on router 2")
        for ip in r2_ping_ip:
            result = rtr2.execute("ping %s" % ip)
            match = re.search(r'Success rate is (?P<rate>\d+) percent', result)
            success_rate = match.group('rate')
            log.info('Ping {} with success rate of {}%'.format(ip, success_rate, ))

    @aetest.cleanup
    def clean_this_tc(self):
        """ Testcase cleanup section """
        log.info("No Changes were made in setup section. \
        		Hence clean up is not required")
        log.info("Pass testcase cleanup")

##################################################################


class Test_OIR(aetest.Testcase):
    '''
    TAG_MAP:
       title: ContinuousLcReload
       descr: This test case covers Continuous LC Reload.
       platform: NCS5500
       min-sw-ver: 6.1.0
       test-phase: dev-test
       modular-pkg: fretta-platform
       test-type: functionality
       test-component: ['coherent']
       sw-component: fretta-coherent
       topology: tgen-fretta-fretta-tgen
       tgn-type: spirent
       link-type: 100G
       customer: all
       cdets-attribute:  auto-fwd-ip
    '''
    execution_group = 'ipv4'

    """ This is user Testcases section """
    @aetest.setup
    def prepare_for_subtest(self):
        """ Testcase Setup section """
        log.info(banner(" Aetest Testcase Execution "))

    @aetest.test
    def Shut_NoShut(self):
        #embed()
        testCaseName="Scale_Stress1"
        global g_topo_data, g_test_data
        global GV

        rtr1_name = g_topo_data['R1']
        rtr1 = routers[rtr1_name]
        rtr1.execute("terminal length 500")
        rtr1.execute("terminal width 500")

        rtr2_name = g_topo_data['R2']
        rtr2 = routers[rtr2_name]
        rtr2.execute("terminal length 500")
        rtr2.execute("terminal width 500")
        LcNodeList = []
        # rtr.transmit('admin\r')
        # rtr.receive('sysadmin-vm.*')
        # rtr.execute('terminal length 0')

        for slot in r1_IMS:
            log.info('entering proc to reload ' % slot)
            rtr1.transmit('admin\r')
            device.receive(r'#', timeout=30)
            log.info('reloading %s node' % slot)
            cmd = 'hw-module location %s reload force noprompt' % slot
            rtr1.transmit(cmd)
            # rtr1.receive(r'\[no,yes\]', timeout=30)
            # rtr1.transmit('yes\r')
            rtr1.receive(r'#', timeout=30)
            rtr1.transmit('exit\r')
        for slot in r2_IMS:
            log.info('entering proc to reload ' % slot)
            rtr2.transmit('admin\r')
            device.receive(r'#', timeout=30)
            log.info('reloading %s node' % slot)
            cmd = 'hw-module location %s reload force noprompt' % slot
            rtr2.transmit(cmd)
            # rtr2.receive(r'\[no,yes\]', timeout=30)
            # rtr2.transmit('yes\r')
            rtr2.receive(r'#', timeout=30)
            rtr2.transmit('exit\r')

        for slot in r1_IMS :
            result = Verifylc(rtr1, lc=slot)
            if result != True:
                log.info("LC is not up")
                # self.failed()
                pdb.set_trace()

        for slot in r2_IMS :
            result = Verifylc(rtr2, lc=slot)
            if result != True:
                log.info("LC is not up")
                # self.failed()
                pdb.set_trace()

    @aetest.cleanup
    def clean_this_tc(self):
        """ Testcase cleanup section """
        log.info("No Changes were made in setup section. \
        		Hence clean up is not required")

###########################################################################################


class TestPe(aetest.Testcase):
    '''
    TAG_MAP:
       title: ContinuousLcReload
       descr: This test case covers Continuous LC Reload.
       platform: NCS5500
       min-sw-ver: 6.1.0
       test-phase: dev-test
       modular-pkg: fretta-platform
       test-type: functionality
       test-component: ['coherent']
       sw-component: fretta-coherent
       topology: tgen-fretta-fretta-tgen
       tgn-type: spirent
       link-type: 100G
       customer: all
       cdets-attribute:  auto-fwd-ip
    '''
    execution_group = 'ipv4'

    """ This is user Testcases section """

    @aetest.setup
    def prepare_for_subtest(self):
        """ Testcase Setup section """
        log.info(banner(" Aetest Testcase Execution "))

    @aetest.test
    def pe_reload(self):
        # embed()
        testCaseName = "Scale_Stress1"
        global g_topo_data, g_test_data
        global GV
        rtr1_name = g_topo_data['R1']
        rtr1 = routers[rtr1_name]
        rtr1.execute("terminal length 500")
        rtr1.execute("terminal width 500")
        rtr2_name = g_topo_data['R2']
        rtr2 = routers[rtr2_name]
        rtr2.execute("terminal length 500")
        rtr2.execute("terminal width 500")

        rtr1.transmit('admin\r')
        rtr1.transmit('hw-module location {} shutdown force'.format(r1_slot))
        rtr1.receive(r'\[no,yes\]', timeout=30)
        rtr1.transmit('yes\r')
        # rtr1.adminexec('hw-module location {} reload force noprompt'.format(r1_PE1_slot))
        log.info('entering proc to reload %s'%r1_PE1_slot)
        #rtr1.transmit('admin\r')
        device.receive(r'#', timeout=30)
        log.info('reloading %s node' % r1_PE1_slot)
        cmd = 'hw-module location %s reload force noprompt' % r1_PE1_slot
        rtr1.transmit(cmd)
        # rtr1.receive(r'\[no,yes\]', timeout=30)
        # rtr1.transmit('yes\r')
        rtr1.receive(r'#', timeout=30)
        rtr1.transmit('exit\r')

        result = Verifylc(rtr1, lc=r1_PE1_slot)
        if result != True:
            log.info("LC is not up")
            # self.failed()
            pdb.set_trace()

        for slot in r2_IMS:
            result = Verifylc(rtr2, lc=slot + '/CPU0')
            if result != True:
                log.info("LC is not up")
                # self.failed()
                pdb.set_trace()
        cmds_r1 = []
        for int_list in PE1_config:
            cmds_r1 = cmds_r1 + ['interface {}'.format(int_list[0]),
                                 'no shut',
                                 'ipv4 add {} 255.255.255.0'.format(int_list[1])]
        rtr1.config(cmds_r1)

        for ip in r1_pe1_ping_ip:
            result = rtr1.execute("ping %s" % ip)
            match = re.search(r'Success rate is (?P<rate>\d+) percent', result)
            success_rate = match.group('rate')
            log.info('Ping {} with success rate of {}%'.format(ip, success_rate, ))
        log.info("Pinging on router 2")
        for ip in r2_pe2_ping_ip:
            result = rtr2.execute("ping %s" % ip)
            match = re.search(r'Success rate is (?P<rate>\d+) percent', result)
            success_rate = match.group('rate')
            log.info('Ping {} with success rate of {}%'.format(ip, success_rate, ))


    @aetest.cleanup
    def clean_this_tc(self):
        """ Testcase cleanup section """
        log.info("No Changes were made in setup section. \
        		Hence clean up is not required")


###########################################################################################

class ProcessRestart(aetest.Testcase):
    '''
    TAG_MAP:
       title: ProcessRestart
       descr: This test case covers Process Restart.
       platform: NCS5500
       min-sw-ver: 6.1.0
       test-phase: dev-test
       modular-pkg: fretta-platform
       test-type: functionality
       test-component: ['coherent']
       sw-component: fretta-coherent
       topology: tgen-fretta-fretta-tgen
       tgn-type: spirent
       link-type: 100G
       customer: all
       cdets-attribute:  auto-fwd-ip
    '''
    execution_group = 'ipv4' 

    """ This is user Testcases section """
    @aetest.setup
    def prepare_for_subtest(self):
        """ Testcase Setup section """
        log.info(banner(" Aetest Testcase Execution "))

    @aetest.test
    def process_restart(self):
        testCaseName = "Scale_Stress1"
        global g_topo_data, g_test_data
        global GV

        rtr1_name = g_topo_data['R1']
        rtr1 = routers[rtr1_name]
        rtr1.execute("terminal length 500")
        rtr1.execute("terminal width 500")

        rtr2_name = g_topo_data['R2']
        rtr2 = routers[rtr2_name]
        rtr2.execute("terminal length 500")
        rtr2.execute("terminal width 500")

        for proces in r1_process :
            rtr1.execute("process restart {}".format(proces))
        for proces in r2_process :
            rtr2.execute("process restart {}".format(proces))

        time.sleep(360)
        for proces in r1_process:
            output = rtr1.execute("show processes {} | include Process state:".format(proces))
            if output.count("Run") == 1:
                logging.info("Process {} in UP".format(proces))
            else:
                self.failed("Process {} is not UP in 6mins".format(proces))

        for proces in r2_process:
            output = rtr2.execute("show processes {} | include Process state:".format(proces))
            if output.count("Run") == 1:
                logging.info("Process {} in UP".format(proces))
            else:
                self.failed("Process {} is not UP in 6mins".format(proces))

        for ip in r1_pe1_ping_ip:
            result = rtr1.execute("ping %s" % ip)
            match = re.search(r'Success rate is (?P<rate>\d+) percent', result)
            success_rate = match.group('rate')
            log.info('Ping {} with success rate of {}%'.format(ip, success_rate, ))
        log.info("Pinging on router 2")
        for ip in r2_pe2_ping_ip:
            result = rtr2.execute("ping %s" % ip)
            match = re.search(r'Success rate is (?P<rate>\d+) percent', result)
            success_rate = match.group('rate')
            log.info('Ping {} with success rate of {}%'.format(ip, success_rate, ))
       
    @aetest.cleanup
    def clean_this_tc(self):
        """ Testcase cleanup section """
        log.info("No Changes were made in setup section. \
        		Hence clean up is not required")     		

##################################################################

        
########################################################################
####                       COMMON CLEANUP SECTION                    ###
########################################################################


class common_cleanup(aetest.CommonCleanup):

    @aetest.subsection
    def common_clean(self):
        get_test_topo(self.script_args)
        global g_topo_data
        global GV
        #g_test_data = get_test_data_from_yaml(self.script_args['test_data_file'])

        self.script_args['testStep']=1
        check_result=1
        log.info('No Clean up is required to maintain its state')
        
      #  rtr1_name=g_topo_data['R1']
      #  rtr2_name=g_topo_data['R2']
        
      #  global GV
      # uut1 = GV['uut1']
      #  uut2 = GV['uut2']
        
       # Startup_Config = self.script_args['Startup_Conf']
        #for fretta_rtr in [rtr1_name,rtr2_name]:
        #    log.info('applying configuration')
        #    cmd='load ' + Startup_Config + '\r'
        #    routers[fretta_rtr].transmit('configure terminal\r')
        #    routers[fretta_rtr].receive(r'#',timeout=20)
        #    routers[fretta_rtr].transmit('commit replace\r')
        #    routers[fretta_rtr].receive(r':',timeout=20)
        #    routers[fretta_rtr].transmit('yes\r')
        #    routers[fretta_rtr].receive(r'#',timeout=20)
        #    routers[fretta_rtr].transmit(cmd)
        #    routers[fretta_rtr].receive(r'#',timeout=20)
        #    routers[fretta_rtr].transmit('commit\r')
        #    routers[fretta_rtr].receive(r'#',timeout=20)
        #    routers[fretta_rtr].transmit('exit\r') 
        #    output=routers[fretta_rtr].receive_buffer()

        #    if re.search('Failed to commit one or more configuration items', output):
        #        raise Exception('configuration apply failed')
        #        self.failed()
        #    else:
        #        log.info('configuration applied successfully')
            
         
        
        ##############################################################
        #clean up the session, release the ports reserved and cleanup the dbfile
        ##############################################################
        
      #  cleanup_sta = sth.cleanup_session (port_handle= GV['port_handle'],clean_dbfile= '1')
      #  status = cleanup_sta['status']
      #  if (status == '0') :
	  #      log.info("run sth.cleanup_session failed")
	  #      self.failed()
      #  else:
	  #      log.info("***** run sth.cleanup_session successfully")


if __name__ == '__main__':
    aetest.main()

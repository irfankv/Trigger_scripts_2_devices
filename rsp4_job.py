# To run the job:
# easypy -tf $VIRTUAL_ENV/ats/examples/tests/connection_example_conf.yaml
#            $VIRTUAL_ENV/ats/examples/jobs/connection_example.py
# Description: This example uses a sample testbed, connects to a device,
#              and executes some commands
import os
from ats.easypy.easypy import run

def main():
    # Find the examples/tests directory where the test script exists
    #traff_type value can be 100,200,150 or 100_200 or 100_150 or 150_200,100_150_200
    test_path = (os.path.dirname(os.path.abspath(__file__))
                 .replace('/jobs', '/tests'))

    run(testscript='/ws/ikyalnoo-bgl/Cafy10_Production/xProjects/Fretta_pmfc_Scripts/rsp4_dpfga/rsp4_main.py',\
        run_ids=['common_setup','ping_testcase','common_cleanup'],\
        #run_ids=['common_setup','Scale_Stress27$','Scale_Stress28$','Scale_Stress35$','Scale_Stress36$','Scale_Stress39$','Scale_Stress40$','Scale_Stress41$','Scale_Stress42$','Scale_Stress43$','Scale_Stress44$','common_cleanup'],\
        #skip_ids=['Scale_Stress13','Scale_Stress18'],\
        R1='rsp4',\
        R1a = 'rsp4-a',\
        R2a = 'fretta-a',\
        R2 = "fretta",
        R1_interface = [""],
        R2_interface=[""],
        config1 = [['TenGigE0/4/0/2', '12.12.12.2'],
               ],
        config2=[['TenGigE0/7/0/10/2', '12.12.12.1'],
                 ],
        r1_ping_ip=["12.12.12.1"],
        r2_ping_ip = ["12.12.12.2"],
        r1_IMS=["0/4", "0/4"],
        r2_IMS = ["0/6", "0/10", "0/11"],
        r1_PE1_slot = "0/6",
        r1_slot = "0/5",
        r2_slot =" ",
        PE1_config=[['gig0/6/0/12', '15.15.15.1']],
        r1_pe1_ping_ip=["15.15.15.2", "13.13.13.2", "14.14.14.2"],
        r2_pe2_ping_ip = ["15.15.15.1", "13.13.13.1", "14.14.14.1"],
        r1_process=["eth_intf_ea", "optics_driver", ],
        r2_process = ["eth_intf_ea", "optics_driver"],
        )
        
'''
IntfList : list number of interfaces to be a part of trigger
TraffPortList : list number of interfaces for which you need to verify traffic recovery post trigger
IterCnt : Total iteration count of each trigger inside test case. After each iteration the validation part takes place
RepeatCnt : Total repeat count of the trigger prior to validation. For continuous execution.
ProcessList : List of process names for Process restart and crash scenarios
ProcessLCLocation : LC Location of the processes running for process restart/crash scenarios
LeakLCLocation : LC location of the process to check for memory leak
ReloadLCLocation : LC location for LC reload scenarions
MemLeakLCProcessList : List of process names running on LC to verify memory leaks post triggers
MemLeakRPProcessList : List of process names running on RP to verify memory leaks post triggers
RPProcess : "on" if you are giving any RP process as input else "off"
ShowCmdList : List of show commands to be executed and verify memory leaks or crash
CliList : Give each configuration as a single statement with in quotes with \n inserted for next line of CLI execution
ConvergTime : The amount of time to wait before verifying traffic after any trigger
Traffic : Whether the traffic validation is required or not. If yes then given option as "on" and keep the traffic running in the background before starting the script
LcList : List of LC locations to be used for reload test cases.
'''



       
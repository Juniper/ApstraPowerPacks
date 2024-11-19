import os
import time
import urllib.parse
from string import Template

import pysnow
import requests
import urllib3
import yaml
from aos.client import AosClient
from python_terraform import *

setup = {}


# Do Terraform Initialize
def terraform_init():
    t = Terraform()
    t.init()


# Do Terraform Apply
def terraform_apply():
    t = Terraform()
    t.apply(skip_plan=True)


# Load the yaml file with the config
def load_setup():
    global setup
    with open('setup.yaml', "r") as s:
        setup = yaml.safe_load(s)


# Save the yaml
def save_setup():
    global setup
    with open('setup.yaml', "w") as s:
        yaml.safe_dump(setup, s)


# Set up the apstra client
def get_apstra_client():
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    aos_ip = os.environ.get('APSTRA_URL').split("https://")[1]
    aos_port = os.environ.get('APSTRA_PORT')
    aos_user = os.environ.get('APSTRA_USER')
    aos_pw = os.environ.get('APSTRA_PASS')
    session = requests.Session()
    session.verify = True
    aos_client = AosClient(protocol="https", host=aos_ip, port=int(aos_port), session=session)
    aos_client.auth.login(aos_user, aos_pw)
    return aos_client

# Print the anomalies
def print_anomalies(ano):
    for a in ano:
        print(a['identity'].get('probe_label'))
        print(a['identity']['stage_name'])


# Get all anomalies
def get_anomalies(bp_id):
    ano = aos.rest.json_resp_get("api/blueprints/" + bp_id + "/anomalies")
    return ano['items']


# Is the blueprint locked?
def is_locked(bp_id):
    ls = aos.rest.json_resp_get("api/blueprints/" + bp_id + "/lock-status")
    return ls.get("lock_status") == "locked"


# Reset the values to the initial values
def reset_original(init=False):
    global setup
    with open("configlet_dcqcn.tf.template") as r:
        src = Template(r.read())
        with open("configlet_dcqcn.tf", "w") as w:
            w.write(src.safe_substitute(fill_low=str(setup['initial']['fill_level_low']),
                                        fill_high=str(setup['initial']['fill_level_high']),
                                        drop_probability_low=str(setup['initial']['drop_probability_low']),
                                        drop_probability_high=str(setup['initial']['drop_probability_high']),
                                        bp_name=str(setup['apstra']['blueprint_name']),
                                        auto_commit=str(auto_commit)
                                        )
                    )
    setup['drop_probability_low'] = setup['initial']['drop_probability_low']
    setup['drop_probability_high'] = setup['initial']['drop_probability_high']
    setup['fill_level_low'] = setup['initial']['fill_level_low']
    setup['fill_level_high'] = setup['initial']['fill_level_high']
    setup['low_limit'] = setup['initial']['low_limit']
    setup['high_limit'] = setup['initial']['high_limit']
    if init:
        terraform_init()
    terraform_apply()
    terraform_apply()
    save_setup()


# Decide which direction to move
# If pfcs or tail drop anomalies exist move left (return "left")
# If no pfcs or tail drop anomalies exist, but ecn anomalies exist, move right (return "right")
# If no anomalies exist, stay put (return "none").
def get_direction(anomalies):
    ecn = 0
    pfc = 0
    drops = 0
    direction = "none"
    message = ""
    # print(setup['pfc_probe_name'], setup['ecn_probe_name'], setup['drop_probe_name'])
    for a in anomalies:
        # print (a)
        if a['identity'].get('probe_label') == setup['ecn_probe_name']:
            print("Packets Marked ECN.")
            # print(a['id'])
            ecn = ecn + 1
        if a['identity'].get('probe_label') == setup['pfc_probe_name']:
            # if a['identity']['stage_name'] == "Range":
            print("Packets marked PFC.")
            # print(a['id'])
            pfc = pfc + 1
        if a['identity'].get('probe_label') == setup['drop_probe_name']:
            print("Tail Drops.")
            # print(a['id'])
            drops = drops + 1
    message = "%s \n Number of ECN Anomalies %d \n Number of PFC Anomalies %d \n Number of Tail Drop Anomalies %d \n" % (
    message, ecn, pfc, drops)
    if pfc or drops:
        direction = "left"
    if not pfc and not drops and ecn:
        direction = "right"
    return direction, message


def print_usage():
    print("Usage : python3 ecn_monitor.py --restore-original to restore the original fill level "
          "and drop probability. \n python3 ecn_monitor.py to start the monitor.")


def monitor_loop():
    global auto_commit
    global edge_detect

    edge_detect_counter = setup['reset_edge_detection_time_seconds']

    edge_detect_start = False
    edge_detect_threshold = 1
    left_step_low = setup['window_left_shift_quantum_low']
    left_step_high = setup['window_left_shift_quantum_high']
    right_step_low = setup['window_right_shift_quantum_low']
    right_step_high = setup['window_right_shift_quantum_high']
    left_step = left_step_high
    right_step = right_step_high
    wait_cycles = 1
    while True:
        go_left = False
        go_right = False
        direction = "none"
        work_notes = ""

        # In case there are no probes or no apstra, this is for testing
        if user_input:
            pfc = input("Any pfc packet(y/n)") == 'y'
            dropped_packets = input("Any dropped packets (y/n)") == 'y'
            ecn_marked_packets = input("ECN marked_packets (y/n)") == 'y'
            if pfc > 1 or dropped_packets:
                direction = "left"
            if not (pfc > 1) and not dropped_packets and ecn_marked_packets:
                direction = "right"
        else:
            ano = get_anomalies(bp_id)
            direction, work_notes = get_direction(ano)
            print("anomalies pulled")
            # print(datetime.datetime.now())

        if direction == "left":
            go_left = True
        if direction == "right":
            go_right = True
        if setup['fill_level_high'] == setup['high_limit'] and go_right == True:
            print("Reached the high limit")
            go_right = False
        if setup['fill_level_low'] == setup['low_limit'] and go_left == True:
            print("Reached the low limit")
            go_left = False

        if not go_left and not go_right and edge_detect_start:
            # This will be the wait cycle from the previous loop, so if we have been waiting here long, we might as well call this stable
            # and save some time
            edge_detect_counter = edge_detect_counter - setup['wait_time_seconds'] * wait_cycles
        else:
            edge_detect_counter = setup['reset_edge_detection_time_seconds']

        if edge_detect_counter < 0:
            edge_detect_counter = setup['reset_edge_detection_time_seconds']
            edge_detect_start = False
            edge_detect_threshold = 1
            edge_detect = False
            setup['low_limit'] = setup['initial']['low_limit']
            setup['high_limit'] = setup['initial']['high_limit']
            left_step_low = setup['window_left_shift_quantum_low']
            left_step_high = setup['window_left_shift_quantum_high']
            right_step_low = setup['window_right_shift_quantum_low']
            right_step_high = setup['window_right_shift_quantum_high']
            work_notes = "ECN Drop Profile is Kmin = %s%%  , Kmax = %s%% \n New stable position found. Tuning will be terminated." % (
            setup['fill_level_low'], setup['fill_level_high'])
            update_ticket(work_notes)
            if setup.get('stop_on_reset'):
                return

        wait_cycles = 1

        if go_left:
            print("Moving Window Left")
            work_notes = " \n %s \n Configuring DCQCN parameters to lower values \n " % (work_notes)
            # print("Time before config push")
            # print(datetime.datetime.now())
            with open("configlet_dcqcn.tf.template") as r:
                src = Template(r.read())
                with open("configlet_dcqcn.tf", "w") as w:
                    setup['fill_level_low'] = setup['fill_level_low'] - left_step
                    setup['fill_level_high'] = setup['fill_level_high'] - left_step
                    if setup['fill_level_low'] < setup['low_limit']:
                        setup['fill_level_low'] = setup['low_limit']

                    w.write(src.safe_substitute(fill_low=str(setup['fill_level_low']),
                                                fill_high=str(setup['fill_level_high']),
                                                drop_probability_low=str(setup['drop_probability_low']),
                                                drop_probability_high=str(setup['drop_probability_high']),
                                                bp_name=str(setup['apstra']['blueprint_name']),
                                                auto_commit=str(auto_commit)
                                                )
                            )
            terraform_apply()
            terraform_apply()
            if edge_detect_start:
                if edge_detect:
                    print("Edge Detection is on, so a new high limit is set.")
                    work_notes = (work_notes + "\n Edge Detection is on, so a new high limit is set. "
                                  + str(setup['fill_level_high']) + "\n")
                else:
                    work_notes = work_notes + "\n We have started fine-tuning DCQCN Drop Profile.\n"
                    print("We have started fine-tuning DCQCN Drop Profile")
                    edge_detect = True
                    # Wait extra because we expect this to be the right spot
                    # wait_cycles = wait_cycles + 2

                setup['high_limit'] = setup['fill_level_high']
                wait_cycles = wait_cycles + 2

            save_setup()
            # print("Time after config push")
            # print(datetime.datetime.now())
            print(setup['fill_level_low'], setup['fill_level_high'])
            # print("Wait %d seconds" % setup['wait_time_seconds'])
            wait_cycles = wait_cycles + 1

        if go_right:
            print("Moving Window Right")
            #  print("Time before config push")
            #  print(datetime.datetime.now())
            work_notes = " \n %s \n Configuring dcqn parameters to higher values \n " % (work_notes)
            with open("configlet_dcqcn.tf.template") as r:
                src = Template(r.read())
                with open("configlet_dcqcn.tf", "w") as w:
                    setup['fill_level_low'] = setup['fill_level_low'] + right_step
                    setup['fill_level_high'] = setup['fill_level_high'] + right_step
                    if setup['fill_level_high'] > setup['high_limit']:
                        setup['fill_level_high'] = setup['high_limit']
                    w.write(src.safe_substitute(fill_low=str(setup['fill_level_low']),
                                                fill_high=str(setup['fill_level_high']),
                                                drop_probability_low=str(setup['drop_probability_low']),
                                                drop_probability_high=str(setup['drop_probability_high']),
                                                bp_name=str(setup['apstra']['blueprint_name']),
                                                auto_commit=str(auto_commit)
                                                )
                            )
            terraform_apply()
            terraform_apply()
            save_setup()
            #   print("Time after config push")
            #   print(datetime.datetime.now())
            print(setup['fill_level_low'], setup['fill_level_high'])
            # print("Pushed Config.")
            if not edge_detect_start:
                edge_detect_threshold = edge_detect_threshold - 1
                if edge_detect_threshold == 0:
                    print("Edge Detection will be started. Next Left Move will start detecting edges.")
                    work_notes = work_notes + "Starting Edge Detection for optimal DCQCN profile."
                    edge_detect_start = True
                    right_step = right_step_low
                    left_step = left_step_low
                wait_cycles = wait_cycles + 1

        work_notes = "%s.\nECN Drop Profile is Kmin = %s%%  , Kmax = %s%% " % (
            work_notes, setup['fill_level_low'], setup['fill_level_high'])

        if is_locked(bp_id) and not auto_commit:
            work_notes = work_notes + "\n The Configlet needs to be committed."

        if direction != "none":
            update_ticket(work_notes)

        while is_locked(bp_id) and not auto_commit:
            print("Blueprint is locked, Wait %d seconds" % setup['wait_time_seconds'])
            time.sleep(setup['wait_time_seconds'])
            auto_commit = check_auto_commit()
        print("Bottom of loop Wait %d seconds" % (setup['wait_time_seconds'] * wait_cycles))
        print(edge_detect_counter)
        print(setup['fill_level_low'], setup['fill_level_high'])
        time.sleep(setup['wait_time_seconds'] * wait_cycles)


def setup_ticket():
    global snow
    global incident

    ticket = setup['snow'].get('monitor_ticket_id')
    make_ticket = not ticket
    print(ticket)
    if ticket:
        # Query for incidents with state 1
        response = incident.get(query={'number': ticket}, sysparm_display_value=True)
        if response.all().count == 0:
            make_ticket = True
    if make_ticket:
        print("making ticket")
        response = incident.create(payload={
            'short_description': 'Congestion Noticed by ECN Monitor',
            'description': ''
        })
        setup['snow']['monitor_ticket_id'] = response.all()[0]['number']['value']
        save_setup()


def update_ticket(work_notes):
    incident.update({'number': setup['snow']['monitor_ticket_id']}, {'work_notes': work_notes})


def check_auto_commit():
    try:
        ps = aos.design.property_sets.get_property_set(ps_name="ECN Monitor")
        return ps.get("values").get("auto_commit")
    except Exception as e:
        return True


def check_pause_detect():
    try:
        ps = aos.design.property_sets.get_property_set(ps_name="ECN Monitor")
        return ps.get("values").get("pause_detect")
    except Exception as e:
        return True


user_input = False
read_only = False
edge_detect = False

load_setup()
aos = get_apstra_client()
auto_commit = check_auto_commit()

bp_id = aos.blueprint.get_id_by_name(setup['apstra']['blueprint_name']).id
if len(sys.argv) > 1:
    if sys.argv[1] == "--restore-original":
        reset_original()
        quit()
    if sys.argv[1] == "--init":
        reset_original(True)
        quit()
    elif sys.argv[1] == "--h":
        print_usage()
        quit()
    elif sys.argv[1] == "--user-input":
        user_input = True
    elif sys.argv[1] == "--read-only":
        read_only = True
    else:
        print("unknown option(s) %s" % " ".join(sys.argv[1:]))
        print_usage()
        quit()

if not setup.get('fill_level_low'):
    reset_original()

snow = pysnow.Client(instance=setup['snow']['instance'], user=setup['snow']['user'], password=os.environ.get("SNOW_PASS"))
# Define a resource, here we'll use the incident table API
incident = snow.resource(api_path='/table/incident')
incident.parameters.display_value = "all"

setup_ticket()

monitor_loop()
# Create client object

# Iterate over the result and print out `sys_id` of the matching records.
# for record in response.all():
#     print(record['sys_id'])
# if not setup.get('monitor_ticket_id'):
#

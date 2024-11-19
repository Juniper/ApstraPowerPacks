import os
import pprint
import time

# import pprint
import pysnow
import requests
import urllib3
import yaml
from aos.aos import AosAPIError
from aos.client import AosClient

setup = {}
tickets = {}
devices = {}

# Load the yaml file with the config
def load_setup():
    global setup
    with open('setup.yaml', "r") as s:
        setup = yaml.safe_load(s)


# Save Tickets into the Property Set
def save_tickets_ps(ticks):
    data = []
    for t in ticks.keys():
        data.append(ticks[t] | {'anomaly_id': t})
    values = {'tickets_info': data}
    try:
        ps = aos.design.property_sets.get_property_set(ps_name=ps_tickets)
        aos.rest.patch(uri=f"/api/property-sets/{ps['id']}", data={'label': ps_tickets, 'values': values})
    except AosAPIError as e:
        ps = aos.design.property_sets.add_property_set([{'label': ps_tickets, 'values': values}])
    return

#Find (or create) property set for the device CIS
def save_devices_ps(devs):
    values = {'device_sys_ids': devs}
    try:
        ps = aos.design.property_sets.get_property_set(ps_name=ps_devices)
        aos.rest.put(uri=f"/api/property-sets/{ps['id']}", data={'label': ps_devices, 'values': values})
    except AosAPIError as e:
        ps = aos.design.property_sets.add_property_set([{'label': ps_devices, 'values': values}])
    return

#Check if there's a property set for device CIS. If none exists, go get CIs (or make them) in ServiceNow
def load_devices_ps():
    global devices
    try:
        ps = aos.design.property_sets.get_property_set(ps_name=ps_devices)
        devices = ps.get("values").get("devices_info")
    except AosAPIError as e:
        devices = make_managed_device_cis()
        ps = aos.design.property_sets.add_property_set([{'label': ps_devices, 'values': {'devices_info': devices}}])


# Load Tickets from Property Set
def load_tickets_ps():
    global tickets
    try:
        ps = aos.design.property_sets.get_property_set(ps_name=ps_tickets)
    except AosAPIError as e:
        ps = aos.design.property_sets.add_property_set([{'label': ps_tickets, 'values': {'tickets_info': []}}])

    ticks = ps.get("values").get("tickets_info")
    for t in ticks:
        tickets[t['anomaly_id']] = t
    return


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


# Get all anomalies
def get_anomalies(bp_id):
    anos = aos.rest.json_resp_get("api/blueprints/" + bp_id + "/anomalies")
    return anos['items']


def pretty_print_anomaly(ano):
    s = "Error Type : %s\n" % (ano.get('anomaly_type'))
    role = ano.get('role')
    if role:
        s = "%s \n Role : %s" % (s, role)
    s = "%s \n Severity : %s" % (s, ano['severity'])

    expected = ano['expected'].get('value')
    if not expected:
        expected = ano['expected']

    actual = ano['actual'].get('value')
    if not actual:
        actual = ano['actual']
    for k in ano['identity'].keys():
        s = "%s \n %s : %s " % (s, k, ano['identity'][k])
    if expected and actual:
        s = "%s \nExpected : %s \nActual : %s \n " % (s, expected, actual)
    return s


# Get values from the management property set
def get_control():
    ps = aos.design.property_sets.get_property_set(ps_name=ps_manager)
    if ps.get('values'):
        bps = ps['values'].get("blueprints")
        bp_ids = ps['values'].get("blueprint_ids")
        if bps:
            return ps['values'].get('pause'), [aos.blueprint.get_id_by_name(b.strip()).id for b in bps.split(",")]
        return ps['values'].get('pause'), bp_ids
    return False, []


# Loop through and monitor the environment
def monitor_loop():
    global tickets
    while True:
        t1 = tickets.copy()
        pause, bps = get_control()
        if pause:
            print("Pause Ticket Automation")
            time.sleep(setup['wait_time_seconds'])
            continue

        for bp_id in bps:
            bp = aos.blueprint.get_bp(bp_id.strip())['label']
            ano = get_anomalies(bp_id)
            print(len(ano))
            for a in ano:
                # pprint.pprint(a)
                # continue

                if not tickets.get(a['id']):
                    tick_id = make_ticket(devices[a['identity']['system_id']], a)
                    tickets[a['id']] = {'tick_id': tick_id, 'bp_name': bp, 'bp_id': bp_id}
                    # t_ci = snow.resource(api_path='/table/task_ci')
                    # t_ci.create({'ci_item':devices[a['identity']['system_id']], 'task':tick_id})
                else:
                    print("Ticket for anomaly already exists : %s" % (tickets[a['id']]))
                    t1.pop(a['id'], None)
            # break
        for k in t1.keys():
            tickets.pop(k)
        close_tickets(t1)
        save_tickets_ps(tickets)
        time.sleep(setup['wait_time_seconds'])
        # break


def close_tickets(tickets):
    for t in tickets.values():
        resolve_ticket(t['tick_id'])


def resolve_ticket(t):
    print(f"resolving ticket {t}")
    incident.update({'number': t}, {'work_notes': "Anomaly resolved in Apstra."})
    response = incident.update({'number': t},
                               {"close_code": "Resolved By Caller", "state": "6", "caller_id": "apstra_user",
                                "close_notes": "Closed by API"})
    # print(response)


def make_ticket(ci_id, desc):
    global snow
    global incident

    # print("making ticket")
    # print(a_id, desc)
    s = pretty_print_anomaly(desc)
    response = incident.create(payload={
        'short_description': f'Apstra Network Anomaly - {str(desc.get("anomaly_type")).title()} Error ',
        'caller_id': setup['snow']['caller_id'],
        'cmdb_ci':ci_id
    })
    tick_id = response.all()[0]['number']['value']
    # print(tick_id)
    incident.update({'number': tick_id}, {'work_notes': s})
    return tick_id


def make_cmdb_ci_dc(name):
    cmdb = snow.resource(api_path='/table/cmdb_ci')
    cmdb.create(payload={'name': name})


def make_managed_device_cis():
    # devs = aos.rest.json_resp_post(uri="api/blueprints/" + bp_id + "/qe", data={"query":"match(node('system', name='system', deploy_mode='deploy', role=is_in(['leaf', 'access', 'spine','superspine'])))"})['items']
    devs = aos.rest.json_resp_get(uri="api/systems/")['items']
    cmdb = snow.resource(api_path='/table/cmdb_ci')

    devices = {}

    for d in devs:
       # pprint.pprint(d)
        r = cmdb.get(query={'name':d['status']['hostname']}, stream=True).first_or_none()
        if r:
            devices[d['facts']['serial_number']] = r['sys_id']
        else:
            payload = {'name': d['status']['hostname'], "sys_class_name": "cmdb_ci_ip_switch"}
            payload['ip_address'] = d['facts']['mgmt_ipaddr']
            payload['mac_address'] = d['facts']['mgmt_macaddr']
            payload['manufacturer'] = d['facts']['vendor']
            payload['model_number'] = d['facts']['hw_model']
            payload['serial_number'] = d['facts']['serial_number']

            r = cmdb.create(payload=payload)
            #breakpoint()
            devices[d['facts']['serial_number']] = r.all()[0]['sys_id']

    return devices

load_setup()
aos = get_apstra_client()
snow = pysnow.Client(instance=setup['snow']['instance'], user=setup['snow']['user'],
                     password=os.environ.get('SNOW_PASS'))
ps_manager = setup['management_property_set']
ps_tickets = setup['tickets_property_set']
ps_devices = setup['devices_property_set']

incident = snow.resource(api_path='/table/incident')
incident.parameters.display_value = "all"
load_tickets_ps()
cmdb = snow.resource(api_path='/table/cmdb_ci')
load_devices_ps()

monitor_loop()

# breakpoint()
# print(get_managed_devices("evpn-vex-virtual"))

# rs = cmdb.get(stream=True)
# rs = cmdb.get(query={"sys_class_name": "cmdb_ci_ip_switch"}, stream=True)
# for r in rs.all():
#     pprint.pprint(r)
#   a[r['sys_class_name']]=True


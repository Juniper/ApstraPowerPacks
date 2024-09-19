import time
from pathlib import Path

# import pprint
import pysnow
import urllib3
import yaml
from aos.aos import AosAPIError
from aos.client import AosClient

setup = {}
tickets = {}


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
        aos.rest.put(uri=f"/api/property-sets/{ps['id']}", data={'label': ps_tickets, 'values': values})
    except AosAPIError as e:
        ps = aos.design.property_sets.add_property_set([{'label': ps_tickets, 'values': values}])
    return


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
    global setup
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    aos_ip = setup['apstra']['aos_ip']
    aos_port = setup['apstra']['aos_port']
    aos_user = setup['apstra']['aos_user']
    aos_pw = setup['apstra']['aos_pass']
    aos_client = AosClient(protocol="https", host=aos_ip, port=aos_port)
    aos_client.auth.login(aos_user, aos_pw)
    return aos_client


# Get all anomalies
def get_anomalies(bp_id):
    anos = aos.rest.json_resp_get("api/blueprints/" + bp_id + "/anomalies")
    return anos['items']


def pretty_print_anomaly(ano):
    s = "Error Type : %s\n" % (ano.pop('anomaly_type'))
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
        if bps:
            return ps['values'].get('pause'), bps.split(",")
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

        for bp in bps:
            bp_id = aos.blueprint.get_id_by_name(bp.strip()).id
            ano = get_anomalies(bp_id)
            print(len(ano))
            for a in ano:
                # pprint.pprint(a)
                # continue

                if not tickets.get(a['id']):
                    s = pretty_print_anomaly(a)
                    tick_id = make_ticket(a['id'], s)
                    tickets[a['id']] = {'tick_id': tick_id, 'bp_name': bp, 'bp_id': bp_id}
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
    print (f"resolving ticket {t}")
    incident.update({'number': t}, {'work_notes': "Anomaly resolved in Apstra."})
    response = incident.update({'number': t},
                               {"close_code": "Resolved By Caller", "state": "6", "caller_id": "apstra_user",
                                "close_notes": "Closed by API"})
    # print(response)


def make_ticket(a_id, desc):
    global snow
    global incident

    # print("making ticket")
    # print(a_id, desc)
    response = incident.create(payload={
        'short_description': 'Apstra Network Anomaly',
        'caller_id': setup['snow']['caller_id']
    })
    tick_id = response.all()[0]['number']['value']
    # print(tick_id)
    incident.update({'number': tick_id}, {'work_notes': desc})
    return tick_id


load_setup()
aos = get_apstra_client()
snow = pysnow.Client(instance=setup['snow']['instance'], user=setup['snow']['user'], password=setup['snow']['password'])
ps_manager = setup['management_property_set']
ps_tickets = setup['tickets_property_set']

incident = snow.resource(api_path='/table/incident')
incident.parameters.display_value = "all"
load_tickets_ps()
monitor_loop()

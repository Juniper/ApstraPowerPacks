import logging
import os

import pysnow
import sys

sys.path.insert(1, "../PowerPackBase")
from power_pack import PowerPackBase


class SNOWPowerPack(PowerPackBase):
    def __init__(self):
        super().__init__(worker_callback=self.worker, checker_callback=self.get_pause)
        self.tickets = {}
        self.devices_ci_map = {}
        self.devices = {}

        self.snow = pysnow.Client(instance=self.setup['snow']['instance'], user=self.setup['snow']['user'],
                                  password=os.environ.get('SNOW_PASS'))
        self.ps_manager = self.setup['management_property_set']
        self.ps_tickets = self.setup['tickets_property_set']
        self.ps_devices = self.setup['devices_property_set']

        self.incident = self.snow.resource(api_path='/table/incident')
        self.incident.parameters.display_value = "all"
        self.load_tickets_ps()
        self.dev_map = {}
        self.make_devices_map()
        self.load_devices_ps()

        self.bp_ids = self.get_bp_ids()

    def worker(self):
        # pprint.pprint (self.tickets)
        t1 = self.tickets.copy()
        for bp_id in self.bp_ids:
            bp = self.aos_client.get_bp(bp_id.strip())['label']
            ano = self.aos_client.get_anomalies(bp_id)
            # print(len(ano))
            for a in ano:
                if self.ignore_ano(a):
                    #print("ignoring")
                    continue
                if not self.tickets.get(a['id']):
                    tick_id, sys_id = self.make_ticket(self.devices_ci_map[a['identity']['system_id']], a)
                    self.tickets[a['id']] = {'tick_id': tick_id, 'bp_name': bp, 'bp_id': bp_id,
                                             'sys_id': sys_id,
                                             'link': f"{self.snow.base_url}/nav_to.do?uri=incident.do?sys_id={sys_id}",
                                             'anomaly_id': a['id'],
                                             'bp_link': f"{self.aos_client.base_url}/#/blueprints/{bp_id}/active/anomalies"
                                             }
                else:
                    #print("Ticket for anomaly already exists : %s" % (self.tickets[a['id']]))
                    t1.pop(a['id'], None)
            # break
        for k in t1.keys():
            self.tickets.pop(k)
        self.close_tickets(t1)
        self.save_tickets_ps(self.tickets)

    # Get pause value
    def get_pause(self):
        ps = self.aos_client.get_property_set(self.ps_manager)
        if ps.get('values'):
            return ps['values'].get('pause') and str(ps['values'].get('pause')).upper() == "TRUE"
        return False

    # Decide if anomaly needs to be reported
    def ignore_ano(self, a):
        ps = self.aos_client.get_property_set(self.ps_manager)['values']
        a_type = a.get('anomaly_type')
        a_severity = a.get('severity')
        a_device = None
        i = a.get('identity')
        if i:
            a_device = self.dev_map.get(i.get('system_id'))['hostname']

        #print(a_type, a_severity, a_device)

        if a_device in ps.get('ignore_devices'):
            return True
        if a_type in ps.get('ignore_anomalies'):
            return True
        include_only_anomalies = ps.get('include_only_anomalies')
        if include_only_anomalies:
            if not (a_type in include_only_anomalies):
                return True
        include_only_devices = ps.get('include_only_devices')
        if include_only_devices:
            if not(a_device in include_only_devices):
                return True
        include_only_severity = ps.get('include_only_severity')
        if include_only_severity:
            if not(a_severity in include_only_severity):
                return True

        return False

    # Save Tickets into the Property Set
    def save_tickets_ps(self, ticks):
        data = []
        for t in ticks.keys():
            data.append(ticks[t] | {'anomaly_id': t})
        values = {'tickets_info': data}
        try:
            ps = self.aos_client.get_property_set(self.ps_tickets)
            self.aos_client.update_property_set(ps['id'],
                                                {'label': self.ps_tickets, 'values': values})
        except Exception:
            self.aos_client.make_property_set({'label': self.ps_tickets, 'values': values})
        return

    # Find (or create) property set for the device CIS
    def save_devices_ps(self, devs):
        values = {'device_sys_ids': devs}
        try:
            ps = self.aos_client.get_property_set(self.ps_devices)
            self.aos_client.update_property_set(ps['id'], {'label': self.ps_devices, 'values': values})
        except Exception as e:
            logging.exception(e)
            self.aos_client.add_property_set([{'label': self.ps_devices, 'values': values}])
        return

    # Check if there's a property set for device CIS. If none exists, go get CIs (or make them) in ServiceNow
    def load_devices_ps(self):
        try:
            ps = self.aos_client.get_property_set(self.ps_devices)
            self.devices_ci_map = ps.get("values").get("devices_info")
        except Exception as e:
            logging.debug("devices property set not found ")
            self.devices_ci_map = self.make_managed_device_cis()
            self.aos_client.make_property_set(
                {'label': self.ps_devices, 'values': {'devices_info': self.devices_ci_map}})

    # Load Tickets from Property Set
    def load_tickets_ps(self):
        try:
            ps = self.aos_client.get_property_set(self.ps_tickets)
        except Exception as e:
            logging.exception(e)
            ps = self.aos_client.make_property_set(
                {'label': self.ps_tickets, 'values': {'tickets_info': []}})
        ticks = ps.get("values").get("tickets_info")
        for t in ticks:
            self.tickets[t['anomaly_id']] = t
        return

    def pretty_print_anomaly(self, ano):
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

    def get_bp_ids(self):
        ps = self.aos_client.get_property_set(self.ps_manager)
        if ps.get('values'):
            bps = ps['values'].get("blueprints")
            if bps:
                return [self.aos_client.blueprint.get_id_by_name(b.strip()).id for b in bps.split(",")]
            return ps['values'].get("blueprint_ids")
        return []

    def close_tickets(self, tickets):
        for t in tickets.values():
            self.resolve_ticket(t['tick_id'])

    def resolve_ticket(self, t):
        #print(f"resolving ticket {t}")
        self.incident.update({'number': t}, {'work_notes': "Anomaly resolved in Apstra."})
        response = self.incident.update({'number': t},
                                        {"close_code": "Resolved By Caller", "state": "6", "caller_id": "apstra_user",
                                         "close_notes": "Closed by API"})
        # print(response)

    def make_ticket(self, ci_id, desc):
        # print("making ticket")
        # print(a_id, desc)
        s = self.pretty_print_anomaly(desc)

        response = self.incident.create(payload={
            'short_description': f'Apstra Network Anomaly - {str(desc.get("anomaly_type")).title()} Error ',
            'caller_id': self.setup['snow']['caller_id'],
            'cmdb_ci': ci_id
        })

        tick_id = response.all()[0]['number']['value']
        sys_id = response.all()[0]['sys_id']['value']
        # print(tick_id)
        self.incident.update({'number': tick_id}, {'work_notes': s})

        return tick_id, sys_id

    def make_managed_device_cis(self):
        cmdb = self.snow.resource(api_path='/table/cmdb_ci')

        devs = {}
        for d in self.dev_map:
            # pprint.pprint(d)
            r = cmdb.get(query={'name': self.dev_map[d]['hostname']}, stream=True).first_or_none()
            if r:
                devs[d] = r['sys_id']
            else:
                payload = {'name': self.dev_map[d]['hostname'], "sys_class_name": "cmdb_ci_ip_switch",
                           'ip_address': self.dev_map[d]['ip_address'], 'mac_address': self.dev_map[d]['mac_address'],
                           'manufacturer': self.dev_map[d]['manufacturer'], 'model_number': self.dev_map[d]['model_number'],
                           'serial_number': d}

                r = cmdb.create(payload=payload)
                devs[d] = r.all()[0]['sys_id']

        return devs

    def make_devices_map(self):
        devs = self.aos_client.make_api_request("GET", "/api/systems/")['items']
        for d in devs:
            self.dev_map[d['facts']['serial_number']] = {
                "hostname": d["status"]["hostname"],
                "ip_address": d["facts"]["mgmt_ipaddr"],
                "mac_address": d["facts"]["mgmt_macaddr"],
                "manufacturer": d["facts"]["vendor"],
                "model_number": d["facts"]["hw_model"]
            }


if __name__ == '__main__':
    pp = SNOWPowerPack()
    pp.start_threads(blocking=True)

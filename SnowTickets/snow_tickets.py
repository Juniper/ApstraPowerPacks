import os

import pysnow
from aos.aos import AosAPIError

from power_pack import PowerPackBase


class SNOWPowerPack(PowerPackBase):
    def __init__(self):
        super().__init__(worker_callback=self.worker, checker_callback=self.get_pause)
        self.tickets = {}
        self.devices = {}
        self.snow = pysnow.Client(instance=self.setup['snow']['instance'], user=self.setup['snow']['user'],
                                  password=os.environ.get('SNOW_PASS'))
        self.ps_manager = self.setup['management_property_set']
        self.ps_tickets = self.setup['tickets_property_set']
        self.ps_devices = self.setup['devices_property_set']

        self.incident = self.snow.resource(api_path='/table/incident')
        self.incident.parameters.display_value = "all"
        self.load_tickets_ps()
        self.load_devices_ps()
        self.bp_ids = self.get_bp_ids()

    def worker(self):
        # pprint.pprint (self.tickets)
        t1 = self.tickets.copy()
        for bp_id in self.bp_ids:
            bp = self.aos_client.blueprint.get_bp(bp_id.strip())['label']
            ano = self.get_anomalies(bp_id)
            # print(len(ano))
            for a in ano:
                if not self.tickets.get(a['id']):
                    tick_id, sys_id = self.make_ticket(self.devices[a['identity']['system_id']], a)
                    self.tickets[a['id']] = {'tick_id': tick_id, 'bp_name': bp, 'bp_id': bp_id,
                                             'sys_id': sys_id,
                                             'link': f"{self.snow.base_url}/nav_to.do?uri=incident.do?sys_id={sys_id}",
                                             'anomaly_id': a['id'],
                                             'bp_link': f"{self.aos_client.rest.base_url}/#/blueprints/{bp_id}/active/anomalies"
                                             }
                else:
                    print("Ticket for anomaly already exists : %s" % (self.tickets[a['id']]))
                    t1.pop(a['id'], None)
            # break
        for k in t1.keys():
            self.tickets.pop(k)
        self.close_tickets(t1)
        self.save_tickets_ps(self.tickets)

    # Get pause value
    def get_pause(self):
        ps = self.aos_client.design.property_sets.get_property_set(ps_name=self.ps_manager)
        if ps.get('values'):
            return ps['values'].get('pause') and str(ps['values'].get('pause')).upper() == "TRUE"
        return False

    # Save Tickets into the Property Set
    def save_tickets_ps(self, ticks):
        data = []
        for t in ticks.keys():
            data.append(ticks[t] | {'anomaly_id': t})
        values = {'tickets_info': data}
        try:
            ps = self.aos_client.design.property_sets.get_property_set(ps_name=self.ps_tickets)
            self.aos_client.rest.patch(uri=f"/api/property-sets/{ps['id']}",
                                       data={'label': self.ps_tickets, 'values': values})
        except AosAPIError:
            self.aos_client.design.property_sets.add_property_set([{'label': self.ps_tickets, 'values': values}])
        return

    # Find (or create) property set for the device CIS
    def save_devices_ps(self, devs):
        values = {'device_sys_ids': devs}
        try:
            ps = self.aos_client.design.property_sets.get_property_set(ps_name=self.ps_devices)
            self.aos_client.rest.put(uri=f"/api/property-sets/{ps['id']}",
                                     data={'label': self.ps_devices, 'values': values})
        except AosAPIError:
            self.aos_client.design.property_sets.add_property_set([{'label': self.ps_devices, 'values': values}])
        return

    # Check if there's a property set for device CIS. If none exists, go get CIs (or make them) in ServiceNow
    def load_devices_ps(self):
        try:
            ps = self.aos_client.design.property_sets.get_property_set(ps_name=self.ps_devices)
            self.devices = ps.get("values").get("devices_info")
        except AosAPIError:
            self.devices = self.make_managed_device_cis()
            self.aos_client.design.property_sets.add_property_set(
                [{'label': self.ps_devices, 'values': {'devices_info': self.devices}}])

    # Load Tickets from Property Set
    def load_tickets_ps(self):
        try:
            ps = self.aos_client.design.property_sets.get_property_set(ps_name=self.ps_tickets)
        except AosAPIError:
            ps = self.aos_client.design.property_sets.add_property_set(
                [{'label': self.ps_tickets, 'values': {'tickets_info': []}}])
        ticks = ps.get("values").get("tickets_info")
        for t in ticks:
            self.tickets[t['anomaly_id']] = t
        return

    # Get all anomalies
    def get_anomalies(self, bp_id):
        ano = self.aos_client.rest.json_resp_get("api/blueprints/" + bp_id + "/anomalies")
        return ano['items']

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
        ps = self.aos_client.design.property_sets.get_property_set(ps_name=self.ps_manager)
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
        print(f"resolving ticket {t}")
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
        devs = self.aos_client.rest.json_resp_get(uri="api/systems/")['items']
        cmdb = self.snow.resource(api_path='/table/cmdb_ci')

        devices = {}
        for d in devs:
            # pprint.pprint(d)
            r = cmdb.get(query={'name': d['status']['hostname']}, stream=True).first_or_none()
            if r:
                devices[d['facts']['serial_number']] = r['sys_id']
            else:
                payload = {'name': d['status']['hostname'], "sys_class_name": "cmdb_ci_ip_switch",
                           'ip_address': d['facts']['mgmt_ipaddr'], 'mac_address': d['facts']['mgmt_macaddr'],
                           'manufacturer': d['facts']['vendor'], 'model_number': d['facts']['hw_model'],
                           'serial_number': d['facts']['serial_number']}

                r = cmdb.create(payload=payload)
                devices[d['facts']['serial_number']] = r.all()[0]['sys_id']

        return devices


if __name__ == '__main__':
    pp = SNOWPowerPack()
    pp.start_threads(blocking=True)

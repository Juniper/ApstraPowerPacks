import ipaddress
import os
import pprint

import pysnow


class SNOWClient:
    def __init__(self):
        self.username = os.environ.get('SNOW_USER')
        self.password = os.environ.get('SNOW_PASS')
        self.client_id = "" #os.environ.get('SNOW_CLIENT_ID')
        self.client_secret = os.environ.get('SNOW_CLIENT_SECRET')
        self.token_updater = self.updater
        self.instance = os.environ.get('SNOW_INSTANCE_ID')
        self.token = os.environ.get('SNOW_TOKEN')
        if self.client_id:
            self.client = pysnow.OAuthClient(client_id=self.client_id,
                                        client_secret=self.client_secret,
                                        token_updater=self.updater, instance=self.instance)
            if not self.token:
                self.token = self.client.generate_token(self.username, self.password)
                self.client.set_token(self.token)
        else:
            self.client = pysnow.Client(user = self.username, password=self.password, instance=self.instance)
        self.incident = self.client.resource(api_path='/table/incident')
        self.incident.parameters.display_value = "all"
        self.switch = self.client.resource(api_path='/table/cmdb_ci_ip_switch')
        self.switch.parameters.display_value = "all"
        self.adapter  = self.client.resource(api_path="/table/cmdb_ci_network_adapter")
        self.adapter.parameters.display_value = "all"
        self.relationship = self.client.resource(api_path="/table/cmdb_rel_ci")
        self.relationship.parameters.display_value = "all"
        self.datacenter = self.client.resource(api_path="/table/cmdb_ci_datacenter")
        self.datacenter.parameters.display_value = "all"
        self.ip_address = self.client.resource(api_path="/table/cmdb_ci_ip_address")
        self.ip_address.parameters.display_value = "all"

    def updater(self, new_token):
        self.token = new_token

    def get_switch_cis(self):
        return self.switch.get().all()

    def get_adapter_cis(self):
        return self.adapter.get().all()


    def delete_switch_ci(self, sys_id):
        self.switch.delete(query={'sys_id': sys_id})
        rels = self.relationship.get(query={'parent':sys_id}).all()
        for r in rels:
            self.adapter.delete(query={'sys_id': r['child']['value']})
        adapters = self.adapter.get().all()
        for a in adapters:
            if a.get('cmdb_ci'):
                if a.get('value'):
                    self.adapter.delete(query={'sys_id':a.get('value')})

    def delete_adapter_ci(self, sys_id):
        self.adapter.delete(query={'sys_id': sys_id})

    def create_switch_ci_from_device(self, dev):
        r = self.switch.get(query={'name': dev['hostname']}, stream=True).first_or_none()
        if r:
            return r['sys_id']['value']
        else:
            payload = {'name': dev['hostname'], "sys_class_name": "cmdb_ci_ip_switch",
                       'ip_address': dev['ip_address'], 'mac_address': dev['mac_address'],
                       'manufacturer': dev['manufacturer'], 'model_number': dev['model_number'],
                       'serial_number': dev['serial_number']}
            r = self.switch.create(payload=payload)
            switch_sys_id = r.all()[0]['sys_id']['value']
            dev['sys_id'] = switch_sys_id
            for i in dev['interfaces']:
               # pprint.pprint(i)
                ip = i.get('ipv4_addr')
                if not ip:
                    ip = ''
                ip = ip.split('/')[0]
                payload = {
                            "ip_address":ip,
                            "netmask":'255.255.255.254',
                            "name":i.get("if_name"),
                            "cmdb_ci":switch_sys_id,
                            "short_description":i.get("description")
                           }
                #Create Adapter
                r2 = self.adapter.create(payload)
                adapter_sys_id = r2.all()[0]['sys_id']['value']
                rel = self.relationship.create(payload = {"parent":switch_sys_id,"child":adapter_sys_id, "type":{"value": "owned_by"}})
                i['sys_id'] = adapter_sys_id
                #Create IP Address
                payload.pop("cmdb_ci")
                payload.pop('name')
                payload.pop('short_description')
                payload['nic'] = adapter_sys_id
                self.ip_address.create(payload)

            return switch_sys_id


    def create_adapter_relationship(self, sys_id_1 ,sys_id_2):
        self.relationship.create(payload = {"parent":sys_id_1,"child":sys_id_2, "type":{"value": "connected_by"}})

    def create_datacenter(self, datacenter):
        payload = {'name': datacenter['label']}
        r = self.datacenter.create(payload)
        return r.all()[0]['sys_id']['value']

    def attach_device_to_datacenter(self, datacenter_sys_id, device_sys_id):
        self.relationship.create(payload = {"parent":datacenter_sys_id,"child":device_sys_id, "type":{"value": "Contained_in"}})


    def resolve_ticket(self, t):
        #print(f"resolving ticket {t}")
        self.incident.update({'number': t}, {'work_notes': "Anomaly resolved in Apstra."})
        response = self.incident.update({'number': t},
                                        {"close_code": "Resolved By Caller", "state": "6",
                                         "close_notes": "Closed by API"})
        # print(response)
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

    def make_ticket(self, ci_id, desc):
        # print("making ticket")
        # print(a_id, desc)
        s = self.pretty_print_anomaly(desc)

        response = self.incident.create(payload={
            'short_description': f'Apstra Network Anomaly - {str(desc.get("anomaly_type")).title()} Error ',
            'cmdb_ci': ci_id
        })

        tick_id = response.all()[0]['number']['value']
        sys_id = response.all()[0]['sys_id']['value']
        # print(tick_id)
        self.incident.update({'number': tick_id}, {'work_notes': s})

        return tick_id, sys_id


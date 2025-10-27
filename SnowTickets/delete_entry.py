from snow import SNOWClient


s = SNOWClient()
sw = s.get_switch_cis()
ad = s.get_adapter_cis()

for a in ad:
    s.delete_adapter_ci(a['sys_id']['value'])

for i in sw:
    s.delete_switch_ci(i['sys_id']['value'])




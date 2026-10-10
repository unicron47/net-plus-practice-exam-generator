"""Type 7, IP addressing faults (modelled on ExamTopics N10-008 #683): compare each device's IP settings and switch
port with the VLAN plan, then name the problem and the fix. Each device's department is stated, so a wrong IP and a
wrong VLAN cannot be confused."""
import ipaddress
from lib import *

PROBLEMS = ['No problem', 'Bad IP address', 'Bad subnet mask', 'Bad gateway address', 'Bad DNS address', 'Wrong VLAN',
            'APIPA address (no DHCP lease)']
SOLUTIONS = ['No change needed', 'Change IP address', 'Change subnet mask', 'Change gateway address', 'Change DNS address',
             'Change VLAN assignment', 'Release and renew IP address', 'Replace cable']
FIX = {'No problem': 'No change needed', 'Bad IP address': 'Change IP address', 'Bad subnet mask': 'Change subnet mask',
       'Bad gateway address': 'Change gateway address', 'Bad DNS address': 'Change DNS address',
       'Wrong VLAN': 'Change VLAN assignment', 'APIPA address (no DHCP lease)': 'Release and renew IP address'}

def check_fault(plan, dns, d):
    """Recompute the device's fault from its settings, so the key cannot drift from the data."""
    v = plan[d['dept']]
    sub = ipaddress.ip_network(v['subnet'])
    ip = ipaddress.ip_interface(f"{d['ip']}/{d['prefix']}")
    if ip.ip in ipaddress.ip_network('169.254.0.0/16'):
        return 'APIPA address (no DHCP lease)'
    if d['vlan'] != v['vlan']:
        return 'Wrong VLAN'
    if ip.ip not in sub or ip.ip in (sub.network_address, sub.broadcast_address):
        return 'Bad IP address'
    if d['prefix'] != sub.prefixlen:
        return 'Bad subnet mask'
    if d['gw'] != v['gw']:
        return 'Bad gateway address'
    if d.get('dns', dns) != dns:
        return 'Bad DNS address'
    return 'No problem'

def addressing(sid, title, objectives, scenario, plan, dns, devices, switch, diagram, explanation):
    panels = {}
    rows = []
    for d in devices:
        prob = check_fault(plan, dns, d)
        assert prob == d['fault'], (d['name'], prob, d['fault'])
        cfg = [['Department', d['dept']], ['Addressing', d.get('mode', 'Static')], ['IPv4 address', d['ip']],
               ['Subnet mask', mask(d['prefix'])], ['Default gateway', d['gw'] or '(none)'], ['DNS server', d.get('dns', dns)]]
        panels[d['id']] = panel(d['name'], ('IP configuration', [kv(cfg)]),
                                ('Diagnosis', [fields('Diagnosis',
                                    sel(f"{d['id']}_prob", f"{d['name']}: problem", PROBLEMS, prob, width='l'),
                                    sel(f"{d['id']}_fix", f"{d['name']}: solution", SOLUTIONS, FIX[prob], width='l'))]))
        rows.append([d['port'], d['name'], d['vlan']])
    rows.sort(key=lambda r: int(r[0].split('/')[-1]))
    panels['sw'] = panel(switch, [table('Access ports', ['Port', 'Connected to', 'VLAN'], rows)])
    panels['plan'] = panel('VLAN usage', [table('VLAN plan', ['VLAN', 'Department', 'Subnet', 'Gateway (router)'],
                                                [[v['vlan'], k, v['subnet'], v['gw']] for k, v in plan.items()]),
                                          kv([['DNS server', dns]])])
    return {'id': sid, 'type': 'addressing', 'title': title, 'objectives': objectives, 'scenario': scenario,
            'requirements': ['Review the VLAN plan, the switch port assignments and each device\'s IP configuration',
                             'For every device, choose the problem (or No problem) and the solution'],
            'instructions': 'Select VLANs (the usage plan), the switch and each device to open them. Choose a problem and a solution '
                            'for every device.',
            'views': [{'label': 'Network', 'diagram': diagram}], 'panels': panels, 'explanation': explanation}

# ── A: departments on one switch stack (like #683) ─────────────────────────
def departments():
    plan = {'Admin staff': {'vlan': '10', 'subnet': '10.10.4.0/24', 'gw': '10.10.4.1'},
            'HR': {'vlan': '20', 'subnet': '10.10.2.0/24', 'gw': '10.10.2.1'},
            'Marketing': {'vlan': '30', 'subnet': '10.10.3.0/24', 'gw': '10.10.3.1'},
            'Servers': {'vlan': '50', 'subnet': '10.10.5.0/24', 'gw': '10.10.5.1'}}
    dns = '10.10.5.53'
    D = lambda **k: k
    devices = [
        D(id='srv', name='Server1', dept='Servers', ip='10.10.5.53', prefix=24, gw='10.10.5.254', vlan='50', port='Gi1/0/1',
          fault='Bad gateway address'),
        D(id='pc1', name='PC1', dept='Admin staff', ip='10.10.4.11', prefix=24, gw='10.10.4.1', vlan='10', port='Gi1/0/6',
          fault='No problem'),
        D(id='pc2', name='PC2', dept='Admin staff', ip='10.10.4.140', prefix=25, gw='10.10.4.1', vlan='10', port='Gi1/0/7',
          fault='Bad subnet mask'),
        D(id='pc3', name='PC3', dept='HR', ip='10.10.2.13', prefix=24, gw='10.10.2.1', vlan='30', port='Gi1/0/4',
          fault='Wrong VLAN'),
        D(id='pc4', name='PC4', dept='Marketing', ip='10.10.3.14', prefix=24, gw='10.10.3.1', dns='10.10.5.35', vlan='30',
          port='Gi1/0/2', fault='Bad DNS address'),
        D(id='pc5', name='PC5', dept='HR', ip='10.10.3.15', prefix=24, gw='10.10.2.1', vlan='20', port='Gi1/0/3',
          fault='Bad IP address'),
        D(id='prn', name='Printer', dept='Admin staff', ip='10.10.4.16', prefix=24, gw='10.10.4.1', vlan='10', port='Gi1/0/8',
          fault='No problem')]
    pc2 = ipaddress.ip_interface('10.10.4.140/25').network
    diagram = {
        'w': 780, 'h': 400,
        'zones': [zone(14, 14, 200, 130, 'Marketing', 'd'), zone(236, 14, 300, 130, 'HR', 'c'),
                  zone(236, 256, 440, 130, 'Admin staff', 'b'), zone(14, 160, 200, 110, 'Servers', 'a')],
        'nodes': [node('pc4', 'pc', 114, 70, 'PC4', 'Marketing', 'pc4'),
                  node('pc5', 'pc', 320, 70, 'PC5', 'HR', 'pc5'), node('pc3', 'pc', 450, 70, 'PC3', 'HR', 'pc3'),
                  node('srv', 'server', 114, 205, 'Server1', 'DNS / files', 'srv'),
                  node('sw', 'switch', 385, 195, 'Switch1', 'ports', 'sw'),
                  node('rtr', 'router', 600, 195, 'Router', 'gateways'),
                  node('pc1', 'pc', 320, 310, 'PC1', 'Admin', 'pc1'), node('pc2', 'pc', 450, 310, 'PC2', 'Admin', 'pc2'),
                  node('prn', 'printer', 590, 310, 'Printer', 'Admin', 'prn'),
                  node('plan', 'vlan', 700, 70, 'VLANs', 'usage plan', 'plan')],
        'links': [link('sw', 'pc4'), link('sw', 'pc5'), link('sw', 'pc3'), link('sw', 'srv'), link('sw', 'rtr', 'trunk'),
                  link('sw', 'pc1'), link('sw', 'pc2'), link('sw', 'prn')]}
    return addressing('pbq-addr-depts', 'Department addressing faults', ['1.4', '2.1', '5.5'],
        ['Some devices in a small office cannot reach the network or other departments, while others work. Every device '
         'is configured statically, and each department has its own VLAN and subnet.'],
        plan, dns, devices, 'Switch1', diagram,
        ['Server1\'s gateway is 10.10.5.254, but the router\'s address in the server VLAN is 10.10.5.1: change the gateway. '
         f'PC2 uses a /25 mask, so its subnet is {pc2} and the gateway 10.10.4.1 is outside it: change the mask to /24.',
         'PC3 is in HR and has an HR address, but its switch port is in VLAN 30 (Marketing): change the VLAN assignment. '
         'PC5 is in HR and on VLAN 20, but its address 10.10.3.15 is from the Marketing subnet: change the IP address.',
         'PC4 points at 10.10.5.35 for DNS instead of Server1 (10.10.5.53), so it reaches hosts by address but cannot '
         'resolve names: change the DNS address. PC1 and the printer match the plan.'])

# ── B: second floor, routers at .254, DHCP for staff ──────────────────────
def second_floor():
    plan = {'Staff': {'vlan': '110', 'subnet': '172.20.10.0/24', 'gw': '172.20.10.254'},
            'Printers': {'vlan': '130', 'subnet': '172.20.30.0/24', 'gw': '172.20.30.254'},
            'Servers': {'vlan': '140', 'subnet': '172.20.40.0/24', 'gw': '172.20.40.254'}}
    dns = '172.20.40.10'
    D = lambda **k: k
    devices = [
        D(id='lap', name='Laptop1', dept='Staff', mode='DHCP', ip='169.254.33.7', prefix=16, gw='', dns='(none)', vlan='110',
          port='Gi1/0/5', fault='APIPA address (no DHCP lease)'),
        D(id='pc1', name='PC1', dept='Staff', mode='DHCP', ip='172.20.10.21', prefix=24, gw='172.20.10.254', vlan='110',
          port='Gi1/0/6', fault='No problem'),
        D(id='pc2', name='PC2', dept='Staff', ip='172.20.10.22', prefix=24, gw='172.20.10.1', vlan='110', port='Gi1/0/7',
          fault='Bad gateway address'),
        D(id='pc3', name='PC3', dept='Staff', ip='172.20.10.255', prefix=24, gw='172.20.10.254', vlan='110', port='Gi1/0/8',
          fault='Bad IP address'),
        D(id='pr1', name='Printer1', dept='Printers', ip='172.20.30.5', prefix=16, gw='172.20.30.254', vlan='130',
          port='Gi1/0/11', fault='Bad subnet mask'),
        D(id='pr2', name='Printer2', dept='Printers', ip='172.20.30.6', prefix=24, gw='172.20.30.254', vlan='110',
          port='Gi1/0/12', fault='Wrong VLAN'),
        D(id='fs1', name='FS1', dept='Servers', ip='172.20.40.20', prefix=24, gw='172.20.40.254', vlan='140',
          port='Gi1/0/1', fault='No problem')]
    diagram = {
        'w': 780, 'h': 400,
        'zones': [zone(14, 14, 470, 130, 'Staff', 'b'), zone(14, 256, 300, 130, 'Printers', 'd'),
                  zone(510, 256, 256, 130, 'Servers', 'a')],
        'nodes': [node('lap', 'laptop', 80, 70, 'Laptop1', 'DHCP', 'lap'), node('pc1', 'pc', 190, 70, 'PC1', 'DHCP', 'pc1'),
                  node('pc2', 'pc', 300, 70, 'PC2', 'static', 'pc2'), node('pc3', 'pc', 410, 70, 'PC3', 'static', 'pc3'),
                  node('sw', 'switch', 390, 200, 'Floor2-SW', 'ports', 'sw'),
                  node('rtr', 'router', 620, 140, 'Router', 'gateways'),
                  node('pr1', 'printer', 100, 315, 'Printer1', None, 'pr1'),
                  node('pr2', 'printer', 230, 315, 'Printer2', None, 'pr2'),
                  node('fs1', 'server', 600, 315, 'FS1', 'files', 'fs1'),
                  node('plan', 'vlan', 700, 50, 'VLANs', 'usage plan', 'plan')],
        'links': [link('sw', 'lap'), link('sw', 'pc1'), link('sw', 'pc2'), link('sw', 'pc3'), link('sw', 'rtr', 'trunk'),
                  link('sw', 'pr1'), link('sw', 'pr2'), link('sw', 'fs1')]}
    return addressing('pbq-addr-floor', 'Second-floor connectivity', ['1.4', '1.6', '5.5'],
        ['The DHCP server for the staff VLAN was offline this morning and has now been restored, but some devices on the '
         'second floor still cannot connect. Staff laptops and PC1 use DHCP; every other device is configured statically. '
         'On this floor the router is always the .254 address of each subnet.'],
        plan, dns, devices, 'Floor2-SW', diagram,
        ['Laptop1 has a 169.254.x.x (APIPA) address: it self-assigned one when DHCP got no answer and keeps it until its '
         'next retry. Release and renew its address to get a lease now that the server is back. PC1 got a correct lease.',
         'PC2 points at 172.20.10.1, but the router is 172.20.10.254: change the gateway. PC3\'s address 172.20.10.255 is the '
         'broadcast address of 172.20.10.0/24 and cannot be assigned to a host: change the IP address.',
         'Printer1 has a /16 mask, so it treats every 172.20.x.x address (including the staff and server subnets) as local and '
         'never sends that traffic to its gateway: change the mask to /24. Printer2\'s settings are right, but its switch '
         'port is in the staff VLAN 110 instead of 130: change the VLAN assignment. FS1 matches the plan.'])

def build():
    return [departments(), second_floor()]

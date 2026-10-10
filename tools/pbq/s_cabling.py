"""Type 4, cabling and port troubleshooting (modelled on ExamTopics N10-008 #461): read the cable test results,
switch port tables and IP settings, then name each component's problem and the fix."""
import ipaddress
from lib import *

PROBLEMS = ['No problem', 'Cable short detected', 'Open cable detected', 'Connector on backward', 'Cable too long',
            'Crossover cable used', 'Wrong VLAN', 'Bad subnet mask', 'Wrong default gateway', 'Port shut down']
SOLUTIONS = ['No change needed', 'Replace cable', 'Change VLAN assignment', 'Change subnet mask', 'Change IP address',
             'Change gateway address', 'Enable the switch port', 'Enable Spanning Tree Protocol', 'Flush ARP cache']
FIX = {'No problem': 'No change needed', 'Cable short detected': 'Replace cable', 'Open cable detected': 'Replace cable',
       'Connector on backward': 'Replace cable', 'Cable too long': 'Replace cable', 'Crossover cable used': 'Replace cable',
       'Wrong VLAN': 'Change VLAN assignment', 'Bad subnet mask': 'Change subnet mask',
       'Wrong default gateway': 'Change gateway address', 'Port shut down': 'Enable the switch port'}

def device(pid, title, ipcfg, problem):
    """A PC or server: its IP settings plus the diagnosis fields."""
    return panel(title,
                 ('IP configuration', [kv(ipcfg)]),
                 ('Diagnosis', [fields('Diagnosis',
                                       sel(f'{pid}_prob', f'{title}: problem', PROBLEMS, problem, width='l'),
                                       sel(f'{pid}_fix', f'{title}: solution', SOLUTIONS, FIX[problem], width='l'))]))

def ipcfg(ip, prefix, gw, dns):
    return [['IPv4 address', ip], ['Subnet mask', mask(prefix)], ['Default gateway', gw], ['DNS server', dns]]

def cable(name, pairs, length, port, vlan, link, shorts=None, end='switch'):
    return (name, [wiremap(f'{name} cable', pairs,
                           [['Length', f'{length} m'], ['Switch port', port], ['VLAN', vlan], ['Link', link]],
                           shorts=shorts, note=f'Connected to {end}',
                           alt=f'{name} wiremap')])

# ── A: SOHO with Auto-MDIX turned off ──────────────────────────────────────
def soho():
    lan, gw, dns = '192.168.1.0/24', '192.168.1.1', '192.168.1.1'
    ip = lambda n: host(lan, n)
    devs = [('srv', 'Server 1', 10, 'No problem'), ('pc1', 'PC1', 21, 'Cable short detected'),
            ('pc2', 'PC2', 22, 'No problem'), ('pc3', 'PC3', 23, 'Crossover cable used'),
            ('pc4', 'PC4', 24, 'Wrong VLAN'), ('pc5', 'PC5', 25, 'Connector on backward'),
            ('pc6', 'PC6', 26, 'Cable too long')]
    panels = {pid: device(pid, name, ipcfg(ip(n), 24, gw, dns), prob) for pid, name, n, prob in devs}
    panels['sw1'] = panel('Switch 1', ('Ports', [table('Port status', ['Port', 'Connected to', 'VLAN', 'Status'], [
        ['Gi0/1', 'Router', '10', 'connected'], ['Gi0/2', 'Server 1', '10', 'connected'], ['Gi0/3', 'PC1', '10', 'notconnect'],
        ['Gi0/4', 'PC4', '20', 'connected'], ['Gi0/5', 'PC5', '10', 'notconnect'], ['Gi0/24', 'Switch 2', '10 (trunk)', 'connected']]),
        kv([['Auto-MDIX', 'disabled on all ports'], ['Spanning tree', 'enabled']])]),
        ('VLANs', [table('VLANs', ['VLAN', 'Name', 'Subnet'], [['10', 'OFFICE', lan], ['20', 'CAMERAS', '192.168.2.0/24']])]))
    panels['sw2'] = panel('Switch 2', ('Ports', [table('Port status', ['Port', 'Connected to', 'VLAN', 'Status'], [
        ['Gi0/1', 'PC2', '10', 'connected'], ['Gi0/2', 'PC3', '10', 'notconnect'], ['Gi0/3', 'PC6', '10', 'connected'],
        ['Gi0/24', 'Switch 1', '10 (trunk)', 'connected']]), kv([['Auto-MDIX', 'disabled on all ports'], ['Spanning tree', 'enabled']])]))
    panels['tester'] = panel('Cable test results',
        cable('Switch 2 uplink', GIG_CROSSOVER, 16, 'Gi0/24 ↔ Switch 1 Gi0/24', '10 (trunk)', '1000 Mb/s full duplex', end='Switch 1'),
        cable('Server 1', STRAIGHT, 3, 'Switch 1 Gi0/2', '10', '1000 Mb/s full duplex'),
        cable('PC1', STRAIGHT, 22, 'Switch 1 Gi0/3', '10', 'no link', shorts=[[3, 6]]),
        cable('PC2', STRAIGHT, 31, 'Switch 2 Gi0/1', '10', '1000 Mb/s full duplex'),
        cable('PC3', GIG_CROSSOVER, 18, 'Switch 2 Gi0/2', '10', 'no link'),
        cable('PC4', STRAIGHT, 27, 'Switch 1 Gi0/4', '20', '1000 Mb/s full duplex'),
        cable('PC5', REVERSED, 9, 'Switch 1 Gi0/5', '10', 'no link'),
        cable('PC6', STRAIGHT, 112, 'Switch 2 Gi0/3', '10', '100 Mb/s half duplex, CRC errors'))
    return {
        'id': 'pbq-cable-soho', 'type': 'cabling', 'title': 'SOHO connectivity troubleshooting',
        'objectives': ['1.3', '5.2', '5.3', '2.1'],
        'scenario': ['A small office reports that several PCs cannot reach the network while others work normally. All office '
                     'devices belong on VLAN 10 (192.168.1.0/24). Auto-MDIX is turned off on both switches.'],
        'requirements': ['Review the cable test results first',
                         'Check each switch\'s port table and each device\'s IP configuration',
                         'For the server and every PC, choose the problem (or No problem) and the solution'],
        'instructions': 'Select the cable tester, the switches, the server and the PCs to open them. Choose a problem and a '
                        'solution for the server and every PC.',
        'views': [{'label': 'Office', 'diagram': {
            'w': 780, 'h': 400,
            'zones': [zone(14, 14, 752, 372, 'Office', 'b')],
            'nodes': [node('rtr', 'router', 90, 70, 'Router', gw),
                      node('srv', 'server', 90, 220, 'Server 1', None, 'srv'),
                      node('sw1', 'switch', 280, 220, 'Switch 1', None, 'sw1'),
                      node('sw2', 'switch', 560, 220, 'Switch 2', None, 'sw2'),
                      node('pc1', 'pc', 280, 70, 'PC1', None, 'pc1'), node('pc4', 'pc', 190, 340, 'PC4', None, 'pc4'),
                      node('pc5', 'pc', 370, 340, 'PC5', None, 'pc5'), node('pc2', 'pc', 480, 70, 'PC2', None, 'pc2'),
                      node('pc3', 'pc', 650, 70, 'PC3', None, 'pc3'), node('pc6', 'pc', 650, 340, 'PC6', None, 'pc6'),
                      node('tester', 'tester', 720, 220, 'Tester', 'cable results', 'tester')],
            'links': [link('rtr', 'sw1'), link('srv', 'sw1'), link('sw1', 'pc1'), link('sw1', 'pc4'), link('sw1', 'pc5'),
                      link('sw1', 'sw2'), link('sw2', 'pc2'), link('sw2', 'pc3'), link('sw2', 'pc6')]}}],
        'panels': panels,
        'explanation': [
            'Wiremaps: PC1 shows pins 3 and 6 shorted together, PC5 is wired 1→8, 2→7 … (a connector on backward) and PC3 is '
            'a crossover cable. With Auto-MDIX off, a PC needs a straight-through cable to a switch, so PC3 has no link; the '
            'switch-to-switch uplink needs exactly the crossover it has. All three are fixed by replacing the cable.',
            'PC6\'s run is 112 m, longer than the 100 m limit for twisted pair, which causes the CRC errors and the fallback to '
            '100 Mb/s half duplex: replace it with a shorter run (or add a switch). PC4\'s cable and IP settings are fine, but its '
            'switch port is in VLAN 20 (cameras) instead of VLAN 10, so change the VLAN assignment.',
            'Server 1 and PC2 have good straight-through cables under 100 m, link at 1000 Mb/s full duplex and correct settings: '
            'no problem.'],
    }

# ── B: small office, Auto-MDIX on ──────────────────────────────────────────
def office():
    lan, gw, dns = '10.50.4.0/24', '10.50.4.1', '10.50.4.10'
    ip = lambda n: host(lan, n)
    OPEN2 = [[1, 1], [2, None], [3, 3], [4, 4], [5, 5], [6, 6], [7, 7], [8, 8]]
    prn_net = ipaddress.ip_network(f'{ip(41)}/30', strict=False)
    assert ipaddress.ip_address(gw) not in prn_net
    devs = [('nas', 'NAS', ipcfg(ip(10), 24, gw, dns), 'No problem'),
            ('prn', 'Printer', ipcfg(ip(41), 30, gw, dns), 'Bad subnet mask'),
            ('pc1', 'PC1', ipcfg(ip(51), 24, gw, dns), 'Open cable detected'),
            ('pc2', 'PC2', ipcfg(ip(52), 24, gw, dns), 'Port shut down'),
            ('pc3', 'PC3', ipcfg(ip(53), 24, gw, dns), 'No problem'),
            ('pc4', 'PC4', ipcfg(ip(54), 24, ip(254), dns), 'Wrong default gateway'),
            ('pc5', 'PC5', ipcfg(ip(55), 24, gw, dns), 'No problem')]
    panels = {pid: device(pid, name, cfg, prob) for pid, name, cfg, prob in devs}
    panels['sw'] = panel('Office switch', [table('Port status', ['Port', 'Connected to', 'VLAN', 'Status'], [
        ['Gi1/0/1', 'Router', '30', 'connected'], ['Gi1/0/2', 'NAS', '30', 'connected'], ['Gi1/0/3', 'Printer', '30', 'connected'],
        ['Gi1/0/4', 'PC1', '30', 'notconnect'], ['Gi1/0/5', 'PC2', '30', 'disabled'], ['Gi1/0/6', 'PC3', '30', 'connected'],
        ['Gi1/0/7', 'PC4', '30', 'connected'], ['Gi1/0/8', 'PC5', '30', 'connected']]),
        kv([['VLAN 30', f'OFFICE, {lan}'], ['Auto-MDIX', 'enabled'], ['Router (gateway)', gw], ['DNS server', dns]])])
    panels['tester'] = panel('Cable test results',
        cable('NAS', STRAIGHT, 2, 'Gi1/0/2', '30', '1000 Mb/s full duplex'),
        cable('Printer', STRAIGHT, 14, 'Gi1/0/3', '30', '100 Mb/s full duplex'),
        cable('PC1', OPEN2, 37, 'Gi1/0/4', '30', 'no link'),
        cable('PC2', STRAIGHT, 41, 'Gi1/0/5', '30', 'no link'),
        cable('PC3', STRAIGHT, 45, 'Gi1/0/6', '30', '1000 Mb/s full duplex'),
        cable('PC4', STRAIGHT, 52, 'Gi1/0/7', '30', '1000 Mb/s full duplex'),
        cable('PC5', STRAIGHT, 98, 'Gi1/0/8', '30', '1000 Mb/s full duplex'))
    return {
        'id': 'pbq-cable-office', 'type': 'cabling', 'title': 'Office help-desk tickets',
        'objectives': ['1.3', '5.2', '5.3', '5.5'],
        'scenario': ['Several users in a small office opened tickets: some have no network at all, others can reach local '
                     'devices but not the internet, and the printer cannot be reached. Every device is on VLAN 30 '
                     f'({lan}); the router is {gw}.'],
        'requirements': ['Review the cable test results, the switch port table and each device\'s IP configuration',
                         'For the NAS, the printer and every PC, choose the problem (or No problem) and the solution'],
        'instructions': 'Select the cable tester, the switch, the NAS, the printer and the PCs to open them.',
        'views': [{'label': 'Office', 'diagram': {
            'w': 780, 'h': 380,
            'zones': [zone(14, 14, 752, 352, 'Office', 'b')],
            'nodes': [node('rtr', 'router', 390, 60, 'Router', gw),
                      node('sw', 'switch', 390, 190, 'Office switch', None, 'sw'),
                      node('nas', 'db', 100, 110, 'NAS', None, 'nas'), node('prn', 'printer', 100, 270, 'Printer', None, 'prn'),
                      node('pc1', 'pc', 220, 320, 'PC1', None, 'pc1'), node('pc2', 'pc', 340, 320, 'PC2', None, 'pc2'),
                      node('pc3', 'pc', 460, 320, 'PC3', None, 'pc3'), node('pc4', 'pc', 580, 320, 'PC4', None, 'pc4'),
                      node('pc5', 'pc', 690, 200, 'PC5', None, 'pc5'),
                      node('tester', 'tester', 690, 70, 'Tester', 'cable results', 'tester')],
            'links': [link('rtr', 'sw'), link('sw', 'nas'), link('sw', 'prn'), link('sw', 'pc1'), link('sw', 'pc2'),
                      link('sw', 'pc3'), link('sw', 'pc4'), link('sw', 'pc5')]}}],
        'panels': panels,
        'explanation': [
            'PC1\'s wiremap shows pin 2 open, so there is no link: replace the cable. PC2\'s cable tests good, but its switch port '
            'is administratively down (shut down): enable the port.',
            f'The printer\'s mask is {mask(30)} (/30), so its subnet is {prn_net} (hosts {prn_net[1]}–{prn_net[2]}) and the gateway '
            f'{gw} is outside it: change the mask to {mask(24)}. PC4 points at {ip(254)}, which is not the router, so it '
            'reaches local devices but not the internet: change the gateway address.',
            'The NAS, PC3 and PC5 have no problem. PC5\'s 98 m run is within the 100 m limit and links at 1000 Mb/s, and the '
            'printer\'s 100 Mb/s link speed is normal for a printer.'],
    }

def build():
    return [soho(), office()]

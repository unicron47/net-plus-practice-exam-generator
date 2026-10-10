"""Type 3, switch port configuration (modelled on ExamTopics N10-008 #347): fix each switch's port table,
starting from the configuration that is on the switch now."""
from lib import *

FREE = {'free': True}
STATUS = ['Enabled', 'Disabled']
MODE = ['Access', 'Trunk']
LACP = ['Enabled', 'Disabled']

def cell(id, label, kind, options, answer, initial):
    f = {'id': id, 'label': label, 'type': kind, 'options': list(options), 'answer': answer, 'initial': initial}
    if kind == 'checks' and isinstance(answer, list):
        f['answer'] = {'set': answer}
    # a cell that must change is worth 2, so leaving the table as it is earns about a third
    if answer != FREE and (sorted(answer) != sorted(initial) if kind == 'checks' else answer != initial):
        f['points'] = 2
    return f

def grid(title, columns, rows):
    return {'kind': 'grid', 'title': title, 'columns': columns, 'rows': rows}

def vlan_table(rows):
    return table('VLANs', ['VLAN', 'Name', 'Used for'], rows)

# ── A: replaced access switch, LACP uplinks ────────────────────────────────
A_VLANS = ['1', '10', '20', '30', '40']

def a_row(sw, port, dev, want, start):
    """want/start: (status, mode, vlan, allowed, lacp); want None = not graded."""
    p = f'{sw}p{port}'
    name = f'Gi1/0/{port}'
    ws, wm, wv, wa, wl = want
    ss, sm, sv, sa, sl = start
    disabled = ws == 'Disabled'
    trunk = wm == 'Trunk'
    return [name, dev,
            cell(f'{p}_st', f'{sw.upper()} {name} status', 'select', STATUS, ws, ss),
            cell(f'{p}_md', f'{sw.upper()} {name} mode', 'select', MODE, FREE if disabled else wm, sm),
            cell(f'{p}_vl', f'{sw.upper()} {name} access VLAN', 'select', A_VLANS, FREE if disabled or trunk else wv, sv),
            cell(f'{p}_al', f'{sw.upper()} {name} allowed VLANs', 'checks', A_VLANS, wa if trunk and not disabled else FREE, sa),
            cell(f'{p}_lc', f'{sw.upper()} {name} LACP', 'seg', LACP, wl if trunk and not disabled else FREE, sl)]

def replaced():
    cols = ['Port', 'Connected to', 'Status', 'Mode', 'Access VLAN', 'Allowed VLANs (trunk)', 'LACP']
    up = ['10', '20', '30']
    sw1 = [a_row('sw1', 1, 'SW3 Gi1/0/1', ('Enabled', 'Trunk', None, up, 'Enabled'), ('Enabled', 'Trunk', '1', up, 'Enabled')),
           a_row('sw1', 2, 'SW3 Gi1/0/2', ('Enabled', 'Trunk', None, up, 'Enabled'), ('Enabled', 'Trunk', '1', ['10', '20'], 'Disabled')),
           ['Gi1/0/3', 'Router (inter-VLAN routing)', 'Enabled', 'Trunk', '—', '10, 20, 30, 40', 'Disabled'],
           a_row('sw1', 4, '(nothing connected)', ('Disabled', None, None, None, None), ('Enabled', 'Access', '1', [], 'Disabled'))]
    default = ('Enabled', 'Access', '1', [], 'Disabled')
    sw3 = [a_row('sw3', 1, 'SW1 Gi1/0/1', ('Enabled', 'Trunk', None, up, 'Enabled'), default),
           a_row('sw3', 2, 'SW1 Gi1/0/2', ('Enabled', 'Trunk', None, up, 'Enabled'), default),
           a_row('sw3', 3, 'Workstation ENG-14', ('Enabled', 'Access', '10', None, None), default),
           a_row('sw3', 4, 'Workstation ENG-15', ('Enabled', 'Access', '10', None, None), default),
           a_row('sw3', 5, 'Printer PRN-3', ('Enabled', 'Access', '20', None, None), default),
           a_row('sw3', 6, 'IP camera CAM-East', ('Enabled', 'Access', '30', None, None), default),
           a_row('sw3', 7, '(nothing connected)', ('Disabled', None, None, None, None), default),
           a_row('sw3', 8, '(nothing connected)', ('Disabled', None, None, None, None), default)]
    vlans = vlan_table([['1', 'default', 'not used'], ['10', 'ENG-STAFF', 'staff workstations'], ['20', 'PRINT', 'printers'],
                        ['30', 'CAMERAS', 'security cameras'], ['40', 'GUEST', 'guest Wi-Fi (other floors only)']])
    return {
        'id': 'pbq-ports-replaced', 'type': 'switchports', 'title': 'Replaced access switch',
        'objectives': ['2.1', '2.2', '5.5'],
        'scenario': ['Switch SW3 on the engineering floor failed and was replaced with a new switch that still has its '
                     'factory settings. SW1, the distribution switch, was changed during the outage and may also need attention.'],
        'requirements': ['Each device must reach only its correct network (see the VLAN list)',
                         'Disable every switch port that has nothing connected',
                         'The two links between SW1 and SW3 must form a single fault-tolerant connection',
                         'The links between SW1 and SW3 must carry only the VLANs that devices on SW3 use',
                         'Only make the changes needed to meet these requirements'],
        'instructions': 'Select SW1 or SW3 to open its port table. Changes save automatically; the table starts with the '
                        'configuration the switch has now. Cells that do not apply to a port (for example, the access VLAN '
                        'of a trunk, or anything but the status of a disabled port) are not graded.',
        'views': [{'label': 'Engineering floor', 'diagram': {
            'w': 760, 'h': 340,
            'zones': [zone(16, 16, 300, 308, 'Distribution', 'a'), zone(340, 16, 404, 308, 'Engineering floor', 'b')],
            'nodes': [node('rtr', 'router', 160, 70, 'Router', 'inter-VLAN'),
                      node('sw1', 'switch', 160, 200, 'SW1', 'distribution', 'sw1'),
                      node('sw3', 'switch', 420, 200, 'SW3', 'replaced', 'sw3'),
                      node('ws1', 'pc', 560, 70, 'ENG-14'), node('ws2', 'pc', 670, 70, 'ENG-15'),
                      node('prn', 'printer', 560, 290, 'PRN-3'), node('cam', 'camera', 670, 290, 'CAM-East')],
            'links': [link('rtr', 'sw1', 'Gi1/0/3'), link('sw1', 'sw3', '2 links'),
                      link('sw3', 'ws1', 'Gi1/0/3'), link('sw3', 'ws2', 'Gi1/0/4'),
                      link('sw3', 'prn', 'Gi1/0/5'), link('sw3', 'cam', 'Gi1/0/6')]}}],
        'panels': {
            'sw1': panel('SW1 (distribution switch)', ('Ports', [grid('SW1 port table', cols, sw1)]), ('VLANs', [vlans])),
            'sw3': panel('SW3 (replacement switch)', ('Ports', [grid('SW3 port table', cols, sw3)]), ('VLANs', [vlans]))},
        'explanation': [
            'Each end device needs an access port in its own VLAN: the two workstations in 10, the printer in 20 and the camera '
            'in 30. A new switch puts every port in VLAN 1, which none of these devices use.',
            'Two links between switches become one fault-tolerant connection with link aggregation (LACP, 802.3ad), so LACP must '
            'be enabled on both ports at both ends; SW1 Gi1/0/2 had it disabled. A link that carries several VLANs must be an 802.1Q trunk, '
            'and pruning it to 10, 20 and 30 keeps VLAN 40 (and the unused VLAN 1) off the floor. SW1 Gi1/0/2 was missing VLAN 30.',
            'Unused ports are disabled so nobody can plug in an unauthorized device (port security, objective 5.5). The router '
            'port on SW1 was already correct and should be left alone.'],
    }

# ── B: voice VLAN and AP trunks with a native VLAN ─────────────────────────
B_VLANS = ['None', '1', '10', '50', '60', '99']
B_ALLOWED = ['1', '10', '50', '60', '99']

def b_row(port, dev, want, start):
    """want/start: (status, mode, access, voice, native, allowed)."""
    p = f'fop{port}'
    name = f'Gi1/0/{port}'
    ws, wm, wa, wv, wn, wl = want
    off, trunk = ws == 'Disabled', wm == 'Trunk'
    ss, sm, sa, sv, sn, sl = start
    g = lambda w, applies: w if applies and not off else FREE
    return [name, dev,
            cell(f'{p}_st', f'{name} status', 'select', STATUS, ws, ss),
            cell(f'{p}_md', f'{name} mode', 'select', MODE, g(wm, True), sm),
            cell(f'{p}_ac', f'{name} access VLAN', 'select', B_VLANS[1:], g(wa, not trunk), sa),
            cell(f'{p}_vo', f'{name} voice VLAN', 'select', B_VLANS, g(wv, not trunk), sv),
            cell(f'{p}_nv', f'{name} native VLAN', 'select', B_VLANS[1:], g(wn, trunk), sn),
            cell(f'{p}_al', f'{name} allowed VLANs', 'checks', B_ALLOWED, g(wl, trunk), sl)]

def front_office():
    cols = ['Port', 'Connected to', 'Status', 'Mode', 'Access VLAN', 'Voice VLAN', 'Native VLAN', 'Allowed VLANs (trunk)']
    ap = ['10', '60', '99']
    rows = [['Gi1/0/1', 'Router (uplink)', 'Enabled', 'Trunk', '—', '—', '1', '10, 50, 60, 99'],
            b_row(2, 'Phone FO-1 (desk PC behind it)', ('Enabled', 'Access', '10', '50', None, None),
                  ('Enabled', 'Access', '10', 'None', '1', [])),
            b_row(3, 'Phone FO-2 (desk PC behind it)', ('Enabled', 'Access', '10', '50', None, None),
                  ('Enabled', 'Access', '50', '10', '1', [])),
            b_row(4, 'Access point AP-Lobby', ('Enabled', 'Trunk', None, None, '99', ap),
                  ('Enabled', 'Access', '60', 'None', '1', [])),
            b_row(5, 'Access point AP-Office', ('Enabled', 'Trunk', None, None, '99', ap),
                  ('Enabled', 'Trunk', '1', 'None', '1', ['10', '99'])),
            b_row(6, 'Printer FO-PRN', ('Enabled', 'Access', '10', 'None', None, None),
                  ('Enabled', 'Access', '10', '50', '1', [])),
            b_row(7, '(nothing connected)', ('Disabled', None, None, None, None, None),
                  ('Enabled', 'Access', '10', 'None', '1', [])),
            b_row(8, '(nothing connected)', ('Disabled', None, None, None, None, None),
                  ('Disabled', 'Access', '1', 'None', '1', []))]
    vlans = vlan_table([['1', 'default', 'not used'], ['10', 'DATA', 'PCs and printers'], ['50', 'VOICE', 'IP phones'],
                        ['60', 'GUEST', 'guest Wi-Fi (SSID Visitor)'], ['99', 'MGMT', 'switch and AP management']])
    return {
        'id': 'pbq-ports-voice', 'type': 'switchports', 'title': 'Front office phones and access points',
        'objectives': ['2.1', '2.2', '2.3', '5.5'],
        'scenario': ['A front office is moving to IP phones and two new access points on switch FO-SW. Each desk PC plugs into '
                     'the back of its phone, so phone and PC share one switch port. Part of the port configuration was entered '
                     'by a contractor and contains errors.'],
        'requirements': ['Phones must use the voice VLAN and the PCs behind them the data VLAN',
                         'Configure a voice VLAN only on ports that have a phone',
                         'Each access point is managed on the management VLAN, sent untagged, and serves the staff SSID (data VLAN) '
                         'and the guest SSID Visitor (guest VLAN) as tagged traffic',
                         'Carry only the VLANs each access point needs',
                         'Disable every switch port that has nothing connected'],
        'instructions': 'Select FO-SW to open its port table. Changes save automatically; the table starts with the configuration '
                        'the switch has now. Cells that do not apply to a port (for example, the native VLAN of an access '
                        'port, or anything but the status of a disabled port) are not graded.',
        'views': [{'label': 'Front office', 'diagram': {
            'w': 760, 'h': 330,
            'zones': [zone(16, 16, 728, 298, 'Front office', 'b')],
            'nodes': [node('rtr', 'router', 110, 80, 'Router', 'uplink'),
                      node('sw', 'switch', 110, 230, 'FO-SW', 'select to configure', 'fosw'),
                      node('ph1', 'phone', 330, 80, 'FO-1', 'Gi1/0/2'), node('pc1', 'pc', 450, 80, 'Desk PC'),
                      node('ph2', 'phone', 330, 160, 'FO-2', 'Gi1/0/3'), node('pc2', 'pc', 450, 160, 'Desk PC'),
                      node('ap1', 'ap', 600, 80, 'AP-Lobby', 'Gi1/0/4'), node('ap2', 'ap', 600, 200, 'AP-Office', 'Gi1/0/5'),
                      node('prn', 'printer', 330, 260, 'FO-PRN', 'Gi1/0/6')],
            'links': [link('rtr', 'sw'), link('sw', 'ph1'), link('ph1', 'pc1'), link('sw', 'ph2'), link('ph2', 'pc2'),
                      link('sw', 'ap1'), link('sw', 'ap2'), link('sw', 'prn')]}}],
        'panels': {'fosw': panel('FO-SW (access switch)', ('Ports', [grid('FO-SW port table', cols, rows)]), ('VLANs', [vlans]))},
        'explanation': [
            'A phone with a PC behind it uses an access port with two VLANs: the access (data) VLAN 10 for the PC\'s untagged '
            'frames and the voice VLAN 50, which the phone tags (learned through CDP/LLDP). FO-2 had the two swapped. The printer '
            'has no phone, so its port should not carry a voice VLAN.',
            'An access point that serves several SSIDs needs an 802.1Q trunk. Its management traffic is untagged, so the native '
            'VLAN is 99, and the allowed list is 10, 60 and 99 (not 50: no phones on Wi-Fi, and not 1). AP-Lobby was an access '
            'port in the guest VLAN, which would put the AP and both SSIDs on guest; AP-Office had native VLAN 1 and was missing VLAN 60.',
            'Unused ports are disabled (port security). The router uplink was already correct.'],
    }

def build():
    return [replaced(), front_office()]

"""Type 8, monitoring dashboard (modelled on ExamTopics N10-008 #753): read dashboard tabs (tables and bar widgets)
and answer the questions under them. Every answer is supported by exactly one piece of evidence on the dashboard."""
import ipaddress
from lib import *

def bars(title, series, wide=False):
    b = {'kind': 'bars', 'title': title, 'series': series}
    if wide: b['wide'] = True
    return b

def bar(label, value, unit='%', max=100, tone=None, text=None):
    s = {'label': label, 'value': value, 'unit': unit, 'max': max}
    if tone: s['tone'] = tone
    if text: s['text'] = text
    return s

def wide(block):
    return {**block, 'wide': True}

def tone(v, warn, crit):
    return 'r' if v >= crit else 'c' if v >= warn else 'b'

# ── A: after a power outage (like #753) ────────────────────────────────────
def outage():
    wan = [['WAN1', '10 Gb/s', '412 Mb/s', '2.51 %', '24 ms', '9.5 ms'],
           ['WAN2', '1 Gb/s', '96 Mb/s', '0.01 %', '11 ms', '3.9 ms']]
    devices = [('Router A', 'Up', 31, 44), ('Router B', 'Up', 22, 40), ('Switch A', 'Up', 18, 35), ('Switch B', 'Up', 24, 37),
               ('WAP1', 'Up', 63, 58), ('WAP2', 'Down', None, None), ('Wireless controller', 'Up', 41, 52),
               ('DHCP server', 'Up', 12, 46), ('Web server', 'Up', 38, 61), ('App server', 'Up', 47, 64)]
    talkers = [('203.0.113.45', 'external (cloud backup provider)', '104.7 GB'), ('10.1.90.53', 'internal', '80.9 GB'),
               ('10.1.90.55', 'internal', '74.7 GB'), ('10.1.59.81', 'internal', '3.0 GB'), ('10.1.99.22', 'internal', '2.1 GB'),
               ('10.1.99.14', 'internal', '2.1 GB')]
    biggest_internal = max((t for t in talkers if ipaddress.ip_address(t[0]) in ipaddress.ip_network('10.1.0.0/16')),
                           key=lambda t: float(t[2].split()[0]))[0]
    down = [d[0] for d in devices if d[1] == 'Down']
    assert down == ['WAP2'] and biggest_internal == '10.1.90.53'
    dev_options = [d[0] for d in devices]
    ip_options = sorted({t[0] for t in talkers}, key=ipaddress.ip_address)
    causes = ['Duplex mismatch on the app server\'s switch port', 'Packet loss on WAN1', 'High CPU on Router A',
              'DHCP scope exhaustion', 'A switching loop on Switch A', 'The app server is low on memory']
    return {
        'id': 'pbq-dash-outage', 'type': 'dashboard', 'title': 'Monitoring after a power outage',
        'objectives': ['3.1', '3.2', '5.3'],
        'scenario': ['Power failed at 02:14 last night and was restored at 02:20. Since then users report that the '
                     'application server is slow, and users in the east wing have weak or no Wi-Fi. The network '
                     'monitoring dashboard is shown below.'],
        'requirements': ['Open each dashboard tab and review the widgets',
                         'Answer every question under the dashboard'],
        'instructions': 'Use the tabs above the dashboard to switch views. The questions stay visible below it.',
        'views': [
            {'label': 'Network health', 'widgets': [
                wide(table('WAN uplinks (last 24 hours)', ['Uplink', 'Speed', 'Avg throughput', 'Loss', 'Avg latency', 'Jitter'], wan)),
                bars('WAN availability (24 h)', [bar('WAN1', 98.9, tone='b'), bar('WAN2', 100, tone='b')]),
                table('VoIP guidelines', ['Metric', 'Limit'], [['One-way latency', '≤ 150 ms'], ['Jitter', '≤ 30 ms'],
                                                              ['Packet loss', '≤ 1 %']])]},
            {'label': 'Device monitoring', 'widgets': [
                wide(table('Device status', ['Device', 'Status', 'CPU', 'Memory', 'Last change'],
                           [[n, s, f'{c} %' if c is not None else '—', f'{m} %' if m is not None else '—',
                             'down since 02:14' if s == 'Down' else 'rebooted 02:20'] for n, s, c, m in devices])),
                wide(table('Top hosts by traffic (24 h)', ['Host', 'Location', 'Bytes'], [list(t) for t in talkers]))]},
            {'label': 'Interfaces', 'widgets': [
                wide(table('Switch A ports of interest (since 02:20)',
                           ['Port', 'Connected to', 'Speed / duplex', 'CRC errors', 'Late collisions', 'Utilization'],
                           [['Gi1/0/10', 'App server', '100 Mb/s half (auto)', '0', '12,440', '97 %'],
                            ['Gi1/0/11', 'Web server', '1 Gb/s full (auto)', '0', '0', '14 %'],
                            ['Gi1/0/24', 'WAP2', 'no link (PoE: power denied)', '—', '—', '—']])),
                text('The app server NIC is hard-coded to 100 Mb/s full duplex. WAP1 covers the west wing and WAP2 the east wing.')]}],
        'questions': [fields('Questions',
            sel('d1_wan', 'Which WAN uplink should be preferred for VoIP traffic?', ['WAN1', 'WAN2'], 'WAN2', width='l'),
            sel('d1_dev', 'Which device explains the east-wing Wi-Fi problem?', dev_options, 'WAP2', width='l'),
            sel('d1_app', 'What is the most likely cause of the slow application server?', causes, causes[0], width='l'),
            sel('d1_top', 'Which internal host is generating the most traffic?', ip_options, biggest_internal, width='l'))],
        'explanation': [
            'VoIP needs low loss, latency and jitter more than bandwidth. WAN1 has more capacity but 2.51 % loss, above the 1 % '
            'guideline; WAN2 has 0.01 % loss, 11 ms latency and 3.9 ms jitter, so it should carry voice.',
            'WAP2 has been down since 02:14 and its switch port shows PoE power denied, which is why the east wing has weak or no Wi-Fi (clients there reach only the distant WAP1). '
            'Every other device is up.',
            'After the outage the app server\'s switch port came back on auto-negotiation. Facing a NIC hard-coded to 100 Mb/s '
            'full duplex (which does not negotiate), it detected 100 Mb/s but fell back to half duplex: a duplex mismatch. Late collisions are its signature, and the port is saturated at 97 %.',
            '203.0.113.45 sends the most bytes, but it is an external host (the backup provider), not one of ours. The busiest '
            'internal host is 10.1.90.53.'],
    }

# ── B: school network on a Monday morning ─────────────────────────────────
def school():
    util = [('Gi1/0/48 (uplink to core)', 98), ('Gi1/0/12 (Lab PC 12)', 4), ('Gi1/0/5 (Room 104 wall jack A)', 61),
            ('Gi1/0/6 (Room 104 wall jack B)', 59), ('Gi1/0/20 (AP3)', 22), ('Gi1/0/2 (Library printer)', 1)]
    errs = [['Gi1/0/48', '10 Gb/s full', '0', '0', '0'], ['Gi1/0/12', '1 Gb/s full', '18,442', '0', '0'],
            ['Gi1/0/5', '1 Gb/s full', '0', '0', '0'], ['Gi1/0/6', '1 Gb/s full', '0', '0', '0'],
            ['Gi1/0/20', '1 Gb/s full', '0', '0', '0']]
    mac = '00a0.c914.2b7e'
    log = '\n'.join([
        f'08:12:41 %SW_MATM-4-MACFLAP_NOTIF: Host {mac} in vlan 20 is flapping between port Gi1/0/5 and port Gi1/0/6',
        f'08:12:44 %SW_MATM-4-MACFLAP_NOTIF: Host {mac} in vlan 20 is flapping between port Gi1/0/6 and port Gi1/0/5',
        '08:12:52 %SW_MATM-4-MACFLAP_NOTIF: Host 0050.56a1.0c33 in vlan 20 is flapping between port Gi1/0/5 and port Gi1/0/6',
        '08:13:05 %SYS-5-CONFIG_I: Configured from console by admin on vty0 (10.20.99.5)',
        '08:13:30 %LINK-3-UPDOWN: Interface Gi1/0/31, changed state to up'])
    aps = [('AP1', 'Library', '1', 34, 38, 22), ('AP2', 'Gym', '6', 41, 36, 25), ('AP3', 'Science wing', '6', 87, 34, 24),
           ('AP4', 'Cafeteria', '11', 39, 37, 31)]
    chans = [a[2] for a in aps]
    shared = sorted({c for c in chans if chans.count(c) > 1})
    assert shared == ['6'] and max(aps, key=lambda a: a[3])[0] == 'AP3'
    assert max(util, key=lambda u: u[1])[0].startswith('Gi1/0/48')
    ports = ['Gi1/0/2', 'Gi1/0/5', 'Gi1/0/6', 'Gi1/0/12', 'Gi1/0/20', 'Gi1/0/48']
    log_causes = ['A switching loop', 'A duplex mismatch', 'DHCP scope exhaustion', 'A rogue DHCP server',
                  'ARP spoofing']
    wifi_causes = ['Co-channel interference', 'Low signal-to-noise ratio', 'Too many clients for one AP',
                   'Wrong SSID', 'The AP is on the wrong band']
    return {
        'id': 'pbq-dash-school', 'type': 'dashboard', 'title': 'School network health check',
        'objectives': ['3.1', '3.2', '5.2', '5.4'],
        'scenario': ['On Monday morning teachers report that everything is slow, a computer lab PC keeps losing its '
                     'connection, and Wi-Fi in the science wing is sluggish even close to the access point. Use the '
                     'monitoring dashboard for the main building switch and wireless network.'],
        'requirements': ['Open each dashboard tab and review the widgets', 'Answer every question under the dashboard'],
        'instructions': 'Use the tabs above the dashboard to switch views. The questions stay visible below it.',
        'views': [
            {'label': 'Interfaces', 'widgets': [
                wide(bars('Utilization (5-minute average)', [bar(n, v, tone=tone(v, 70, 90)) for n, v in util])),
                wide(table('Interface errors (since Monday 07:00)', ['Port', 'Speed / duplex', 'CRC errors', 'Late collisions',
                                                                       'Output drops'], errs))]},
            {'label': 'Syslog', 'widgets': [wide(pre('Main switch log (newest last)', log))]},
            {'label': 'Wireless', 'widgets': [
                wide(table('Access points (2.4 GHz radio)', ['AP', 'Location', 'Channel', 'Channel utilization', 'SNR', 'Clients'],
                           [[a, l, c, f'{u} %', f'{snr} dB', str(n)] for a, l, c, u, snr, n in aps])),
                text('AP2 (gym) and AP3 (science wing) are on either side of a shared wall. All APs allow up to 60 clients.')]}],
        'questions': [fields('Questions',
            sel('d2_util', 'Which port is the bottleneck making everything slow?', ports, 'Gi1/0/48', width='l'),
            sel('d2_phys', 'Which port has a physical-layer (cabling) problem?', ports, 'Gi1/0/12', width='l'),
            sel('d2_log', 'What do the syslog messages indicate?', log_causes, 'A switching loop', width='l'),
            sel('d2_wifi', 'What is the most likely cause of the slow science-wing Wi-Fi?', wifi_causes,
                'Co-channel interference', width='l'))],
        'explanation': [
            'The uplink to the core, Gi1/0/48, is at 98 % utilization, so everything that leaves the building queues behind it. '
            'Gi1/0/12 (the lab PC) has thousands of CRC errors at full duplex with no late collisions: corrupted frames from a '
            'bad cable or connector, not a duplex mismatch.',
            'The same MAC addresses flapping between Gi1/0/5 and Gi1/0/6 (two wall jacks in room 104, both busy at about 60 %) '
            'means frames loop between them: someone has connected the two jacks, for example through a small switch. That '
            'is a switching loop. The config message is a normal admin login.',
            'AP3 shares channel 6 with AP2 on the other side of the wall, and its channel utilization is 87 %. SNR (34 dB) '
            'and the client count (24 of 60) are fine, so the cause is co-channel interference: move AP3 to a free '
            'non-overlapping channel.'],
    }

def build():
    return [outage(), school()]

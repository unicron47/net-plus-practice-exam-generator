"""Type 1, wireless deployment (modelled on ExamTopics N10-008 #6): configure three APs."""
from lib import *

CH24 = [str(c) for c in range(1, 12)]
SEC = ['None', 'WEP', 'WPA (TKIP)', 'WPA2-Personal (AES)', 'WPA2-Enterprise', 'WPA3-Personal']

def ap_ids(p, i):
    return {k: f'{p}{i}_{k}' for k in ('ip', 'mask', 'gw', 'ssid', 'bc', 'band', 'mode', 'ch', 'w', 'sec', 'psk',
                                        'rad', 'port', 'secret', 'spd', 'dup')}

def warehouse():
    sub, gw, swip = '10.20.30.0/28', host('10.20.30.0/28', 1), host('10.20.30.0/28', 2)
    panels, chans = {}, []
    for i in (1, 2, 3):
        f = ap_ids('wa', i)
        chans.append(f['ch'])
        panels[f'ap{i}'] = panel(f'AP{i} configuration',
            ('Basic', [kv([['Access point name', f'AP{i}'], ['Uplink', f'SW1 Gi1/0/{i + 1}']]),
                       fields('Addressing',
                              txt(f['ip'], 'IP address', {'ip': sub, 'exclude': [gw, swip], 'unique': 'wa'},
                                  placeholder='x.x.x.x', solution=f'any unused host in {sub} (10.20.30.3–14)'),
                              txt(f['mask'], 'Subnet mask', {'mask': 28}, placeholder='255.255.255.x'),
                              txt(f['gw'], 'Default gateway', gw)),
                       fields('Network name',
                              txt(f['ssid'], 'SSID', {'exact': 'WH-Scanners'}),
                              seg(f['bc'], 'SSID broadcast', ['Yes', 'No'], 'Yes'))]),
            ('Wireless', [fields('Radio',
                              sel(f['mode'], 'Mode', ['802.11a', '802.11b', '802.11g', '802.11ac'], '802.11g'),
                              sel(f['ch'], 'Channel', CH24, '1')),
                          fields('Security',
                              sel(f['sec'], 'Security', SEC, 'WPA2-Personal (AES)', width='l'),
                              txt(f['psk'], 'Key or passphrase', {'exact': 'Pallet#Scan24'}))]),
            ('Wired', [fields('Uplink port',
                              seg(f['spd'], 'Speed', ['Auto', '100', '1000'], '100'),
                              seg(f['dup'], 'Duplex', ['Auto', 'Half', 'Full'], 'Full'))]))
    panels['sw1'] = panel('SW1 (access switch)', [kv([['Management IP', f'{swip}/28'], ['Gateway', gw],
        ['Gi1/0/2–4 (AP uplinks)', '100 Mbps, full duplex (hard-coded)'], ['VLAN', '30 (warehouse)']])])
    return {
        'id': 'pbq-wlan-warehouse', 'type': 'wireless', 'title': 'Warehouse wireless rollout',
        'objectives': ['2.3', '1.4', '4.1'],
        'scenario': ['A distribution center is adding three access points so handheld barcode scanners can reach the '
                     'inventory system. The router (10.20.30.1) and switch SW1 (10.20.30.2) are already configured.'],
        'requirements': ['The SSID must be WH-Scanners, it must appear in the scanners\' network list, and the key is Pallet#Scan24',
                         'The scanners support only 802.11g, and WPA2 with a pre-shared key (not WPA3); use the strongest security they support',
                         'The three access points must not interfere with each other',
                         'The access point subnet is sized for at most 14 devices',
                         'Match the AP uplinks to the switch ports to avoid a duplex mismatch'],
        'instructions': 'Select each access point and the switch to review and change their settings. Changes save automatically.',
        'views': [{'label': 'Warehouse floor', 'diagram': {
            'w': 760, 'h': 330,
            'zones': [zone(16, 16, 728, 298, 'Warehouse floor', 'd')],
            'nodes': [node('sw1', 'switch', 120, 250, 'SW1', '10.20.30.2', 'sw1'),
                      node('rtr', 'router', 120, 110, 'Router', '10.20.30.1'),
                      node('ap1', 'ap', 330, 110, 'AP1', None, 'ap1'),
                      node('ap2', 'ap', 500, 110, 'AP2', None, 'ap2'),
                      node('ap3', 'ap', 670, 110, 'AP3', None, 'ap3')],
            'links': [link('rtr', 'sw1'), link('sw1', 'ap1', 'Gi1/0/2'), link('sw1', 'ap2', 'Gi1/0/3'), link('sw1', 'ap3', 'Gi1/0/4')]}}],
        'panels': panels,
        'groups': [{'kind': 'distinct', 'fields': chans, 'values': ['1', '6', '11'],
                    'solution': '1, 6 and 11 in any order (one each)'}],
        'explanation': [
            'In 2.4 GHz only channels 1, 6 and 11 do not overlap, so each AP takes a different one of them. 802.11g is the only '
            '2.4 GHz option the scanners can join (802.11a and 802.11ac are 5 GHz; 802.11b is slower).',
            'At most 14 devices means a /28 (255.255.255.240, 16 addresses, 14 usable). The APs need unused hosts from '
            '10.20.30.3 to 10.20.30.14, because .1 is the router and .2 is SW1; the gateway is the router.',
            'WPA2-Personal (AES) is the strongest option the scanners support; WEP and TKIP are deprecated. The switch ports are '
            'hard-coded to 100 Mb/s full duplex, so they do not negotiate. An AP left on auto would detect 100 Mb/s but fall back '
            'to half duplex: a duplex mismatch. Set the AP to 100/Full to match.'],
    }

def clinic():
    sub, gw, rad = '172.16.60.0/27', host('172.16.60.0/27', 1), '172.16.50.10'
    panels, chans = {}, []
    for i in (1, 2, 3):
        f = ap_ids('cl', i)
        chans.append(f['ch'])
        panels[f'ap{i}'] = panel(f'CL-AP{i} configuration',
            ('Basic', [kv([['Access point name', f'CL-AP{i}']]),
                       fields('Management addressing',
                              txt(f['ip'], 'IP address', {'ip': sub, 'exclude': [gw], 'unique': 'cl'},
                                  placeholder='x.x.x.x', solution=f'any unused host in {sub} (172.16.60.2–30)'),
                              txt(f['mask'], 'Subnet mask', {'mask': 27}, placeholder='255.255.255.x'),
                              txt(f['gw'], 'Default gateway', gw)),
                       fields('Network name',
                              txt(f['ssid'], 'SSID', {'exact': 'Clinic-Staff'}),
                              seg(f['bc'], 'SSID broadcast', ['Yes', 'No'], 'Yes'))]),
            ('Radio', [fields('Radio',
                              seg(f['band'], 'Band', ['2.4 GHz', '5 GHz'], '5 GHz'),
                              sel(f['mode'], 'Mode', ['802.11g', '802.11n', '802.11ac', '802.11ax'], '802.11ax'),
                              sel(f['ch'], 'Channel', ['1', '6', '11', '36', '40', '44', '48', '52', '56', '100', '149'], '36'),
                              seg(f['w'], 'Channel width', ['20 MHz', '40 MHz', '80 MHz'], '20 MHz'))]),
            ('Security', [fields('Authentication',
                              sel(f['sec'], 'Security', SEC, 'WPA2-Enterprise', width='l'),
                              txt(f['rad'], 'RADIUS server', rad),
                              sel(f['port'], 'RADIUS authentication port', ['49', '389', '636', '1812', '1813'], '1812'),
                              txt(f['secret'], 'Shared secret', {'exact': 'Rad1us-Clinic'}))]))
    panels['nps'] = panel('NPS1 (RADIUS server)', [kv([['IP address', rad], ['Service', 'RADIUS authentication and accounting'],
        ['Clients', '172.16.60.0/27 (access points)'], ['Shared secret for AP clients', 'Rad1us-Clinic']])])
    return {
        'id': 'pbq-wlan-clinic', 'type': 'wireless', 'title': 'Clinic staff Wi-Fi with 802.1X',
        'objectives': ['2.3', '4.1', '1.4'],
        'scenario': ['A medical clinic is replacing its wireless network. Staff must sign in with their own directory accounts, '
                     'and the RADIUS server NPS1 is already running. The access point management VLAN uses the subnet '
                     '172.16.60.0/27 with its gateway at 172.16.60.1.'],
        'requirements': ['SSID Clinic-Staff, visible to staff devices',
                         'Users authenticate individually through NPS1; some staff devices do not support WPA3',
                         'All staff devices support Wi-Fi 6; use the 5 GHz band only',
                         'Use only non-overlapping UNII-1 channels (36–48) at a width that lets all three APs use different channels',
                         'Each AP needs a management address in the AP subnet'],
        'instructions': 'Select each access point (and NPS1 for its details) to configure the network. Changes save automatically.',
        'views': [{'label': 'Clinic floor', 'diagram': {
            'w': 760, 'h': 340,
            'zones': [zone(16, 16, 470, 308, 'Patient wing', 'a'), zone(500, 16, 244, 308, 'Server room', 'c')],
            'nodes': [node('ap1', 'ap', 110, 110, 'CL-AP1', None, 'ap1'), node('ap2', 'ap', 250, 110, 'CL-AP2', None, 'ap2'),
                      node('ap3', 'ap', 390, 110, 'CL-AP3', None, 'ap3'), node('sw', 'switch', 250, 260, 'SW-CLINIC', gw),
                      node('nps', 'server', 620, 110, 'NPS1', rad, 'nps'), node('core', 'router', 620, 260, 'Core', '')],
            'links': [link('sw', 'ap1'), link('sw', 'ap2'), link('sw', 'ap3'), link('sw', 'core'), link('core', 'nps')]}}],
        'panels': panels,
        'groups': [{'kind': 'distinct', 'fields': chans, 'values': ['36', '40', '44', '48'],
                    'solution': 'three different channels from 36, 40, 44, 48'}],
        'explanation': [
            'Individual sign-in through RADIUS is 802.1X, which is WPA2-Enterprise (or WPA3-Enterprise, not offered here). '
            'WPA3-Personal and WPA2-Personal use one shared key. RADIUS authentication uses UDP 1812 (1813 is accounting).',
            '802.11ax (Wi-Fi 6) on 5 GHz is the fastest option every staff device supports. UNII-1 has four non-overlapping '
            '20 MHz channels (36, 40, 44, 48); at 40 or 80 MHz the three APs would have to share spectrum.',
            'A /27 is 255.255.255.224, with hosts 172.16.60.1–30; .1 is the gateway, so each AP takes a different unused host.'],
    }

def build():
    return [warehouse(), clinic()]

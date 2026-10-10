"""Type 2, network design (modelled on ExamTopics N10-008 #43): place servers/devices into zones
and choose each zone's subnet."""
from lib import *

SERVERS = [('dns', 'DNS server'), ('dhcp', 'DHCP server'), ('web', 'Web server'), ('ftp', 'FTP server'),
           ('sftp', 'SFTP server'), ('mail', 'Mail server (SMTP)'), ('ssh', 'SSH server'), ('telnet', 'Telnet server'),
           ('syslog', 'Syslog server'), ('radius', 'RADIUS server'), ('ntp', 'NTP server'), ('nvr', 'Video recorder (NVR)')]
DEVICES = [('ws', 'Workstation', 'pc'), ('laptop', 'Laptop', 'laptop'), ('wap', 'Wireless AP', 'ap'),
           ('voip', 'VoIP phone', 'phone'), ('printer', 'Printer', 'printer'), ('cam', 'IP camera', 'camera')]
PALETTE = {'reusable': True, 'tabs': [
    {'label': 'Servers', 'tokens': [{'id': i, 'label': l, 'icon': 'server'} for i, l in SERVERS]},
    {'label': 'Devices', 'tokens': [{'id': i, 'label': l, 'icon': ic} for i, l, ic in DEVICES]}]}

def slots(zone_id, xy):
    return [{'id': f'{zone_id}{n}', 'x': x, 'y': y, 'zone': zone_id} for n, (x, y) in enumerate(xy, 1)]

def subnet_fields(prefix, zones, options):
    return {'kind': 'fields', 'title': 'Zone subnets',
            'fields': [sel(f'{prefix}_{zid}', label, options, ans) for zid, label, ans in zones]}

def campus():
    dmz, bldg, dc = '203.0.113.0/29', '10.40.8.0/26', '172.20.5.0/28'
    assert smallest_prefix(4) == 29 and smallest_prefix(50) == 26 and smallest_prefix(13) == 28
    options = ['203.0.113.0/24', '203.0.113.0/28', '203.0.113.0/29', '203.0.113.0/30', '203.0.113.8/29',
               '10.40.8.0/24', '10.40.8.0/25', '10.40.8.0/26', '10.40.8.0/27', '10.40.8.64/26',
               '172.20.5.0/27', '172.20.5.0/28', '172.20.5.0/29', '172.20.5.16/28']
    return {
        'id': 'pbq-design-campus', 'type': 'design', 'title': 'Campus network build-out',
        'objectives': ['1.6', '1.8', '1.5', '4.3'],
        'scenario': ['A college is reorganizing three network zones behind its firewall. Place the right servers and devices '
                     'in each zone and choose each zone\'s subnet: the smallest one that contains the zone\'s gateway '
                     'address and has enough usable addresses.'],
        'requirements': ['Screened subnet: publish the college website over HTTPS and accept inbound email. Four addresses are '
                         'needed in total, including the gateway 203.0.113.1',
                         'Building B: add three workstations for new staff and a wireless access point for laptops, and replace '
                         'the Telnet server with a secure remote-administration server. Plan for 50 hosts; gateway 10.40.8.1',
                         'Data center: provide name resolution, central log collection and time synchronization. Plan for '
                         '13 hosts; gateway 172.20.5.1'],
        'instructions': 'Select an object in the palette, then select an empty slot to place it; select a placed object to remove it. '
                        'Objects can be used more than once and not every slot needs to be filled. Then choose each zone\'s subnet.',
        'views': [{'label': 'Network', 'diagram': {
            'w': 780, 'h': 500,
            'zones': [zone(14, 14, 360, 200, 'Screened subnet', 'c'), zone(404, 14, 362, 472, 'Building B', 'b'),
                      zone(14, 286, 360, 200, 'Data center', 'a')],
            'nodes': [node('fw', 'firewall', 194, 250, 'Firewall', None), node('proxy', 'server', 80, 120, 'Reverse proxy', '203.0.113.2'),
                      node('dmzgw', 'switch', 200, 60, 'DMZ switch', '203.0.113.1'),
                      node('bgw', 'switch', 470, 250, 'Bldg B switch', '10.40.8.1'),
                      node('telnet', 'server', 700, 80, 'Telnet server', 'to retire'),
                      node('dcgw', 'switch', 200, 330, 'DC switch', '172.20.5.1'),
                      node('dhcp', 'server', 80, 430, 'DHCP server', None)],
            'links': [link('fw', 'dmzgw'), link('fw', 'bgw'), link('fw', 'dcgw'), link('dmzgw', 'proxy'), link('bgw', 'telnet'),
                      link('dcgw', 'dhcp')],
            'slots': slots('dmz', [(190, 150), (300, 150), (300, 100)]) +
                     slots('bldg', [(600, 160), (600, 220), (600, 280), (600, 340), (600, 400), (700, 450)]) +
                     slots('dc', [(190, 430), (300, 430), (300, 380), (300, 330)])},
            'blocks': [subnet_fields('cp', [('dmz', 'Screened subnet', dmz), ('bldg', 'Building B', bldg),
                                            ('dc', 'Data center', dc)], options)]}],
        'palette': PALETTE,
        'dragdrop': {'zones': [{'id': 'dmz', 'label': 'Screened subnet', 'expect': ['web', 'mail']},
                               {'id': 'bldg', 'label': 'Building B', 'expect': ['ws', 'ws', 'ws', 'wap', 'ssh']},
                               {'id': 'dc', 'label': 'Data center', 'expect': ['dns', 'syslog', 'ntp']}]},
        'explanation': [
            'Public services belong in the screened subnet: a web server for HTTPS (443) and a mail server for inbound SMTP (25). '
            'Telnet sends credentials in clear text; SSH (22) replaces it. DNS (53), syslog (514) and NTP (123) are internal '
            'infrastructure, so they go in the data center.',
            'Subnet sizing: usable hosts = 2^(32−prefix) − 2. Four hosts need a /29 (6 usable), 50 hosts a /26 (62), and 13 '
            'hosts a /28 (14). The subnet must also contain the gateway: 203.0.113.8/29 and 10.40.8.64/26 do not, and '
            '/30, /27 and /29 are too small for their zones.'],
    }

def branch():
    guest, cams, staff = '192.168.50.0/25', '10.9.0.32/27', '10.9.1.0/24'
    assert smallest_prefix(100) == 25 and smallest_prefix(20) == 27 and smallest_prefix(200) == 24
    options = ['192.168.50.0/24', '192.168.50.0/25', '192.168.50.0/26', '192.168.50.128/25',
               '10.9.0.0/26', '10.9.0.0/27', '10.9.0.32/27', '10.9.0.32/28',
               '10.9.0.0/23', '10.9.1.0/24', '10.9.1.0/25', '10.9.1.0/26']
    return {
        'id': 'pbq-design-branch', 'type': 'design', 'title': 'New branch office design',
        'objectives': ['1.6', '1.8', '2.3', '4.1'],
        'scenario': ['A new branch office needs three segments plus a small server closet. Place the servers and devices '
                     'the requirements call for and choose each segment\'s subnet: the smallest that contains its gateway and '
                     'fits the planned hosts.'],
        'requirements': ['Guest Wi-Fi: two access points for visitors; up to 100 clients; gateway 192.168.50.1',
                         'Security: three IP cameras and a device that records their video; 20 hosts planned; gateway 10.9.0.33',
                         'Staff LAN: two desk phones and a shared printer; 200 hosts planned; gateway 10.9.1.1',
                         'Server closet (no subnet to choose): automatic addressing for every segment, and 802.1X authentication for the staff LAN\'s switch ports'],
        'instructions': 'Select an object, then select an empty slot to place it; select a placed object to remove it. Objects can be '
                        'used more than once and not every slot needs to be filled. Then choose the subnets.',
        'views': [{'label': 'Branch', 'diagram': {
            'w': 780, 'h': 470,
            'zones': [zone(14, 14, 360, 200, 'Guest Wi-Fi', 'c'), zone(404, 14, 362, 200, 'Security', 'd'),
                      zone(14, 256, 360, 200, 'Staff LAN', 'b'), zone(404, 256, 362, 200, 'Server closet', 'a')],
            'nodes': [node('rtr', 'router', 389, 235, 'Branch router', None),
                      node('gsw', 'switch', 90, 70, 'Guest switch', '192.168.50.1'),
                      node('csw', 'switch', 480, 70, 'Camera switch', '10.9.0.33'),
                      node('ssw', 'switch', 90, 310, 'Staff switch', '10.9.1.1'),
                      node('vsw', 'switch', 480, 310, 'Server switch', None)],
            'links': [link('rtr', 'gsw'), link('rtr', 'csw'), link('rtr', 'ssw'), link('rtr', 'vsw')],
            'slots': slots('guest', [(200, 80), (300, 80), (250, 150)]) +
                     slots('sec', [(600, 70), (700, 70), (600, 150), (700, 150), (500, 170)]) +
                     slots('staff', [(200, 330), (300, 330), (200, 400), (300, 400)]) +
                     slots('srv', [(610, 320), (710, 320), (610, 400), (710, 400)])},
            'blocks': [subnet_fields('br', [('guest', 'Guest Wi-Fi', guest), ('sec', 'Security', cams),
                                            ('staff', 'Staff LAN', staff)], options)]}],
        'palette': PALETTE,
        'dragdrop': {'zones': [{'id': 'guest', 'label': 'Guest Wi-Fi', 'expect': ['wap', 'wap']},
                               {'id': 'sec', 'label': 'Security', 'expect': ['cam', 'cam', 'cam', 'nvr']},
                               {'id': 'staff', 'label': 'Staff LAN', 'expect': ['voip', 'voip', 'printer']},
                               {'id': 'srv', 'label': 'Server closet', 'expect': ['dhcp', 'radius']}]},
        'explanation': [
            'A network video recorder (NVR) stores the IP cameras\' video. DHCP hands out addresses to every segment (with '
            'relay on the router), and RADIUS is the authentication server behind 802.1X.',
            'Usable hosts = 2^(32−prefix) − 2: 100 clients need a /25 (126), 20 hosts a /27 (30) and 200 hosts a /24 (254). '
            'Gateway 10.9.0.33 sits in 10.9.0.32/27 (.32–.63), not 10.9.0.0/27 (.0–.31); a /28 holds only 14 hosts. '
            '192.168.50.128/25 does not contain .1, and 10.9.0.0/23 contains 10.9.1.1 but is larger than needed.'],
    }

def build():
    return [campus(), branch()]

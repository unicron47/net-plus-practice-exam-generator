"""Type 5, router ACL (modelled on ExamTopics N10-008 #462): complete a rule table from written requirements.
The expected rules are permits that do not overlap, followed by a deny-all, so their order does not matter and the
rowset grader can compare them as a set (the last rule is fixed)."""
from lib import *

SERVICES = ['SSH (TCP 22)', 'Telnet (TCP 23)', 'HTTP (TCP 80)', 'HTTPS (TCP 443)', 'SMB (TCP 445)', 'RDP (TCP 3389)',
            'VNC (TCP 5900)', 'DNS (UDP 53)', 'DNS (TCP 53)', 'NTP (UDP 123)', 'SNMP (UDP 161)', 'SNMP trap (UDP 162)',
            'Syslog (UDP 514)', 'Any']
ACTIONS = ['Permit', 'Deny']
FREE = {'free': True}       # rowset cells are graded by the rowset, not one by one

def acl(prefix, nets, expect):
    """nets: [(label, cidr)]; expect: rows of (source, destination, service, action) using network labels or 'Any'.
    Returns (grid block, rowset)."""
    opts = [cidr for _, cidr in nets] + ['Any']
    by = dict(nets)
    by['Any'] = 'Any'
    rows, ids, want = [], [], []
    for i, (s, d, svc, act) in enumerate(expect, 1):
        assert svc in SERVICES and act in ACTIONS
        r = [f'{prefix}{i}_{k}' for k in ('src', 'dst', 'svc', 'act')]
        ids.append(r)
        want.append([by[s], by[d], svc, act])
        rows.append([str(i),
                     {'id': r[0], 'label': f'Rule {i} source', 'type': 'select', 'options': opts, 'answer': FREE},
                     {'id': r[1], 'label': f'Rule {i} destination', 'type': 'select', 'options': opts, 'answer': FREE},
                     {'id': r[2], 'label': f'Rule {i} service', 'type': 'select', 'options': SERVICES, 'answer': FREE},
                     {'id': r[3], 'label': f'Rule {i} action', 'type': 'select', 'options': ACTIONS, 'answer': FREE}])
    g = {'kind': 'grid', 'title': 'Access control list (evaluated top to bottom, first match wins)',
         'columns': ['Rule', 'Source', 'Destination', 'Service', 'Action'], 'rows': rows}
    rs = {'label': 'ACL', 'rows': ids, 'expect': want, 'fixedLast': True}
    return g, rs

def net_table(nets):
    return table('Networks', ['Segment', 'Network'], [[l, c] for l, c in nets])

# ── A: secure remote administration ────────────────────────────────────────
def remote_admin():
    nets = [('Management', '10.0.99.0/24'), ('Users', '10.0.10.0/24'), ('Linux servers', '10.0.20.0/24'),
            ('Windows servers', '10.0.30.0/24'), ('Web servers', '10.0.40.0/24')]
    expect = [('Management', 'Linux servers', 'SSH (TCP 22)', 'Permit'),
              ('Management', 'Windows servers', 'RDP (TCP 3389)', 'Permit'),
              ('Management', 'Web servers', 'SSH (TCP 22)', 'Permit'),
              ('Users', 'Web servers', 'HTTPS (TCP 443)', 'Permit'),
              ('Any', 'Any', 'Any', 'Deny')]
    g, rs = acl('ra', nets, expect)
    return {
        'id': 'pbq-acl-remote', 'type': 'acl', 'title': 'Secure remote administration ACL',
        'objectives': ['4.3', '1.5', '4.1'],
        'scenario': ['You are writing the ACL that the core router applies to all traffic routed between the five segments '
                     'below. Both the Linux servers and the web servers run Linux; the Windows servers run Windows Server. The router '
                     'tracks connections, so return traffic for a permitted session is allowed automatically.'],
        'requirements': ['Administrators on the management network must reach every server segment using the most common secure '
                         'remote-administration protocol for that segment\'s operating system',
                         'Users must reach the web servers over encrypted web traffic only',
                         'Users must not be able to open remote-administration sessions to any server segment',
                         'Block everything that has not been specifically permitted, with an explicit final rule',
                         'Do not permit anything broader than the requirements need (no "Any" where a segment will do)'],
        'instructions': 'Select the router to open the ACL. Choose the source, destination, service and action for every rule.',
        'views': [{'label': 'Segments', 'diagram': {
            'w': 780, 'h': 380,
            'zones': [zone(14, 14, 250, 110, 'Management 10.0.99.0/24', 'a'), zone(14, 256, 250, 110, 'Users 10.0.10.0/24', 'b'),
                      zone(516, 14, 250, 110, 'Linux servers 10.0.20.0/24', 'c'),
                      zone(516, 256, 250, 110, 'Windows servers 10.0.30.0/24', 'c'),
                      zone(290, 256, 200, 110, 'Web servers 10.0.40.0/24', 'd')],
            'nodes': [node('rtr', 'router', 390, 130, 'Core router', 'select: ACL', 'acl'),
                      node('mg', 'pc', 140, 75, 'Admin PCs'), node('us', 'laptop', 140, 317, 'User PCs'),
                      node('lx', 'server', 640, 75, 'Linux'), node('win', 'server', 640, 317, 'Windows Server'),
                      node('web', 'server', 390, 317, 'Web servers')],
            'links': [link('rtr', 'mg'), link('rtr', 'us'), link('rtr', 'lx'), link('rtr', 'win'), link('rtr', 'web')]}}],
        'panels': {'acl': panel('Core router ACL', ('Rules', [g]), ('Networks', [net_table(nets)]))},
        'rowsets': [rs],
        'explanation': [
            'The most common secure remote-administration protocols are SSH (TCP 22) for Linux and RDP (TCP 3389) for Windows. '
            'Telnet and VNC are not encrypted by default. The web servers run Linux, so they are managed with SSH too.',
            'Users get HTTPS (TCP 443) to the web servers only; plain HTTP is not encrypted. Because nothing else is permitted '
            'for users, the final deny already stops their SSH and RDP sessions to the servers.',
            'Every permit names one source segment, one destination segment and one service, so none overlaps another and '
            'their order does not matter. The explicit deny any/any/any must be last: an ACL is read top to bottom and the '
            'first match wins, so a deny-all above a permit would block it.'],
    }

# ── B: UDP infrastructure services ─────────────────────────────────────────
def infra():
    nets = [('Users', '172.16.10.0/24'), ('Servers', '172.16.20.0/24'), ('Cameras', '172.16.30.0/24'),
            ('Monitoring', '172.16.99.0/24')]
    expect = [('Users', 'Servers', 'DNS (UDP 53)', 'Permit'),
              ('Users', 'Servers', 'HTTPS (TCP 443)', 'Permit'),
              ('Cameras', 'Servers', 'NTP (UDP 123)', 'Permit'),
              ('Monitoring', 'Cameras', 'SNMP (UDP 161)', 'Permit'),
              ('Cameras', 'Monitoring', 'Syslog (UDP 514)', 'Permit'),
              ('Any', 'Any', 'Any', 'Deny')]
    g, rs = acl('in', nets, expect)
    return {
        'id': 'pbq-acl-infra', 'type': 'acl', 'title': 'Branch services ACL',
        'objectives': ['4.3', '1.5', '3.2'],
        'scenario': ['A branch router routes between four segments and filters that traffic with one ACL. The DNS and '
                     'NTP servers and the intranet web server are all in the server segment; the network monitoring system is '
                     'in the monitoring segment. The router tracks connections, so return traffic for a permitted '
                     'session is allowed automatically.'],
        'requirements': ['Users must be able to resolve names with ordinary client DNS queries, and reach the intranet site '
                         'over encrypted web traffic',
                         'The IP cameras must synchronize their clocks with the NTP server',
                         'The monitoring system must poll the cameras for status and counters',
                         'The cameras must send their log messages to the monitoring system',
                         'Block everything else with an explicit final rule, and permit nothing broader than needed'],
        'instructions': 'Select the router to open the ACL. Choose the source, destination, service and action for every rule.',
        'views': [{'label': 'Segments', 'diagram': {
            'w': 780, 'h': 380,
            'zones': [zone(14, 14, 250, 110, 'Users 172.16.10.0/24', 'b'), zone(516, 14, 250, 110, 'Servers 172.16.20.0/24', 'c'),
                      zone(14, 256, 250, 110, 'Cameras 172.16.30.0/24', 'd'),
                      zone(516, 256, 250, 110, 'Monitoring 172.16.99.0/24', 'a')],
            'nodes': [node('rtr', 'router', 390, 190, 'Branch router', 'select: ACL', 'acl'),
                      node('us', 'laptop', 140, 75, 'User PCs'), node('sv', 'server', 600, 75, 'DNS / NTP'),
                      node('web', 'server', 700, 75, 'Intranet'), node('cam', 'camera', 140, 317, 'IP cameras'),
                      node('nms', 'dashboard', 640, 317, 'Monitoring')],
            'links': [link('rtr', 'us'), link('rtr', 'sv'), link('rtr', 'web'), link('rtr', 'cam'), link('rtr', 'nms')]}}],
        'panels': {'acl': panel('Branch router ACL', ('Rules', [g]), ('Networks', [net_table(nets)]))},
        'rowsets': [rs],
        'explanation': [
            'Ordinary DNS client queries use UDP 53 (TCP 53 is for zone transfers and oversized responses). NTP uses UDP 123. '
            'Encrypted web traffic is HTTPS on TCP 443.',
            'Polling devices for status and counters is SNMP: the monitoring system sends requests to UDP 161 on the cameras. '
            'Traps (UDP 162) flow the other way and are not polling. Log messages are syslog, UDP 514, from the cameras to the '
            'monitoring system.',
            'The permits do not overlap, so their order does not matter; the explicit deny-all must be the last rule because '
            'the ACL stops at the first match.'],
    }

def build():
    return [remote_admin(), infra()]

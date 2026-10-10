"""Type 6, static routing (modelled on ExamTopics N10-008 #671): read each router's routing table, decide whether it
has a problem, and add the one missing route. The tables are generated from the topology, so they always agree."""
import ipaddress
from lib import *

FREE = {'free': True}
CODES = ('Codes: L - local, C - connected, S - static, R - RIP, O - OSPF, D - EIGRP, B - BGP\n'
         '       * - candidate default')

def show_ip_route(name, ifaces, statics):
    """ifaces: {ifname: 'a.b.c.d/len'}; statics: [(cidr, next_hop)]. Returns Cisco-style 'show ip route' text."""
    entries = []                                        # (network, code, text)
    for ifn, addr in ifaces.items():
        i = ipaddress.ip_interface(addr)
        entries.append((i.network, 'C', f'{i.network} is directly connected, {ifn}'))
        entries.append((ipaddress.ip_network(f'{i.ip}/32'), 'L', f'{i.ip}/32 is directly connected, {ifn}'))
    default = None
    for cidr, nh in statics:
        n = ipaddress.ip_network(cidr)
        if n.prefixlen == 0:
            default = nh
            continue
        entries.append((n, 'S', f'{n} [1/0] via {nh}'))
    out = [f'{name}# show ip route', CODES, '',
           f'Gateway of last resort is {default} to network 0.0.0.0' if default else 'Gateway of last resort is not set', '']
    if default:
        out.append(f'S*    0.0.0.0/0 [1/0] via {default}')
    majors = {}
    for n, code, t in entries:
        first = int(str(n.network_address).split('.')[0])
        cls = 8 if first < 128 else 16 if first < 192 else 24
        majors.setdefault(ipaddress.ip_network(f'{n.network_address}/{cls}', strict=False), []).append((n, code, t))
    for major in sorted(majors):
        rows = sorted(majors[major], key=lambda r: (r[0].network_address, r[0].prefixlen))
        masks = {r[0].prefixlen for r in rows}
        if len(rows) == 1 and rows[0][0] == major:         # a lone classful route has no parent line
            out.append(f'{rows[0][1]:<6}{rows[0][2]}')
            continue
        if len(masks) == 1:
            out.append(f'      {major} is subnetted, {len(rows)} subnet{"s" if len(rows) > 1 else ""}')
        else:
            out.append(f'      {major} is variably subnetted, {len(rows)} subnets, {len(masks)} masks')
        out += [f'{code:<9}{t}' for _, code, t in rows]
    return '\n'.join(out)

def reaches(routers, src_router, dst):
    """Follow the tables hop by hop from src_router toward address dst. True if a connected route is reached."""
    d = ipaddress.ip_address(dst)
    cur, seen = src_router, set()
    while cur not in seen:
        seen.add(cur)
        r = routers[cur]
        if any(d in ipaddress.ip_interface(a).network for a in r['ifaces'].values()):
            return True
        best = None
        for cidr, nh in r['statics']:
            n = ipaddress.ip_network(cidr)
            if d in n and (best is None or n.prefixlen > best[0].prefixlen):
                best = (n, nh)
        if not best:
            return False
        nxt = [k for k, o in routers.items() if any(ipaddress.ip_interface(a).ip == ipaddress.ip_address(best[1])
                                                    for a in o['ifaces'].values())]
        if not nxt:
            return False
        cur = nxt[0]
    return False                                        # routing loop

def router_panel(rid, name, r, fault, hops):
    """fault: None, or (prefix, prefixlen, next_hop) of the route to add on this router."""
    p = rid
    problem = seg(f'{p}_prob', f'{name}: problem found?', ['Yes', 'No'], 'Yes' if fault else 'No')
    if fault:
        pre_, plen, nh = fault
        route = [txt(f'{p}_pfx', f'{name}: destination prefix', pre_, placeholder='x.x.x.x'),
                 txt(f'{p}_mask', f'{name}: prefix mask', {'mask': plen}, placeholder='255.x.x.x or /n',
                     solution=f'{mask(plen)} (/{plen})'),
                 sel(f'{p}_nh', f'{name}: next hop', hops, nh)]
    else:
        route = [txt(f'{p}_pfx', f'{name}: destination prefix', FREE, placeholder='x.x.x.x'),
                 txt(f'{p}_mask', f'{name}: prefix mask', FREE, placeholder='255.x.x.x or /n'),
                 sel(f'{p}_nh', f'{name}: next hop', hops, FREE)]
    return panel(name,
                 ('Routing table', [pre(None, show_ip_route(name, r['ifaces'], r['statics']))]),
                 ('Routing configuration', [fields('Diagnosis', problem),
                                            fields('Static route to add (only if a problem was found)', *route)]))

def fixed(routers, rid, fault):
    """The topology with the keyed route added on rid."""
    out = {k: {'ifaces': v['ifaces'], 'statics': list(v['statics'])} for k, v in routers.items()}
    pfx, plen, nh = fault
    out[rid]['statics'].append((f'{pfx}/{plen}', nh))
    return out

def hop_options(routers):
    return sorted({str(ipaddress.ip_interface(a).ip) for r in routers.values() for a in r['ifaces'].values()
                   if ipaddress.ip_interface(a).network.prefixlen == 30}, key=ipaddress.ip_address)

# ── A: two sites through a transit router (like #671) ─────────────────────
def two_sites():
    R = {'ra': {'ifaces': {'GigabitEthernet1': '10.0.5.1/24', 'GigabitEthernet2': '10.0.6.1/24',
                           'GigabitEthernet3': '172.16.27.1/30'},
                'statics': [('0.0.0.0/0', '172.16.27.2')]},
         'rc': {'ifaces': {'GigabitEthernet2': '172.16.27.2/30', 'GigabitEthernet1': '172.16.28.1/30'},
                'statics': [('10.0.6.0/24', '172.16.27.1'), ('10.0.0.0/24', '172.16.28.2'), ('10.0.1.0/24', '172.16.28.2')]},
         'rb': {'ifaces': {'GigabitEthernet1': '172.16.28.2/30', 'GigabitEthernet2': '10.0.1.1/24',
                           'GigabitEthernet3': '10.0.0.1/24'},
                'statics': [('0.0.0.0/0', '172.16.28.1')]}}
    fault = ('rc', ('10.0.5.0', 24, '172.16.27.1'))
    ws_a, fs2 = '10.0.1.20', '10.0.5.30'
    assert reaches(R, 'rb', fs2) is False and reaches(R, 'ra', '10.0.1.20') is True
    F = fixed(R, *fault)
    assert reaches(F, 'rb', fs2) and reaches(F, 'ra', ws_a)
    hops = hop_options(R)
    names = {'ra': 'Router A', 'rc': 'Router C', 'rb': 'Router B'}
    panels = {k: router_panel(k, names[k], R[k], fault[1] if k == fault[0] else None, hops) for k in R}
    return {
        'id': 'pbq-route-sites', 'type': 'routing', 'title': 'Unreachable department share',
        'objectives': ['2.2', '5.5', '1.4'],
        'scenario': [f'Users at site B, such as workstation A ({ws_a}), cannot open their department share on file server 2 '
                     f'({fs2}) at site A. Routing between the sites is static.'],
        'requirements': ['Review the routing table on each router',
                         'For each router, state whether it has a problem',
                         'Where there is a problem, add one static route, for the destination subnet, that fixes it'],
        'instructions': 'Select each router. Its first tab shows the routing table; the second is where you record a '
                        'problem and the route to add. Leave the route empty on routers that need no change.',
        'views': [{'label': 'Sites', 'diagram': {
            'w': 780, 'h': 380,
            'zones': [zone(14, 14, 300, 352, 'Site A', 'a'), zone(466, 14, 300, 352, 'Site B', 'b')],
            'nodes': [node('fs2', 'server', 90, 300, 'File server 2', '10.0.5.0/24'),
                      node('wsf', 'pc', 90, 80, 'Workstations', '10.0.6.0/24'),
                      node('ra', 'router', 240, 190, 'Router A', None, 'ra'),
                      node('rc', 'router', 390, 190, 'Router C', 'transit', 'rc'),
                      node('rb', 'router', 540, 190, 'Router B', None, 'rb'),
                      node('wsa', 'pc', 690, 80, 'Workstation A', '10.0.1.0/24'),
                      node('fs1', 'server', 690, 300, 'File server 1', '10.0.0.0/24')],
            'links': [link('fs2', 'ra', 'Gi1'), link('wsf', 'ra', 'Gi2'), link('ra', 'rc'), link('rc', 'rb'),
                      link('rb', 'wsa', 'Gi2'), link('rb', 'fs1', 'Gi3')],
            'notes': [{'x': 315, 'y': 150, 'text': '172.16.27.0/30', 'anchor': 'middle', 'mono': True},
                      {'x': 465, 'y': 150, 'text': '172.16.28.0/30', 'anchor': 'middle', 'mono': True}]}}],
        'panels': panels,
        'explanation': [
            'Router B sends everything that is not local to its default route, Router C (172.16.28.1). Router C has routes '
            'for 10.0.6.0/24, 10.0.0.0/24 and 10.0.1.0/24, but none for 10.0.5.0/24 and no default route, so it drops the '
            'traffic for file server 2.',
            'The fix on Router C is a static route to 10.0.5.0 with mask 255.255.255.0 (/24) via Router A\'s address on '
            'their shared link, 172.16.27.1. Router A already reaches site B through its default route, and Router B '
            'already reaches site A through its default route, so neither needs a change.'],
    }

# ── B: hub and spoke with a missing default route ─────────────────────────
def hub_spoke():
    R = {'hq': {'ifaces': {'GigabitEthernet0/0': '192.168.10.1/24', 'GigabitEthernet0/1': '10.255.0.1/30',
                           'GigabitEthernet0/2': '10.255.0.5/30', 'GigabitEthernet0/3': '203.0.113.2/30'},
                'statics': [('0.0.0.0/0', '203.0.113.1'), ('192.168.20.0/24', '10.255.0.2'), ('192.168.30.0/24', '10.255.0.6')]},
         'b1': {'ifaces': {'GigabitEthernet0/0': '192.168.20.1/24', 'GigabitEthernet0/1': '10.255.0.2/30'},
                'statics': [('0.0.0.0/0', '10.255.0.1')]},
         'b2': {'ifaces': {'GigabitEthernet0/0': '192.168.30.1/24', 'GigabitEthernet0/1': '10.255.0.6/30'},
                'statics': [('192.168.10.0/24', '10.255.0.5')]},
         'isp': {'ifaces': {'Gi0': '203.0.113.1/30'}, 'statics': []}}
    fault = ('b2', ('0.0.0.0', 0, '10.255.0.5'))
    web = '198.51.100.80'                        # an internet host, reached through HQ's default route
    assert reaches(R, 'b2', '192.168.10.25') and not reaches(R, 'b2', '192.168.20.25')
    assert not reaches(R, 'b2', '203.0.113.1') and reaches(R, 'b1', '192.168.10.25')
    F = fixed(R, *fault)
    assert reaches(F, 'b2', '192.168.20.25') and reaches(F, 'b2', '203.0.113.1') and reaches(F, 'b1', '192.168.30.25')
    hops = hop_options(R)
    names = {'hq': 'R-HQ', 'b1': 'R-Branch1', 'b2': 'R-Branch2'}
    panels = {k: router_panel(k, names[k], R[k], fault[1] if k == fault[0] else None, hops) for k in names}
    return {
        'id': 'pbq-route-hub', 'type': 'routing', 'title': 'Branch office routing',
        'objectives': ['2.2', '5.5'],
        'scenario': ['A company connects two branch offices to headquarters over point-to-point links; HQ has the only '
                     'internet connection. Branch 2 users (192.168.30.0/24) can reach the HQ servers (192.168.10.0/24), but not '
                     f'Branch 1 or internet sites such as {web}. Branch 1 users can reach HQ and the internet. Routing is static.'],
        'requirements': ['Review the routing table on each router',
                         'For each router, state whether it has a problem',
                         'Where there is a problem, add the single static route that restores all of the missing access'],
        'instructions': 'Select each router. Its first tab shows the routing table; the second is where you record a '
                        'problem and the route to add. Leave the route empty on routers that need no change.',
        'views': [{'label': 'WAN', 'diagram': {
            'w': 780, 'h': 380,
            'zones': [zone(250, 14, 280, 170, 'Headquarters', 'a'), zone(14, 220, 300, 146, 'Branch 1', 'b'),
                      zone(466, 220, 300, 146, 'Branch 2', 'b')],
            'nodes': [node('inet', 'cloud', 680, 70, 'Internet', 'via ISP 203.0.113.1'),
                      node('srv', 'server', 320, 70, 'HQ servers', '192.168.10.0/24'),
                      node('hq', 'router', 460, 110, 'R-HQ', None, 'hq'),
                      node('b1', 'router', 230, 290, 'R-Branch1', None, 'b1'),
                      node('b2', 'router', 550, 290, 'R-Branch2', None, 'b2'),
                      node('u1', 'pc', 90, 290, 'Users', '192.168.20.0/24'),
                      node('u2', 'pc', 690, 290, 'Users', '192.168.30.0/24')],
            'links': [link('srv', 'hq'), link('hq', 'inet'), link('hq', 'b1', '10.255.0.0/30'), link('hq', 'b2', '10.255.0.4/30'),
                      link('b1', 'u1'), link('b2', 'u2')]}}],
        'panels': panels,
        'explanation': [
            'R-Branch2 has a route only for the HQ server subnet and no default route ("Gateway of last resort is not set"), so '
            'it drops traffic for Branch 1 and the internet. Return traffic is not the problem: R-HQ has routes to both '
            'branches and R-Branch1 sends everything to HQ by default.',
            'One route fixes both: a default route on R-Branch2, prefix 0.0.0.0 with mask 0.0.0.0 (/0), via R-HQ\'s end of '
            'their link, 10.255.0.5. Separate routes for 192.168.20.0/24 would fix Branch 1 only; the internet cannot be '
            'listed network by network.'],
    }

def build():
    return [two_sites(), hub_spoke()]

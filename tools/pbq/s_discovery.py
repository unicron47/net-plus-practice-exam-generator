"""Type 9, network discovery (modelled on ExamTopics N10-008 #754): run show commands in simulated switch terminals
and complete the documentation. Each device starts with one known fact from the old documentation, so there is exactly
one chain of commands that identifies it (#754 had no such anchor, which is why its key was unreliable).
All command output is generated from the same device list."""
from lib import *

def mac_table(rows):
    """rows: (vlan, mac, port)."""
    out = ['          Mac Address Table', '-------------------------------------------', '',
           'Vlan    Mac Address       Type        Ports', '----    -----------       --------    -----']
    out += [f'{v:>4}    {m}    DYNAMIC     {p}' for v, m, p in sorted(rows, key=lambda r: (int(r[0]), r[1]))]
    out.append(f'Total Mac Addresses for this criterion: {len(rows)}')
    return '\n'.join(out)

def arp_table(rows):
    """rows: (ip, mac, interface, age); age '-' for the switch's own address."""
    out = ['Protocol  Address          Age (min)  Hardware Addr   Type   Interface']
    key = lambda r: tuple(int(x) for x in r[0].split('.'))
    out += [f'Internet  {ip:<15}  {age:>9}   {mac}  ARPA   {ifc}' for ip, mac, ifc, age in sorted(rows, key=key)]
    return '\n'.join(out)

def cdp_table(rows):
    """rows: (device, local, holdtime, capability, platform, remote)."""
    out = ['Capability Codes: R - Router, T - Trans Bridge, B - Source Route Bridge',
           '                  S - Switch, H - Host, I - IGMP, r - Repeater, P - Phone,',
           '                  D - Remote, C - CVTA, M - Two-port Mac Relay', '',
           'Device ID        Local Intrfce     Holdtme    Capability  Platform  Port ID']
    out += [f'{d:<17}{l:<18}{h:<11}{c:<12}{p:<10}{r}' for d, l, h, c, p, r in rows]
    out += ['', f'Total cdp entries displayed : {len(rows)}']
    return '\n'.join(out)

def vlan_brief(vlans, ports_by_vlan):
    out = ['VLAN Name                             Status    Ports',
           '---- -------------------------------- --------- -------------------------------']
    for vid, name in vlans:
        out.append(f'{vid:<5}{name:<33}active    {", ".join(ports_by_vlan.get(vid, []))}'.rstrip())
    return '\n'.join(out)

def if_status(rows):
    """rows: (port, name, status, vlan)."""
    out = ['Port      Name               Status       Vlan       Duplex  Speed Type']
    for p, n, st, v in rows:
        up = st == 'connected'
        out.append(f'{p:<10}{n:<19}{st:<13}{v:<11}{"a-full" if up else "auto":<8}{"a-1000" if up else "auto":<6}'
                   ' 10/100/1000BaseTX')
    return '\n'.join(out)

def terminal(id, prompt, commands):
    return {'kind': 'terminal', 'id': id, 'prompt': prompt,
            'banner': f'Type help for the available commands. Commands may be abbreviated (for example, sh mac add).',
            'commands': [{'cmd': c, 'out': o} for c, o in commands]}

# ── A: two access switches under a core (like #754) ───────────────────────
def two_access():
    core_mac = '0200.0000.0001'
    vlans = [('1', 'default'), ('30', 'STAFF'), ('60', 'LAB')]
    pcs = [  # name, switch, port, vlan, mac, ip, known field
        ('PC1', 'sw1', 'Gi0/3', '30', '0200.0000.0005', '10.10.30.52', 'ip'),
        ('PC2', 'sw1', 'Gi0/2', '60', '0200.0000.0003', '10.10.60.53', 'mac'),
        ('PC3', 'sw2', 'Gi0/4', '30', '0200.0000.0008', '10.10.30.54', 'port'),
        ('PC4', 'sw2', 'Gi0/2', '60', '0200.0000.0006', '10.10.60.51', 'vlan')]
    servers = [('10.10.30.10', '0200.0000.0004', 'Gi1/0/5', '30'), ('10.10.60.10', '0200.0000.0007', 'Gi1/0/6', '60')]
    uplink = {'sw1': ('Gi0/1', 'Gi1/0/1'), 'sw2': ('Gi0/1', 'Gi1/0/2')}
    names = {'sw1': 'Access-SW1', 'sw2': 'Access-SW2'}
    # the known fact must pick out exactly one PC on its switch, and every MAC/IP must be unique
    for n, sw, port, vlan, mac, ip, known in pcs:
        same = [p for p in pcs if p[1] == sw and p[{'ip': 5, 'mac': 4, 'port': 2, 'vlan': 3}[known]] ==
                {'ip': ip, 'mac': mac, 'port': port, 'vlan': vlan}[known]]
        assert len(same) == 1, n
    assert len({p[4] for p in pcs}) == 4 and len({p[5] for p in pcs}) == 4
    panels = {}
    for sw in ('sw1', 'sw2'):
        mine = [p for p in pcs if p[1] == sw]
        others = [p for p in pcs if p[1] != sw]
        up, core_port = uplink[sw]
        macs = [(p[3], p[4], p[2]) for p in mine] + [(v, core_mac, up) for v in ('30', '60')] + \
               [(others[0][3], others[0][4], up)]                     # one remote PC learned over the uplink
        used = {p[2] for p in mine}
        free = [x for x in ('Gi0/2', 'Gi0/3', 'Gi0/4') if x not in used]
        by_vlan = {'1': free}
        for p in mine: by_vlan.setdefault(p[3], []).append(p[2])
        cmds = [('show mac address-table', mac_table(macs)),
                ('show cdp neighbors', cdp_table([('Core-SW1', f'Gig {up[2:]}', '151', 'R S I', 'C9300', f'Gig {core_port[2:]}')])),
                ('show vlan brief', vlan_brief(vlans, by_vlan)),
                ('show interfaces status', if_status([(up, 'uplink-core', 'connected', 'trunk')] +
                                                     [(x, '', 'connected' if x in used else 'notconnect',
                                                       next((p[3] for p in mine if p[2] == x), '1')) for x in ('Gi0/2', 'Gi0/3', 'Gi0/4')]))]
        panels[sw] = panel(names[sw], [terminal(f'{sw}_t', f'{names[sw]}#', cmds)])
    arp = [(f'10.10.{v}.1', core_mac, f'Vlan{v}', '-') for v in ('30', '60')] + \
          [(p[5], p[4], f'Vlan{p[3]}', str(4 + i * 3)) for i, p in enumerate(pcs)] + [(ip, m, f'Vlan{v}', '9') for ip, m, _, v in servers]
    core_macs = [(p[3], p[4], uplink[p[1]][1]) for p in pcs] + [(v, m, port) for _, m, port, v in servers]
    panels['core'] = panel('Core-SW1', [terminal('core_t', 'Core-SW1#', [
        ('show arp', arp_table(arp)), ('show ip arp', arp_table(arp)), ('show mac address-table', mac_table(core_macs)),
        ('show cdp neighbors', cdp_table([('Access-SW1', 'Gig 1/0/1', '163', 'S I', 'C2960', 'Gig 0/1'),
                                          ('Access-SW2', 'Gig 1/0/2', '149', 'S I', 'C2960', 'Gig 0/1')])),
        ('show ip interface brief', 'Interface              IP-Address      OK? Method Status                Protocol\n'
                                    'Vlan30                 10.10.30.1      YES NVRAM  up                    up\n'
                                    'Vlan60                 10.10.60.1      YES NVRAM  up                    up')])])
    mac_opts = sorted({p[4] for p in pcs} | {s[1] for s in servers} | {'0200.0000.0002', '0200.0000.0009'})
    ip_opts = [f'10.10.{v}.{h}' for v in ('30', '60') for h in (51, 52, 53, 54)]
    rows = []
    for n, sw, port, vlan, mac, ip, known in pcs:
        cells = {'mac': mac, 'ip': ip, 'vlan': vlan, 'port': port}
        opts = {'mac': mac_opts, 'ip': ip_opts, 'vlan': ['30', '60'], 'port': ['Gi0/1', 'Gi0/2', 'Gi0/3', 'Gi0/4']}
        label = {'mac': 'MAC address', 'ip': 'IP address', 'vlan': 'VLAN', 'port': 'Interface'}
        row = [n, names[sw]]
        for k in ('mac', 'ip', 'vlan', 'port'):
            row.append(cells[k] if k == known else
                       {'id': f'a_{n.lower()}_{k}', 'label': f'{n} {label[k]}', 'type': 'select', 'options': opts[k],
                        'answer': cells[k]})
        rows.append(row)
    doc = {'kind': 'grid', 'title': 'Network documentation (values shown are from the old documentation)',
           'columns': ['PC', 'Switch', 'MAC address', 'IP address', 'VLAN', 'Interface'], 'rows': rows}
    return {
        'id': 'pbq-disc-access', 'type': 'discovery', 'title': 'Document the access layer',
        'objectives': ['2.1', '2.2', '5.5'],
        'scenario': ['You have been asked to finish the network documentation. The old documentation gives one fact about '
                     'each PC; use the switch terminals to find the rest. Access-SW1 and Access-SW2 are layer 2 switches; '
                     'Core-SW1 routes between the VLANs.'],
        'requirements': ['Select each switch to open its terminal (type help for the commands)',
                         'Complete every empty cell in the documentation table'],
        'instructions': 'Commands can be abbreviated, as on a real switch. The documentation table is below the diagram.',
        'views': [{'label': 'Network', 'diagram': {
            'w': 760, 'h': 330,
            'zones': [],
            'nodes': [node('core', 'switch', 380, 50, 'Core-SW1', 'terminal', 'core'),
                      node('sw1', 'switch', 200, 170, 'Access-SW1', 'terminal', 'sw1'),
                      node('sw2', 'switch', 560, 170, 'Access-SW2', 'terminal', 'sw2'),
                      node('pc1', 'pc', 120, 280, 'PC1'), node('pc2', 'pc', 280, 280, 'PC2'),
                      node('pc3', 'pc', 480, 280, 'PC3'), node('pc4', 'pc', 640, 280, 'PC4')],
            'links': [link('core', 'sw1'), link('core', 'sw2'), link('sw1', 'pc1'), link('sw1', 'pc2'),
                      link('sw2', 'pc3'), link('sw2', 'pc4')]},
            'blocks': [doc]}],
        'panels': panels,
        'explanation': [
            'The access switches\' MAC address tables give each PC\'s MAC, VLAN and port. Ignore entries on Gi0/1: that is '
            'the uplink to the core (see show cdp neighbors), so those MACs belong to devices elsewhere. The core\'s ARP '
            'table then maps each MAC to its IP address.',
            'PC1: IP 10.10.30.52 → ARP gives 0200.0000.0005 → Access-SW1 Gi0/3, VLAN 30. PC2: MAC 0200.0000.0003 → Gi0/2, '
            'VLAN 60 → ARP 10.10.60.53. PC3: Access-SW2 Gi0/4 → 0200.0000.0008, VLAN 30 → 10.10.30.54. PC4: the only VLAN 60 '
            'host on Access-SW2 → Gi0/2, 0200.0000.0006 → 10.10.60.51.'],
    }

# ── B: one floor switch, CDP + DHCP snooping ──────────────────────────────
def colon(mac):
    h = mac.replace('.', '')
    return ':'.join(h[i:i + 2] for i in range(0, 12, 2)).upper()

def floor_switch():
    # name, known fact shown in the documentation, port, vlan, ip, mac, cdp (device id, platform, caps, remote port), poe W
    devs = [('AP-East', 'hostname AP-East', 'Gi1/0/24', '99', '10.40.99.21', '0200.cc00.0024',
             ('AP-East', 'cisco AIR-AP2802I', 'T B I', 'Gig 0'), '22.3'),
            ('Phone-101', 'MAC 0200.aa00.0101', 'Gi1/0/3', '50', '10.40.50.31', '0200.aa00.0101',
             ('SEP0200AA000101', 'Cisco IP Phone 8841', 'H P M', 'Port 1'), '6.1'),
            ('Phone-102', 'MAC 0200.aa00.0102', 'Gi1/0/7', '50', '10.40.50.32', '0200.aa00.0102',
             ('SEP0200AA000102', 'Cisco IP Phone 8841', 'H P M', 'Port 1'), '6.1'),
            ('Printer-2F', 'MAC 0200.00bb.0042', 'Gi1/0/15', '10', '10.40.10.88', '0200.00bb.0042', None, None)]
    pc = ('Gi1/0/3', '10', '10.40.10.57', '0200.dd00.0057')          # desk PC behind Phone-101
    dhcp = [(colon(m), ip, v, port) for _, _, port, v, ip, m, cdp, _ in devs if cdp is None or 'Phone' in cdp[1]] + \
           [(colon(pc[3]), pc[2], pc[1], pc[0])]
    long = lambda port: 'GigabitEthernet' + port[2:]
    cdp_rows = [(c[0], f'Gig {port[2:]}', '142', c[2], 'IP Phone' if 'Phone' in c[1] else c[1].split()[-1][:9], c[3]) for _, _, port, _, _, _, c, _ in devs if c]
    detail = []
    for _, _, port, _, ip, _, c, _ in devs:
        if not c: continue
        detail += ['-------------------------', f'Device ID: {c[0]}', 'Entry address(es):', f'  IP address: {ip}',
                   f'Platform: {c[1]},  Capabilities: {c[2]}',
                   f'Interface: {long(port)},  Port ID (outgoing port): {c[3]}', '']
    snoop = ['MacAddress          IpAddress        Lease(sec)  Type           VLAN  Interface',
             '------------------  ---------------  ----------  -------------  ----  --------------------']
    snoop += [f'{m:<20}{ip:<17}{"84211":<12}{"dhcp-snooping":<15}{v:<6}{long(port)}' for m, ip, v, port in
              sorted(dhcp, key=lambda r: r[1])]
    snoop.append(f'Total number of bindings: {len(dhcp)}')
    poe = ['Interface    Admin  Oper       Power   Device              Class  Max', '                              (Watts)']
    for n, _, port, _, _, _, c, w in sorted(devs, key=lambda d: int(d[2].split('/')[-1])):
        if c: poe.append(f'{port:<13}{"auto":<7}{"on":<11}{w:<8}{c[1][-19:]:<20}{"4" if float(w) > 15 else "2":<7}30.0')
    trunk = ('Port        Mode         Encapsulation  Status        Native vlan\n'
             'Gi1/0/24    on           802.1q         trunking      99\n'
             'Gi1/0/48    on           802.1q         trunking      1\n\n'
             'Port        Vlans allowed on trunk\n'
             'Gi1/0/24    10,99\n'
             'Gi1/0/48    1-4094')
    vlans = vlan_brief([('1', 'default'), ('10', 'DATA'), ('50', 'VOICE'), ('99', 'MGMT')],
                       {'1': ['Gi1/0/1', 'Gi1/0/2'], '10': ['Gi1/0/3', 'Gi1/0/7', 'Gi1/0/15'], '50': ['Gi1/0/3', 'Gi1/0/7']})
    macs = mac_table([(v, m, port) for _, _, port, v, _, m, _, _ in devs] + [(pc[1], pc[3], pc[0])])
    term = terminal('fl_t', 'Floor2-SW#', [('show cdp neighbors', cdp_table(cdp_rows)),
                                           ('show cdp neighbors detail', '\n'.join(detail).rstrip()),
                                           ('show ip dhcp snooping binding', '\n'.join(snoop)),
                                           ('show power inline', '\n'.join(poe)),
                                           ('show interfaces trunk', trunk), ('show vlan brief', vlans),
                                           ('show mac address-table', macs)])
    ports = sorted({d[2] for d in devs} | {'Gi1/0/1', 'Gi1/0/2', 'Gi1/0/48'}, key=lambda x: int(x.split('/')[-1]))
    ips = sorted({d[4] for d in devs} | {pc[2], '10.40.99.1', '10.40.50.1'}, key=lambda x: tuple(map(int, x.split('.'))))
    rows = []
    for n, known, port, v, ip, _, _, _ in devs:
        f = lambda k, opts, ans, lab: {'id': f'b_{n.lower().replace("-", "")}_{k}', 'label': f'{n} {lab}', 'type': 'select',
                                       'options': opts, 'answer': ans}
        rows.append([n, known, f('port', ports, port, 'interface'), f('ip', ips, ip, 'IP address'),
                     f('vlan', ['1', '10', '50', '99'], v, 'VLAN')])
    doc = {'kind': 'grid', 'title': 'Floor 2 documentation', 'rows': rows,
           'columns': ['Device', 'Known from old documentation', 'Interface', 'IP address',
                       'VLAN']}
    # every answer must appear in the output the student can see
    seen = '\n'.join(c['out'] for c in term['commands'])
    for n, _, port, v, ip, m, _, _ in devs:
        assert ip in seen and (port in seen or long(port) in seen), n
    return {
        'id': 'pbq-disc-floor', 'type': 'discovery', 'title': 'Document the floor 2 switch',
        'objectives': ['2.1', '2.2', '1.5'],
        'scenario': ['A new floor switch was installed with an access point, two IP phones and a printer. The installer left '
                     'only partial notes. Use the switch terminal to complete the documentation.'],
        'requirements': ['Select the switch to open its terminal (type help for the commands)',
                         'For each device, find its switch interface, IP address and VLAN (for the access point, the native '
                         'VLAN of its trunk; for the phones, the voice VLAN)'],
        'instructions': 'Commands can be abbreviated, as on a real switch. The documentation table is below the diagram.',
        'views': [{'label': 'Floor 2', 'diagram': {
            'w': 760, 'h': 260, 'zones': [],
            'nodes': [node('sw', 'switch', 380, 60, 'Floor2-SW', 'terminal', 'sw'),
                      node('ap', 'ap', 130, 190, 'AP-East'), node('ph1', 'phone', 300, 190, 'Phone-101'),
                      node('ph2', 'phone', 460, 190, 'Phone-102'), node('prn', 'printer', 630, 190, 'Printer-2F')],
            'links': [link('sw', 'ap'), link('sw', 'ph1'), link('sw', 'ph2'), link('sw', 'prn')]},
            'blocks': [doc]}],
        'panels': {'sw': panel('Floor2-SW', [term])},
        'explanation': [
            'show cdp neighbors detail gives the access point\'s and phones\' interfaces and IP addresses. A Cisco phone\'s '
            'CDP device ID is SEP followed by its MAC, so SEP0200AA000101 is Phone-101 (Gi1/0/3, 10.40.50.31) and '
            'SEP0200AA000102 is Phone-102 (Gi1/0/7, 10.40.50.32). The phones\' DHCP bindings are in VLAN 50, the voice VLAN.',
            'AP-East is on Gi1/0/24 (10.40.99.21); show interfaces trunk shows that port\'s native VLAN is 99. The printer '
            'does not run CDP, but the DHCP snooping table lists its MAC (shown as 02:00:00:BB:00:42) with 10.40.10.88 in '
            'VLAN 10 on Gi1/0/15. The 10.40.10.57 binding on Gi1/0/3 is the PC behind Phone-101, not the phone.'],
    }

def build():
    return [two_access(), floor_switch()]

"""Pure repair function; validates byte preservation before returning output."""
import struct
import hashlib
from .container import unpack, pack
from .records import records, Reader
from .properties import props, value

def fs(s):
    b = s.encode() + b'\x00'
    return struct.pack('<i', len(b)) + b

def pd(d, b):
    ps, end = props(d, b['data']['start'] + 1, b['data']['end'])
    if not (d[b['data']['start']] == 0 and d[end:b['data']['end']] == bytes(8)):
        raise ValueError("Unsupported save or validation failure: d[b['data']['start']] == 0 and d[end:b['data']['end']] == bytes(8)")
    result = {p['name']: p for p in ps}
    if len(result) != len(ps):
        raise ValueError('Duplicate property names')
    return result

def cells(d, p):
    r = Reader(d, p['value_start'])
    n = r.num()
    if n <= 0 or p['size'] != 4 + 4 * n:
        raise ValueError('Invalid occupied-cell array')
    return [r.num() for _ in range(n)]

def locate(d):
    aa = records(d)
    palaces = []
    altars = []
    for a in aa:
        if 'Monument' not in a['cls'] and 'Altar' not in a['cls']:
            continue
        ps = pd(d, a)
        tag = ps.get('BuildingTag')
        if not tag:
            continue
        nested, _ = props(d, tag['value_start'], tag['end'])
        tagval = value(d, nested[0])
        if tagval == 'Building.Monument.WaterPalace':
            palaces.append((a, ps))
        if tagval == 'Building.Religion.Altar':
            altars.append((a, ps))
    if not len(palaces) == 1:
        raise ValueError('Expected exactly one Water Palace')
    palace, pp = palaces[0]
    occupied = cells(d, pp['OccupiedCellsID'])
    matched = [(a, p) for a, p in altars if 'AddresOfConstructedMonument' in p and value(d, p['AddresOfConstructedMonument']) == occupied[0]]
    if not len(matched) == 1:
        raise ValueError('Expected one altar linked to first palace cell')
    altar, ap = matched[0]
    inv = [c for c in altar['components'] if c['name'] == 'Inventory']
    if not len(inv) == 1:
        raise ValueError('Unsupported save or validation failure: len(inv) == 1')
    return (aa, palace, altar, ap, inv[0], pd(d, inv[0]))

def repair(original):
    d, blocks = unpack(original)
    if not unpack(pack(d))[0] == d:
        raise ValueError('Compression round trip failed')
    aa, palace, altar, ap, inv, ip = locate(d)
    managers = [a for a in aa if 'ResourcesMenager' in a['name']]
    inventories = [c for a in managers for c in a['components'] if c['name'] == 'Inventory Component']
    if not any(('AdvancedTool' in {k for k, v, o in value(d, pd(d, c)['OwnedResources'])['entries']} for c in inventories)):
        raise ValueError('Resource key must exist in the resource manager inventory')
    if not value(d, ap['MonumentConstructionStage']) == 'EMonumentConstructionStage::CollectingResoures':
        raise ValueError("Unsupported save or validation failure: value(d, ap['MonumentConstructionStage']) == 'EMonumentConstructionStage::CollectingResoures'")
    if not value(d, ap['MonumentStage']) == 0:
        raise ValueError("Unsupported save or validation failure: value(d, ap['MonumentStage']) == 0")
    edits = []
    details = []
    for b, p, newval, fmt in [(altar, ap['GatheringResource'], 1, 'B'), (inv, ip['OwnedResources'], 0.0, 'f')]:
        expected = 'BoolProperty' if fmt == 'B' else 'FloatProperty'
        if p['type'] != ['MapProperty', [['NameProperty', []], [expected, []]]]:
            raise ValueError('Unsupported target map type')
        m = value(d, p)
        if not m['removed'] == 0:
            raise ValueError("Unsupported save or validation failure: m['removed'] == 0")
        old = {k: v for k, v, off in m['entries']}
        if 'AdvancedTool' in old:
            raise ValueError('AdvancedTool already exists; this repair only handles entries missing from BOTH maps')
        if 'AdvancedTools' in old:
            raise ValueError('Obsolete plural-key patch detected; use an untouched original')
        if not len(old) == len(m['entries']):
            raise ValueError('Duplicate resource keys')
        addition = fs('AdvancedTool') + struct.pack('<' + fmt, newval)
        edits.extend([(p['end'], b'', addition), (p['size_offset'], d[p['size_offset']:p['size_offset'] + 4], struct.pack('<i', p['size'] + len(addition))), (p['value_start'] + 4, d[p['value_start'] + 4:p['value_start'] + 8], struct.pack('<i', len(old) + 1)), (b['data']['size_offset'], d[b['data']['size_offset']:b['data']['size_offset'] + 4], struct.pack('<i', b['data']['size'] + len(addition)))])
        details.append({'property': p['name'], 'added': {'AdvancedTool': newval}, 'original_entries': old, 'insert_at_original_offset': p['end'], 'added_bytes': len(addition)})
    delta = sum((len(new) - len(old) for off, old, new in edits))
    edits.append((0, d[:4], struct.pack('<i', len(d) - 4 + delta)))
    patched = d
    for off, old, new in sorted(edits, reverse=True):
        if not patched[off:off + len(old)] == old:
            raise ValueError('Unsupported save or validation failure: patched[off:off + len(old)] == old')
        patched = patched[:off] + new + patched[off + len(old):]
    op = np = 0
    for off, old, new in sorted(edits):
        if not d[op:off] == patched[np:np + off - op]:
            raise ValueError('Unsupported save or validation failure: d[op:off] == patched[np:np + off - op]')
        np += off - op
        if not patched[np:np + len(new)] == new:
            raise ValueError('Unsupported save or validation failure: patched[np:np + len(new)] == new')
        np += len(new)
        op = off + len(old)
    if not d[op:] == patched[np:]:
        raise ValueError('Unsupported save or validation failure: d[op:] == patched[np:]')
    newaa, newpalace, newaltar, newap, newinv, newip = locate(patched)
    if not len(newaa) == len(aa):
        raise ValueError('Unsupported save or validation failure: len(newaa) == len(aa)')
    for a, b in zip(aa, newaa):
        if not (a['name'] == b['name'] and a['cls'] == b['cls']):
            raise ValueError("Unsupported save or validation failure: a['name'] == b['name'] and a['cls'] == b['cls']")
        if a['index'] != altar['index']:
            if not d[a['start']:a['end']] == patched[b['start']:b['end']]:
                raise ValueError("Unsupported save or validation failure: d[a['start']:a['end']] == patched[b['start']:b['end']]")
    for oldp, newp in [(ap, newap), (ip, newip)]:
        for name, p in oldp.items():
            q = newp[name]
            if name in ('GatheringResource', 'OwnedResources'):
                oldvals = {k: v for k, v, off in value(d, p)['entries']}
                newvals = {k: v for k, v, off in value(patched, q)['entries']}
                if not (all((newvals[k] == v for k, v in oldvals.items())) and set(newvals) - set(oldvals) == {'AdvancedTool'}):
                    raise ValueError("Unsupported save or validation failure: all((newvals[k] == v for k, v in oldvals.items())) and set(newvals) - set(oldvals) == {'AdvancedTool'}")
            elif not d[p['start']:p['end']] == patched[q['start']:q['end']]:
                raise ValueError("Unsupported save or validation failure: d[p['start']:p['end']] == patched[q['start']:q['end']]")
    for c, e in zip(altar['components'], newaltar['components']):
        if c['name'] != 'Inventory':
            if not d[c['start']:c['data']['end']] == patched[e['start']:e['data']['end']]:
                raise ValueError("Unsupported save or validation failure: d[c['start']:c['data']['end']] == patched[e['start']:e['data']['end']]")
    if not d[aa[-1]['end']:] == patched[newaa[-1]['end']:]:
        raise ValueError("Unsupported save or validation failure: d[aa[-1]['end']:] == patched[newaa[-1]['end']:]")
    out = pack(patched)
    if not unpack(out)[0] == patched:
        raise ValueError('Unsupported save or validation failure: unpack(out)[0] == patched')
    report = {'status': 'Experimental delivery repair; structurally validated, not tested in game', 'source_sha256': hashlib.sha256(original).hexdigest(), 'output_sha256': hashlib.sha256(out).hexdigest(), 'original_raw_bytes': len(d), 'patched_raw_bytes': len(patched), 'actor_count': len(aa), 'palace': palace, 'altar': altar, 'modifications': details, 'edits': [{'offset': o, 'old_hex': old.hex(), 'new_hex': new.hex()} for o, old, new in sorted(edits)], 'validation': 'All other actor records, altar properties, component records, existing map entries and trailing level data preserved byte-for-byte.'}
    return (out, report)

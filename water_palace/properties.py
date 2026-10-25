"""Limited property reader for the target records, not a general UE parser."""
from .records import Reader

def typename(r, depth=0):
    if depth > 16:
        raise ValueError('Property type nesting limit exceeded')
    name = r.string()
    n = r.num()
    if not 0 <= n < 10:
        raise ValueError('Unsupported save or validation failure: 0 <= n < 10')
    return [name, [typename(r, depth + 1) for _ in range(n)]]

def props(d, start, end):
    r = Reader(d, start)
    out = []
    while r.p < end:
        p = r.p
        name = r.string()
        if name == 'None':
            return (out, r.p)
        typ = typename(r)
        so = r.p
        n = r.num()
        flags = r.num('B')
        if not flags in (0, 16):
            raise ValueError((name, flags))
        v = r.p
        if not 0 <= n <= end - v:
            raise ValueError((name, n))
        r.p += n
        out.append(dict(name=name, type=typ, start=p, size_offset=so, size=n, flags=flags, value_start=v, end=r.p))
    return (out, r.p)

def value(d, p):
    r = Reader(d, p['value_start'])
    t = p['type'][0]
    if t == 'IntProperty':
        return r.num()
    if t == 'FloatProperty':
        return r.num('f')
    if t == 'BoolProperty':
        return bool(p['flags'] & 16)
    if t == 'ByteProperty':
        return r.num('B')
    if t in ('NameProperty', 'EnumProperty', 'ObjectProperty'):
        return r.string()
    if t == 'MapProperty':
        removed = r.num()
        n = r.num()
        vals = []
        if not (removed == 0 and 0 <= n <= 100000):
            raise ValueError('Unsupported map removal list or entry count')
        if p['type'][1][0][0] == 'NameProperty':
            if not p['type'][1][1][0] in ('BoolProperty', 'FloatProperty'):
                raise ValueError('Unsupported map value type')
            for _ in range(n):
                key = r.string()
                off = r.p
                v = r.num('B' if p['type'][1][1][0] == 'BoolProperty' else 'f')
                vals.append([key, v, off])
            if not r.p == p['end']:
                raise ValueError("Unsupported save or validation failure: r.p == p['end']")
            return dict(removed=removed, entries=vals)
    return d[p['value_start']:p['end']].hex() if p['size'] < 100 else f"{p['size']} bytes"

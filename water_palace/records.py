"""Observed actor and component framing; opaque bytes are preserved."""
import struct

class Reader:

    def __init__(self, d, p=0):
        self.d = d
        self.p = p

    def num(self, fmt='i'):
        if not 0 <= self.p <= len(self.d) - struct.calcsize(fmt):
            raise ValueError('Truncated numeric field')
        v = struct.unpack_from('<' + fmt, self.d, self.p)[0]
        self.p += struct.calcsize(fmt)
        return v

    def string(self, obfuscated=False):
        n = self.num()
        if not 0 <= n < 10000:
            raise ValueError((self.p, n))
        if not self.p + n <= len(self.d):
            raise ValueError('Truncated string')
        s = self.d[self.p:self.p + n]
        self.p += n
        if obfuscated:
            s = bytes(((c + 1) % 256 if c else 0 for c in s))
        return s.rstrip(b'\x00').decode('utf-8')

    def blob(self):
        off = self.p
        n = self.num()
        if not 0 <= n <= len(self.d) - self.p:
            raise ValueError((off, n))
        p = self.p
        self.p += n
        return dict(size_offset=off, start=p, end=self.p, size=n)

def records(d):
    r = Reader(d)
    if not r.num() == len(d) - 4:
        raise ValueError('Unsupported save or validation failure: r.num() == len(d) - 4')
    n = r.num()
    if not 0 < n <= 100000:
        raise ValueError('Unsupported save or validation failure: 0 < n <= 100000')
    out = []
    for i in range(n):
        a = dict(index=i, start=r.p, cls=r.string(True), name=r.string(True))
        r.p += 80
        a['flag'] = r.num('B')
        a['data'] = r.blob()
        count = r.num()
        if not 0 <= count < 100:
            raise ValueError((i, r.p, count))
        a['components'] = []
        for j in range(count):
            c = dict(start=r.p, name=r.string(True))
            r.p += 80
            c['data'] = r.blob()
            a['components'].append(c)
        a['end'] = r.p
        out.append(a)
    return out

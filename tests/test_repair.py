"""Synthetic saves only: no private city or game assets required."""
import contextlib
import io
import struct
import tempfile
import unittest
from pathlib import Path

from water_palace.container import pack, unpack
from water_palace.repair import fs, locate, repair
from water_palace.properties import value
from water_palace.__main__ import run


def integer(n):
    return struct.pack('<i', n)


def type_tree(name, *children):
    return fs(name) + integer(len(children)) + b''.join(children)


def prop(name, tree, payload):
    return fs(name) + tree + integer(len(payload)) + b'\0' + payload


def simple(name, kind, payload):
    return prop(name, type_tree(kind), payload)


def resource_map(name, kind, entries):
    tree = type_tree('MapProperty', type_tree('NameProperty'), type_tree(kind))
    fmt = '<B' if kind == 'BoolProperty' else '<f'
    payload = integer(0) + integer(len(entries))
    payload += b''.join(fs(key) + struct.pack(fmt, val) for key, val in entries)
    return prop(name, tree, payload)


def tag(name):
    return prop('BuildingTag', type_tree('StructProperty', type_tree('GameplayTag')),
                simple('TagName', 'NameProperty', fs(name)) + fs('None'))


def encoded(name):
    raw = name.encode() + b'\0'
    return integer(len(raw)) + bytes(c - 1 if c else 0 for c in raw)


def blob(properties):
    raw = b'\0' + properties + fs('None') + bytes(8)
    return integer(len(raw)) + raw


def component(name, properties):
    return encoded(name) + bytes(80) + blob(properties)


def actor(name, cls, properties, components=()):
    return (encoded(cls) + encoded(name) + bytes(80) + b'\0' + blob(properties)
            + integer(len(components)) + b''.join(components))


def fixture(existing=False, plural=False, stage=0, resource_amount=9.0):
    palace = actor('Palace', 'MonumentClass', tag('Building.Monument.WaterPalace')
                   + prop('OccupiedCellsID', type_tree('ArrayProperty', type_tree('IntProperty')),
                          integer(2) + integer(123) + integer(124)))
    gathering = [('Scroll', 0), ('Duck', 1)]
    owned = [('Scroll', resource_amount), ('Duck', 11.0)]
    if existing:
        gathering.append(('AdvancedTool', 1))
        owned.append(('AdvancedTool', 7.0))
    if plural:
        gathering.append(('AdvancedTools', 1))
    altar = actor('Altar', 'AltarClass', tag('Building.Religion.Altar')
                  + simple('AddresOfConstructedMonument', 'IntProperty', integer(123))
                  + simple('MonumentStage', 'IntProperty', integer(stage))
                  + simple('MonumentConstructionStage', 'EnumProperty', fs('EMonumentConstructionStage::CollectingResoures'))
                  + resource_map('GatheringResource', 'BoolProperty', gathering),
                  [component('Inventory', resource_map('OwnedResources', 'FloatProperty', owned)),
                   component('Untouched', simple('Health', 'FloatProperty', struct.pack('<f', 77)))])
    manager = actor('ResourcesMenager', 'Manager', b'', [component('Inventory Component',
                    resource_map('OwnedResources', 'FloatProperty', [('AdvancedTool', 498.0)]))])
    raw = integer(3) + palace + altar + manager + b'opaque level tail'
    return pack(integer(len(raw)) + raw)


class RepairTests(unittest.TestCase):
    def test_repair_preserves_values_and_rejects_second_run(self):
        original = fixture(resource_amount=3.5)
        output, report = repair(original)
        raw, _ = unpack(output)
        _, _, _, ap, _, ip = locate(raw)
        flags = {k: v for k, v, _ in value(raw, ap['GatheringResource'])['entries']}
        amounts = {k: v for k, v, _ in value(raw, ip['OwnedResources'])['entries']}
        self.assertEqual(flags, {'Scroll': 0, 'Duck': 1, 'AdvancedTool': 1})
        self.assertEqual(amounts, {'Scroll': 3.5, 'Duck': 11.0, 'AdvancedTool': 0.0})
        self.assertEqual(report['patched_raw_bytes'] - report['original_raw_bytes'], 39)
        with self.assertRaises(ValueError):
            repair(output)

    def test_refuses_existing_plural_and_other_stage(self):
        for options in ({'existing': True}, {'plural': True}, {'stage': 1}):
            with self.subTest(options=options), self.assertRaises(ValueError):
                repair(fixture(**options))

    def test_container_corruption(self):
        source = fixture()
        for damaged in (b'', source[:-1], source + b'junk', bytes(49), source[:-4] + b'xxxx'):
            with self.subTest(size=len(damaged)), self.assertRaises(Exception):
                unpack(damaged)

    def test_multiple_chunks(self):
        raw = bytes(range(256)) * 1200
        decoded, blocks = unpack(pack(raw))
        self.assertEqual(raw, decoded)
        self.assertEqual(len(blocks), 3)

    def test_cli_dry_run_backup_and_collision(self):
        with tempfile.TemporaryDirectory() as folder, contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            root = Path(folder)
            source, dest = root / 'input.sav', root / 'fixed.sav'
            original = fixture()
            source.write_bytes(original)
            self.assertEqual(run([str(source)]), 0)
            self.assertEqual(list(root.iterdir()), [source])
            self.assertEqual(run([str(source), '--output', str(dest)]), 0)
            self.assertEqual(source.read_bytes(), original)
            self.assertEqual(root.joinpath('fixed.sav.original.bak').read_bytes(), original)
            output = dest.read_bytes()
            self.assertEqual(run([str(source), '--output', str(dest)]), 1)
            self.assertEqual(dest.read_bytes(), output)
            self.assertEqual(run([str(source), '--output', str(source)]), 1)
            self.assertEqual(source.read_bytes(), original)


if __name__ == '__main__':
    unittest.main()

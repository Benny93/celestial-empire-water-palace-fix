"""CLI: inspect by default; explicitly request a separate repaired output."""
import argparse
import hashlib
import json
import sys
import struct
import zlib
from pathlib import Path

from .container import MAX_SIZE
from .repair import repair


def run(argv=None):
    parser = argparse.ArgumentParser(description='Repair missing AdvancedTool entries for one Water Palace. Input is never modified.')
    parser.add_argument('input', type=Path, help='Original Level.sav')
    parser.add_argument('--output', type=Path, help='New repaired .sav; omit to inspect without writing')
    args = parser.parse_args(argv)
    source = args.input.resolve()
    try:
        if source.stat().st_size > MAX_SIZE:
            raise ValueError('Input exceeds the 512 MiB limit')
        original = source.read_bytes()
        output, report = repair(original)
        if args.output is None:
            print('Compatible missing-entry state found. Inspection only; no files written.')
        else:
            destination = args.output.resolve()
            backup = destination.with_name(destination.name + '.original.bak')
            report_path = destination.with_name(destination.name + '.report.json')
            paths = (backup, report_path, destination)
            if source in paths or any(p.exists() for p in paths):
                raise ValueError('Input/output collision or output, backup, or report already exists; choose a new output name')
            if not destination.parent.is_dir():
                raise ValueError('Output directory must already exist')
            # Reserve all three paths exclusively. Never truncate an existing file.
            handles = []
            try:
                for path in paths:
                    handles.append(path.open('xb'))
            except OSError:
                for path, handle in zip(paths, handles):
                    handle.close()
                    path.unlink()  # Only empty files created by this invocation.
                raise
            try:
                handles[0].write(original)
                handles[0].flush()
                handles[1].write((json.dumps(report, indent=2) + '\n').encode('utf-8'))
                handles[2].write(output)
            finally:
                for handle in handles:
                    handle.close()
            if backup.read_bytes() != original or destination.read_bytes() != output:
                raise ValueError('Written-file verification failed; do not install the output')
            print(f'Repaired save: {destination}\nOriginal backup: {backup}\nValidation report: {report_path}')
        print(json.dumps({
            'source_sha256': hashlib.sha256(original).hexdigest(),
            'output_sha256': report['output_sha256'],
            'actor_count': report['actor_count'],
            'changes': [dict(property=m['property'], added=m['added']) for m in report['modifications']],
            'validation': report['validation'],
            'in_game_status': 'This output has not been tested in game.'
        }, indent=2))
        return 0
    except (OSError, ValueError, KeyError, IndexError, TypeError, RuntimeError, struct.error, zlib.error) as error:
        print(f'Repair refused or failed: {error}\nInput was not modified. Do not install an output from a failed run.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(run())

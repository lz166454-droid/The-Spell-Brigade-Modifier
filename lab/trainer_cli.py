import argparse
import sys
from lab.trainer.diag import log, log_error
from lab.trainer.session import TrainerSession

def cmd_attach(_args: argparse.Namespace) -> int:
    session = TrainerSession()
    try:
        session.attach()
    except Exception as exc:
        log_error(str(exc))
        return 1
    session.detach()
    return 0

def cmd_stats(_args: argparse.Namespace) -> int:
    session = TrainerSession()
    try:
        session.attach()
        snapshot = session.read_snapshot()
        print('[character stats]')
        for key, value in snapshot.stats.items():
            print(f'{key}: {value}')
        for spell in snapshot.spells:
            print(f'[{spell.name} #{spell.id}]')
            for key, value in spell.stats.items():
                print(f'  {key}: {value}')
    except Exception as exc:
        log_error(str(exc))
        return 1
    finally:
        session.detach()
    return 0

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Spell Brigade Trainer CLI')
    sub = parser.add_subparsers(dest='command', required=True)
    p_attach = sub.add_parser('attach', help='attach and verify player chain')
    p_attach.set_defaults(func=cmd_attach)
    p_stats = sub.add_parser('stats', help='attach and print stats')
    p_stats.set_defaults(func=cmd_stats)
    return parser

def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)

if __name__ == '__main__':
    raise SystemExit(main())

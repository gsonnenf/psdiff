#!/usr/bin/env python3
import argparse
import psdiff
import sys
from psdiff import Psdiff
from pathlib import Path


def main():
    psdiff = Psdiff(Path(__file__).resolve().parent)
    psdiff.snapshot_dir.mkdir(parents=True, exist_ok=True)

    
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    NOVALUE = object()
    group.add_argument("-s", type=int, nargs="?", const=NOVALUE, help="Save snapshot")
    group.add_argument("-p", type=int, nargs='?', const=NOVALUE, help="Print snapshot")
    group.add_argument("-c", type=int, nargs='*', help="Print snapshot diff")
    group.add_argument('--delete', action='store_true', help='Deletes all previous checkpoints')

    try: args = parser.parse_args()
    except SystemExit:
        #parser.print_usage()
        usage()
        sys.exit(1)

    if (args.c is not None) and (len(args.c) > 2 or len(args.c) < 0):
        parser.error("Too many arguments: max 2 allowed per flag.")
    elif (args.s is not None):
        if (args.s is NOVALUE): psdiff.create_snapshot()
        else: psdiff.create_snapshot(args.s)
    elif (args.c is not None):
        arg1 = None if len(args.c) < 1 else args.c[0]
        arg2 = None if len(args.c) < 2 else args.c[1]
        psdiff.print_diff(arg1, arg2)
    elif (args.p is not None):
        if (args.p is NOVALUE): psdiff.print_snapshot()
        else: psdiff.print_snapshot(args.p)
    elif args.delete:
        response = input("Delete all snapshots? [y/N]: ").strip().lower()
        if response == 'y':
            print("Deleting all snapshots...")
            psdiff.delete_snapshots()
        else:
            print("Cancelled.")
    else:
        psdiff.print_diff()
        pass

def usage():
    """Print usage instructions for the psdiff script."""
    print(f"""Usage:
  psdiff          # compare with latest snapshot
  psdiff -s        # saves a new ps snapshot
  psdiff -c N      # compare with snapshot N""")
    

if __name__ == "__main__":
    main()

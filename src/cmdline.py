#!/usr/bin/env python3
import argparse
import psdiff
import sys
from psdiff import Psdiff

def main():
    psdiff = Psdiff()
    psdiff.checkpoint_dir.mkdir(parents=True, exist_ok=True)
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("-s", action="store_true")
    parser.add_argument("-c", type=int)
    args = parser.parse_args()

    if args.s:
        psdiff.create_checkpoint()
    elif args.c is not None:
        psdiff.compare_checkpoint(args.c)
    elif len(sys.argv) == 1:
        psdiff.compare_checkpoint()
    else:
        usage()
        sys.exit(1)

def usage():
    """Print usage instructions for the psdiff script."""
    print(f"""Usage:
  psdiff          # compare with latest checkpoint
  psdiff -s        # saves a new ps snapshot
  psdiff -c N      # compare with checkpoint N""")
    

if __name__ == "__main__":
    main()

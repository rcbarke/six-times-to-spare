#!/usr/bin/env python3
import csv
import os
import re
import sys

DEFAULT_CSV = "ldpc_sionna_spark.csv"
DEFAULT_CHECKPOINT = "ldpc_sionna_spark.checkpoint"

def main():
    csv_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_CSV
    ckpt_path = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_CHECKPOINT

    if not os.path.exists(csv_path):
        print(f"ERROR: CSV file '{csv_path}' not found.", file=sys.stderr)
        sys.exit(1)

    pattern = re.compile(r"^rep(\d+)_N(\d+)_I(\d+)$")

    last_rep = last_n = last_i = None

    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        if "label" not in reader.fieldnames:
            print("ERROR: CSV does not contain a 'label' column.", file=sys.stderr)
            sys.exit(1)

        for row in reader:
            label = row.get("label", "")
            m = pattern.match(label)
            if m:
                rep_str, n_str, i_str = m.groups()
                last_rep = int(rep_str)
                last_n = int(n_str)
                last_i = int(i_str)

    if last_rep is None:
        print("ERROR: No rows with label of the form 'repX_NY_IZ' were found.", file=sys.stderr)
        sys.exit(1)

    # Write checkpoint in the format expected by sweep_ldpc.sh
    with open(ckpt_path, "w") as f:
        f.write(f"LAST_REP={last_rep}\n")
        f.write(f"LAST_N={last_n}\n")
        f.write(f"LAST_I={last_i}\n")

    print(f"Wrote checkpoint to '{ckpt_path}':")
    print(f"  LAST_REP={last_rep}")
    print(f"  LAST_N={last_n}")
    print(f"  LAST_I={last_i}")

if __name__ == "__main__":
    main()


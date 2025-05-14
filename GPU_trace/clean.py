#!/usr/bin/python3

import re
import csv
import os
import argparse
import cxxfilt

def get_function_name(mangled: str) -> str:
    try:
        demangled = cxxfilt.demangle(mangled)
    except Exception:
        # If demangling fails, return the original mangled name.
        return mangled
    # Find the first occurrence of '<' or '(' (if any) to isolate the function signature.
    lt_index = demangled.find('<')
    paren_index = demangled.find('(')
    indices = [i for i in (lt_index, paren_index) if i != -1]
    end_index = min(indices) if indices else len(demangled)
    # Extract the portion before the first '<' or '('.
    name_with_type = demangled[:end_index].strip()
    # Remove any return type or qualifiers by taking the last token.
    # For example, "void functionName" becomes "functionName".
    name = name_with_type.split()[-1]
    return name

def main():
    parser = argparse.ArgumentParser(description="Clean GPU trace file.")
    parser.add_argument("input_file", help="Path to the input file")
    args = parser.parse_args()

    input_file = args.input_file
    directory = os.path.dirname(input_file)
    basename = os.path.basename(input_file)
    name, _ = os.path.splitext(basename)
    output_file = os.path.join(directory, f"{name}_clean.csv")

    # Regex pattern:
    # Group1: event type (any text before '[')
    # Group2: first time value inside []
    # Group3: second time value inside []
    # Group4: duration (number following "duration")
    # Group5: event name (text in quotes)
    pattern = re.compile(r'^(.*?)\s*\[\s*([^,\]]+)\s*,\s*([^\]]+)\s*\]\s*duration\s*([0-9]+),\s*"([^"]+)"')

    with open(input_file, "r") as fin, open(output_file, "w", newline="") as fout:
        writer = csv.writer(fout)
        writer.writerow(["EventType", "TimeStart", "TimeEnd", "Duration", "EventName"])
        for line in fin:
            line = line.strip()
            if not line:
                continue
            match = pattern.search(line)
            if match:
                event_type = match.group(1).strip()
                time_start = match.group(2).strip()
                time_end = match.group(3).strip()
                duration = match.group(4).strip()
                event_name = match.group(5).strip()
                # Demangle the event name and remove any return type.
                event_name = get_function_name(event_name)
                writer.writerow([event_type, time_start, time_end, duration, event_name])

if __name__ == "__main__":
    main()
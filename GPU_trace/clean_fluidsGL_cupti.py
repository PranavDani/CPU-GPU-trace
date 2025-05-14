import re
import csv

# Change this path if needed
input_file = "/home/pranav/Desktop/CPU-GPU-trace/testing/Result/fluidsGL/fluidsGL_cupti"
output_file = "fluidsGL_cupti_clean.csv"

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
            writer.writerow([event_type, time_start, time_end, duration, event_name])

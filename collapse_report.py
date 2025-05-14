#!/usr/bin/python3

import os
import argparse
import configparser
import csv
from collections import defaultdict
import matplotlib.pyplot as plt
from datetime import datetime
import pandas as pd

def arg_file(arg):
    """Validate that the argument is a valid file."""
    if os.path.isfile(arg):
        return arg
    raise argparse.ArgumentTypeError(f"Not a valid file: '{arg}'.")

def parse_args():
    """Parse command-line arguments.
    
    Now the first input CSV file should contain:
      Column1: elapsed timestamp (seconds)
      Column2: callchain records
      Column3: total power consumption (CPU)
      Column4: percentage resource utilization
      Column5: gpu_power consumption
      
    The second CSV file is designated for GPU-specific data.
    """
    parser = argparse.ArgumentParser(
        description='Collapse CSV power consumption data into a performance collapse report.'
    )
    parser.add_argument('input_csv', type=arg_file,
                        help='Path to input CSV file with raw CPU data.')
    parser.add_argument('gpu_csv', type=arg_file,
                        help='Path to input CSV file with GPU-specific data.')
    parser.add_argument('-e', '--scinot', type=int, default=0,
                        help='Multiply power by 10^scinot for scientific notation.')
    return parser.parse_args()

def read_csv_records(csv_path):
    """
    Read CSV file and transform rows into a list of records.
    Each record is a dictionary with keys:
      'timestamp'      -> elapsed time in seconds (string)
      'metadata'       -> dict containing 'callchain'
      'total_power'    -> CPU power consumption (string)
      'resource_util'  -> percentage resource utilization (string)
      'gpu_power'      -> GPU power consumption (string)
    Assumes the CSV file has a header row.
    """
    records = []
    with open(csv_path, newline='') as csvfile:
        reader = csv.reader(csvfile)
        header = next(reader)  # Skip header row
        for row in reader:
            if len(row) < 5:
                continue  # skip malformed rows
            r = {
                'timestamp': row[0],
                'metadata': {'callchain': row[1]},
                'total_power': row[2],
                'resource_util': row[3],
                'gpu_power': row[4]
            }
            records.append(r)
    return records

def read_gpu_records(csv_path):
    """
    Read GPU-specific CSV file and transform rows into a list of records.
    Each record is a dictionary with keys:
      'timestamp'      -> elapsed time in nanoseconds (string)
      'Eventtype'      -> type of event (string)
      'eventname'      -> name of the event (string)
      'Duration_ns'    -> duration of the event in nanoseconds (string)
    Assumes the CSV file has a header row.
    """
    records = []
    with open(csv_path, newline='') as csvfile:
        reader = csv.reader(csvfile)
        header = next(reader)  # Skip header row
        # First, gather all rows into a list to compute the minimum timestart
        rows_list = [row for row in reader if len(row) >= 5]
        if not rows_list:
            return records
        # Compute the minimum timestart value (in nanoseconds)
        t_min = min(float(row[1]) for row in rows_list)
        for row in rows_list:
            timestart_ns = float(row[1])
            timeend_ns = float(row[2])
            # Convert nanoseconds to seconds relative to t_min
            t_start_sec = (timestart_ns - t_min) / 1e9
            t_end_sec = (timeend_ns - t_min) / 1e9
            # Convert duration from nanoseconds to seconds
            duration_sec = float(row[3]) / 1e9
            r = {
            'Eventtype': row[0],
            'timestart': t_start_sec,
            'timeend': t_end_sec,
            'duration': duration_sec,
            'eventname': row[4]
            }
            records.append(r)
    return records

def handle_gpu_records(records_cpu, records_gpu):
    df_cpu = pd.DataFrame({
        'Timestamp': [record['timestamp'] for record in records_cpu],
        'GPU Power': [record['gpu_power'] for record in records_cpu]
    })
    # print(records_gpu[:10])
    
    df_gpu = pd.DataFrame({
        'timestart': [record['timestart'] for record in records_gpu],
        'event': ["GPU;" + record['Eventtype'] + ";" + record['eventname'] for record in records_gpu],
        'duration': [record['duration'] for record in records_gpu],
    })
    
    # Compute the end time for GPU events
    df_gpu['end'] = df_gpu['timestart'] + df_gpu['duration']
    
    # Compute the next timestamp for each CPU row
    df_cpu['next_timestamp'] = df_cpu['Timestamp'].shift(-1)
    
    def find_events(row):
        ts = float(row['Timestamp'])
        # For the last row, use current timestamp as the interval end
        next_ts = float(row['next_timestamp']) if pd.notna(row['next_timestamp']) else ts
        # Find GPU events overlapping the interval [ts, next_ts]
        matching = df_gpu[(df_gpu['timestart'] < next_ts) & (df_gpu['end'] > ts)]
        return '|'.join(matching['event'].tolist()) if not matching.empty else ''
    
    df_cpu['events'] = df_cpu.apply(find_events, axis=1)
    
    # Continue with further processing using df_cpu and df_gpu as needed
    
    print("GPU records processed.")
    # print(df_cpu.head())  # Display first few rows of df_cpu for verification
    
    return df_cpu

def process_records(records, scinot):
    """
    Process CSV records to extract timestamps, CPU power consumption,
    effective (actual) power consumption (CPU plus GPU), effective CPU power and aggregate callchain data.
    
    For each record:
      - Total power is from column3.
      - Effective CPU power = (resource_util / 100) * total_power.
      - Overall effective power = effective CPU power + gpu_power.
    """
    if not records:
        raise ValueError("No records found in CSV file.")

    first_timestamp = float(records[0]['timestamp'])
    timestamps = []
    total_power_series = []
    effective_power_series = []
    gpu_power_series = []
    effective_cpu_series = []
    callchain_power = defaultdict(float)
    callchain_num = defaultdict(int)

    for record in records:
        current_time = float(record['timestamp'])
        timestamps.append(current_time - first_timestamp)
        
        total_power = float(record['total_power'])
        total_power_series.append(total_power)
        
        resource_util = float(record['resource_util'])
        effective_cpu = (resource_util / 100.0) * total_power
        effective_cpu_series.append(effective_cpu)
        
        gpu_power = float(record['gpu_power'])
        gpu_power_series.append(gpu_power)
        
        overall_effective = effective_cpu + gpu_power
        effective_power_series.append(overall_effective)
        
        # Process callchains: split and ignore the last empty element
        callchain_str = record['metadata']['callchain']
        callchains = callchain_str.split('|')[0:-1]
        if len(callchains) == 0:
            continue
        # Distribute overall effective power equally among callchains
        ppc = overall_effective / len(callchains)
        for callchain in callchains:
            processed_chain = ';'.join(callchain.split(';')[:-1][::-1])
            callchain_power[processed_chain] += ppc
            callchain_num[processed_chain] += 1

    # Apply scientific notation multiplier to callchain power values
    for key in callchain_power:
        callchain_power[key] *= (10 ** scinot)
        
    return timestamps, total_power_series, effective_power_series, gpu_power_series, effective_cpu_series, callchain_power, callchain_num

def process_gpu_records(records):
    """
    Process GPU records to extract timestamps, GPU power consumption, and aggregate GPU callchain data.
    For each record:
      - GPU power is taken from the second column.
      - Callchains are extracted from the fourth column (events) by splitting on '|'.
      - The GPU power is distributed equally among all callchains.
    """
    if records.empty:
        raise ValueError("No records found in GPU CSV file.")

    timestamps = []
    gpu_power_series = []
    gpu_callchain_power = defaultdict(float)
    gpu_callchain_count = defaultdict(int)

    for index, row in records.iterrows():
        # Assume columns: 0: timestamp, 1: GPU Power, 3: events
        timestamp = float(row.iloc[0])
        timestamps.append(timestamp)

        gpu_power = float(row.iloc[1])
        gpu_power_series.append(gpu_power)

        events_str = row.iloc[3]
        callchains = events_str.split('|')
        # Remove the last empty element if present
        if callchains and callchains[-1] == '':
            callchains = callchains[:-1]
        if len(callchains) == 0:
            continue
        # Distribute GPU power equally among all callchains
        ppc = gpu_power / len(callchains)
        for chain in callchains:
            gpu_callchain_power[chain] += ppc
            gpu_callchain_count[chain] += 1

    # print(gpu_callchain_power)
    return gpu_callchain_power, gpu_callchain_count

def write_collapsed_files(target, directory, callchain_power, callchain_num, gpu_callchain_power, gpu_callchain_count):
    """
    Write collapsed energy and CPU data to files.
    Format for each file:
      CPU;target;callchain value
    """
    # Write energy data (includes both CPU and GPU power)
    filename_energy = f'{target}_energy.collapsed'
    file_path_energy = os.path.join(directory, filename_energy)
    with open(file_path_energy, 'w') as file:
        for callchain, power in gpu_callchain_power.items():
            file.write(f'{target};{callchain} {power}\n')
        for callchain, power in callchain_power.items():
            file.write(f'{target};CPU;{callchain} {power}\n')

    # Write CPU (number of calls) data
    filename_cpu = f'{target}_cpu.collapsed'
    file_path_cpu = os.path.join(directory, filename_cpu)
    with open(file_path_cpu, 'w') as file:
        for callchain, count in gpu_callchain_count.items():
            file.write(f'{target};{callchain} {count}\n')
        for callchain, num in callchain_num.items():
            file.write(f'{target};CPU;{callchain} {num}\n')

def plot_power_consumption(timestamps, total_power_series, directory, target):
    """Plot total CPU power consumption over time and save to an SVG file."""
    plt.figure(figsize=(12, 6))
    plt.plot(timestamps, total_power_series)
    plt.xlabel('Timestamp (seconds)')
    plt.ylabel('Total CPU Power Consumption (watts)')
    plt.title('Total CPU Power Consumption over Time')
    filename = f'{target}_power_consumption.svg'
    filepath = os.path.join(directory, filename)
    plt.savefig(filepath)
    plt.close()

def plot_effective_power(timestamps, effective_power_series, directory, target):
    """
    Plot effective power consumption (CPU+GPU) over time and save to an SVG file.
    """
    plt.figure(figsize=(12, 6))
    plt.plot(timestamps, effective_power_series, label='Effective (CPU+GPU) Power', color='orange')
    plt.xlabel('Timestamp (seconds)')
    plt.ylabel('Effective Power Consumption (watts)')
    plt.title('Effective (CPU+GPU) Power Consumption over Time')
    plt.legend()
    filename = f'{target}_effective.svg'
    filepath = os.path.join(directory, filename)
    plt.savefig(filepath)
    plt.close()

def plot_effective_cpu_power(timestamps, effective_cpu_series, directory, target):
    """
    Plot effective CPU power consumption over time and save to an SVG file.
    """
    plt.figure(figsize=(12, 6))
    plt.plot(timestamps, effective_cpu_series, label='Effective CPU Power', color='red')
    plt.xlabel('Timestamp (seconds)')
    plt.ylabel('Effective CPU Power (watts)')
    plt.title('Effective CPU Power Consumption over Time')
    plt.legend()
    filename = f'{target}_rapl.svg'
    filepath = os.path.join(directory, filename)
    plt.savefig(filepath)
    plt.close()

def plot_gpu_power(timestamps, gpu_power_series, directory, target):
    """Plot GPU power consumption over time and save to an SVG file."""
    plt.figure(figsize=(12, 6))
    plt.plot(timestamps, gpu_power_series, label='GPU Power', color='green')
    plt.xlabel('Timestamp (seconds)')
    plt.ylabel('GPU Power Consumption (watts)')
    plt.title('GPU Power Consumption over Time')
    plt.legend()
    filename = f'{target}_gpu_power.svg'
    filepath = os.path.join(directory, filename)
    plt.savefig(filepath)
    plt.close()

def ensure_directory(target):
    """Create directory for saving results if it does not exist."""
    target_clean = target[1:] if target.startswith('/') else target
    directory = os.path.join('./Result', target_clean)
    if not os.path.isdir(directory):
        os.makedirs(directory)
    return target_clean, directory

def main():
    # Parse command-line arguments
    args = parse_args()

    # Read CPU records from the first file
    records_cpu = read_csv_records(args.input_csv)
    
    # Read GPU records from the second file and handle them
    records_gpu = read_gpu_records(args.gpu_csv)
    
    df_merged = handle_gpu_records(records_cpu, records_gpu)
    # Optionally, use df_merged for further processing or saving

    # Process records to extract data and aggregate callchain data using CPU data
    (timestamps, total_power_series, effective_power_series, gpu_power_series,
     effective_cpu_series, callchain_power, callchain_num) = process_records(records_cpu, args.scinot)
    
    # Process GPU records to extract GPU power and callchain data
    gpu_callchain_power, gpu_callchain_count = process_gpu_records(df_merged)

    # Determine target name from the CPU CSV file name (without extension)
    target = os.path.splitext(os.path.basename(args.input_csv))[0]
    
    # Ensure output directory exists
    target_clean, directory = ensure_directory(target)

    # Write collapsed data files
    write_collapsed_files(target_clean, directory, callchain_power, callchain_num, gpu_callchain_power, gpu_callchain_count)

    # Plot total CPU power consumption over time
    plot_power_consumption(timestamps, total_power_series, directory, target_clean)

    # Plot effective CPU power consumption over time
    plot_effective_cpu_power(timestamps, effective_cpu_series, directory, target_clean)

    # Plot effective (CPU+GPU) power consumption over time
    plot_effective_power(timestamps, effective_power_series, directory, target_clean)
    
    # Plot GPU power consumption over time
    plot_gpu_power(timestamps, gpu_power_series, directory, target_clean)

if __name__ == '__main__':
    main()
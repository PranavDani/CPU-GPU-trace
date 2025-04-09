#!/usr/bin/python3

import os
import argparse
import configparser
from pymongo import MongoClient
from collections import defaultdict
import matplotlib.pyplot as plt
from datetime import datetime
import csv

def arg_file(arg):
    """Validate that the argument is a valid file."""
    if os.path.isfile(arg):
        return arg
    raise argparse.ArgumentTypeError(f"Not a valid file: '{arg}'.")

def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description='Collapse power consumption db into performance collapse report.'
    )
    parser.add_argument('target', type=str, help='The target container.')
    parser.add_argument('-e', '--scinot', type=int, default=0, help='Multiply power by 10^scinot for scientific notation.')
    parser.add_argument(
        '-c', '--config', type=arg_file,
        default=os.path.dirname(os.path.realpath(__file__)) + '/collapse_report.ini',
        help='Path to config file'
    )
    return parser.parse_args()

def load_config(config_file):
    """Load configuration from the provided config file."""
    config = configparser.ConfigParser()
    config.read(config_file)
    return config['DEFAULT']

def init_db(conf):
    """Initialize the MongoDB connection and get the collection."""
    client = MongoClient(conf['uri'])
    db = client[conf['db']]
    collection = db[conf['collection']]
    return collection

def process_records(records, scinot):
    """
    Process database records to extract timestamps, power consumption,
    and aggregate callchain data.
    """
    # Convert records cursor to list to allow indexing
    records_list = list(records)
    if not records_list:
        raise ValueError("No records found for the given target.")

    # Get the timestamp of the first record for relative time calculation
    first_timestamp = datetime.fromisoformat(
        str(records_list[0]['timestamp']).replace("Z", "+00:00")
    )

    timestamps = []
    power_consumption = []
    callchain_power = defaultdict(float)
    callchain_num = defaultdict(int)

    for record in records_list:
        # Normalize timestamp and calculate time (in seconds) from first record
        timestamp_str = str(record['timestamp'])
        timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        timestamps.append((timestamp - first_timestamp).total_seconds())
        power_consumption.append(record['power'])
        
        # Process callchains: split and ignore the last empty element
        callchains = record['metadata']['callchain'].split('|')[0:-1]
        if len(callchains) == 0:
            continue
        # Distribute power equally among callchains
        ppc = record['power'] / len(callchains)
        for callchain in callchains:
            # Reverse the callchain order after splitting by ';'
            processed_chain = ';'.join(callchain.split(';')[:-1][::-1])
            callchain_power[processed_chain] += ppc
            callchain_num[processed_chain] += 1

    # Apply scientific notation multiplier
    for key in callchain_power:
        callchain_power[key] *= (10 ** scinot)
        
    return timestamps, power_consumption, callchain_power, callchain_num

def write_collapsed_files(target, directory, callchain_power, callchain_num):
    """
    Write collapsed energy and CPU data to files.
    Format:
      target;callchain value
    """
    # Write energy data
    filename_energy = f'{target}_energy.collapsed'
    file_path_energy = os.path.join(directory, filename_energy)
    with open(file_path_energy, 'w') as file:
        for callchain, power in callchain_power.items():
            file.write(f'{target};{callchain} {power}\n')

    # Write CPU (number of calls) data
    filename_cpu = f'{target}_cpu.collapsed'
    file_path_cpu = os.path.join(directory, filename_cpu)
    with open(file_path_cpu, 'w') as file:
        for callchain, num in callchain_num.items():
            file.write(f'{target};{callchain} {num}\n')

def plot_power_consumption(timestamps, power_consumption, directory, target):
    """Plot power consumption over time and save to an SVG file."""
    plt.figure(figsize=(12, 6))
    plt.plot(timestamps, power_consumption)
    plt.xlabel('Timestamp (seconds)')
    plt.ylabel('Power Consumption (watts)')
    plt.title('Power Consumption over Time')
    filename = f'{target}_power_consumption.svg'
    filepath = os.path.join(directory, filename)
    plt.savefig(filepath)
    plt.close()

def process_and_plot_rapl(target, directory):
    """
    Read the RAPL CSV file, process the data, and create a plot.
    Expects the CSV file to be in the same directory with name '{target}_RAPL.csv'
    """
    filename_csv = f'{target}_RAPL.csv'
    file_path_csv = os.path.join(directory, filename_csv)
    rapl_data = []

    with open(file_path_csv, 'r') as csvfile:
        csvreader = csv.reader(csvfile)
        header = next(csvreader)  # Skip header row
        # Grab first row data for reference
        first_row = next(csvreader)
        first_timestamp_rapl = datetime.fromtimestamp(float(first_row[0].split('\t')[0]))
        # Process first row entry as well
        timestamp, rapl = first_row[0].split('\t')
        timestamp = datetime.fromtimestamp(float(timestamp))
        relative_timestamp = (timestamp - first_timestamp_rapl).total_seconds()
        rapl_data.append([relative_timestamp, float(rapl)])

        for row in csvreader:
            timestamp, rapl = row[0].split('\t')
            timestamp = datetime.fromtimestamp(float(timestamp))
            relative_timestamp = (timestamp - first_timestamp_rapl).total_seconds()
            rapl_data.append([relative_timestamp, float(rapl)])

    # Unpack the RAPL data into timestamps and values
    rapl_timestamps, rapl_values = zip(*rapl_data)

    plt.figure(figsize=(12, 6))
    plt.plot(rapl_timestamps, rapl_values, label='RAPL Data', color='orange')
    plt.xlabel('Timestamp (seconds)')
    plt.ylabel('RAPL (watts)')
    plt.title('RAPL over Time')
    plt.legend()
    filename = f'{target}_rapl_consumption.svg'
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

    # Load configuration from file
    conf = load_config(args.config)

    # Initialize database and get collection
    collection = init_db(conf)

    # Query records based on target container
    records = collection.find({'target': args.target})

    # Process records to extract data
    timestamps, power_consumption, callchain_power, callchain_num = process_records(records, args.scinot)

    # Ensure output directory exists
    target, directory = ensure_directory(args.target)

    # Write collapsed data files
    write_collapsed_files(target, directory, callchain_power, callchain_num)

    # Plot power consumption data over time
    plot_power_consumption(timestamps, power_consumption, directory, target)

    # Plot RAPL data from CSV file (assumes the CSV file exists in the directory)
    process_and_plot_rapl(target, directory)

if __name__ == '__main__':
    main()

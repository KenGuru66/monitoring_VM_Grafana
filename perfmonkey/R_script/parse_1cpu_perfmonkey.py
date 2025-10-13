#!/usr/bin/env python3
"""
parse_1cpu_perfmonkey.py - Controller performance parser for PerfMonkey
Python replacement for parse_1cpu_perfmonkey.R
Memory-efficient, creates separate files for each controller
"""

import sys
import csv
import re
from datetime import datetime
from pathlib import Path
from collections import defaultdict

# PerfMonkey format constants
LABEL = "CPUPERF"
TYPE = "CPU"
OUTPUT_FMT = "%m/%d/%y %H:%M:%S"

def extract_serial(filename):
    """Extract serial number from filename (15+ alphanumeric chars)"""
    match = re.search(r'[0-9A-Z]{15,}', filename)
    return match.group(0) if match else "111111"

def clean_metric_name(metric):
    """Clean metric name for PerfMonkey compatibility"""
    metric = metric.replace(',', '_')
    metric = metric.replace('∞', '8')
    metric = metric.replace('"', '')
    return metric

def parse_datetime(time_str):
    """Parse datetime from ISO format"""
    try:
        if 'T' in time_str:
            dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
            return dt.strftime(OUTPUT_FMT)
    except:
        pass
    
    try:
        dt = datetime.strptime(time_str, "%Y/%m/%d %H:%M")
        return dt.strftime(OUTPUT_FMT)
    except:
        pass
    
    return time_str

def extract_controller_type(instance_name):
    """Extract controller type from instance name"""
    # For now, return default CPU type
    # Could be extended to detect actual type from name
    return TYPE

def process_controller_file(input_file):
    """
    Process controller performance file
    Creates separate output file for each controller instance
    Memory-efficient: processes data in streaming mode
    """
    input_path = Path(input_file)
    
    print("\n═══════════════════════════════════════════════════════════════")
    print("  CONTROLLER PERFORMANCE → PERFMONKEY FORMAT (Python)")
    print("═══════════════════════════════════════════════════════════════\n")
    
    # Extract serial number
    serial = extract_serial(input_path.name)
    print(f"Serial Number: {serial}")
    
    print("\nPass 1: Reading and organizing data...")
    
    # Data structure: data[instance][time][metric] = value
    data = defaultdict(lambda: defaultdict(dict))
    all_metrics = []  # List to preserve order of first appearance
    metrics_seen = set()
    all_times = defaultdict(list)  # times per instance (preserve order)
    times_seen = defaultdict(set)
    all_instances = []  # List to preserve order
    instances_seen = set()
    
    # Read all data
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            instance = row['InstanceName']
            time = row['Time']
            metric = clean_metric_name(row['Metric'])
            value = row['Value']
            
            data[instance][time][metric] = value
            
            # Preserve order of first appearance (like R's unique())
            if metric not in metrics_seen:
                all_metrics.append(metric)
                metrics_seen.add(metric)
            
            if time not in times_seen[instance]:
                all_times[instance].append(time)
                times_seen[instance].add(time)
            
            if instance not in instances_seen:
                all_instances.append(instance)
                instances_seen.add(instance)
    
    # Use preserved order (not sorted)
    metrics = all_metrics
    instances = all_instances
    
    print(f"  ✓ Instances (controllers): {len(instances)}")
    print(f"  ✓ Metrics: {len(metrics)}")
    print(f"  ✓ Controllers: {', '.join(instances)}\n")
    
    # Show timepoints per instance
    for inst in instances:
        print(f"  • Instance {inst}: {len(all_times[inst])} timepoints")
    
    # Find common timepoints across all controllers
    print("\nFinding common timepoints across all controllers...")
    common_times = set(all_times[instances[0]])
    for inst in instances[1:]:
        common_times = common_times.intersection(set(all_times[inst]))
    
    # Sort common timepoints
    common_times = sorted(common_times)
    
    print(f"  ✓ Common timepoints: {len(common_times)}")
    if len(common_times) != len(all_times[instances[0]]):
        print(f"  ⚠ Filtered out {len(all_times[instances[0]]) - len(common_times)} non-common timepoints")
    
    print("\nPass 2: Writing combined file with all controllers...")
    
    # Create single output filename
    output_file = str(input_path).replace('.csv', '').replace('_cpu_all', '') + '_ALL_CONTROLLERS.csv'
    
    # Write single file with all controllers
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        
        # Write header
        header = ['CPUPERF', '#', 'BgnDateTime', 'EndDateTime', 'Serial',
                  'Slot', 'Type'] + metrics
        writer.writerow(header)
        
        # Write data rows: for each time, write all controllers
        total_rows = 0
        for row_num, time in enumerate(common_times, 1):
            formatted_time = parse_datetime(time)
            
            # Write row for each controller at this time
            for inst in instances:
                controller_type = extract_controller_type(inst)
                
                row_data = [
                    LABEL,
                    row_num,  # Same row number for all controllers at this time
                    formatted_time,
                    formatted_time,
                    serial,
                    inst,  # Slot (controller ID)
                    controller_type
                ]
                
                # Add metric values for this controller at this time
                for metric in metrics:
                    value = data[inst][time].get(metric, '')
                    row_data.append(value)
                
                writer.writerow(row_data)
                total_rows += 1
        
        print(f"\n  ✓ Written {total_rows} rows ({len(common_times)} timepoints × {len(instances)} controllers)")
    
    output_files = [output_file]
    
    # Summary
    print("\n═══════════════════════════════════════════════════════════════")
    print("  ✅ COMPLETED SUCCESSFULLY!")
    print("═══════════════════════════════════════════════════════════════\n")
    print(f"Created combined file: {Path(output_file).name}")
    print(f"\nSerial Number: {serial}")
    print(f"Controllers: {', '.join(instances)}")
    print(f"Total rows: {total_rows} ({len(common_times)} timepoints × {len(instances)} controllers)")
    print(f"Columns: {7 + len(metrics)} (7 service + {len(metrics)} metrics)")
    print("\nFormat: All controllers in ONE file")
    print("        Same Row # for same timestamp across all controllers")
    print("        CSV without quotes, sorted by time\n")
    print("File is ready for PerfMonkey import! 🚀\n")
    
    return output_files

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 parse_1cpu_perfmonkey.py <input_file>")
        print("\nExample:")
        print("  python3 parse_1cpu_perfmonkey.py 2102353TJWFSP3100020.csv_cpu_all")
        print("\nCreates ONE combined file with all controllers")
        print("Same Row # for same timestamp across all controllers")
        sys.exit(1)
    
    input_file = sys.argv[1]
    
    if not Path(input_file).exists():
        print(f"Error: File not found: {input_file}")
        sys.exit(1)
    
    process_controller_file(input_file)


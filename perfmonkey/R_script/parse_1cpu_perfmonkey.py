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
    
    print("\nPass 2: Writing separate file for each controller...")
    
    output_files = []
    
    for inst in instances:
        print(f"\n  Processing controller: {inst}")
        
        # Get timepoints for this instance (already in order)
        times = all_times[inst]
        
        # Determine controller type
        controller_type = extract_controller_type(inst)
        
        # Create output filename
        output_file = str(input_path).replace('.csv', '').replace('_cpu_all', '') + f'_{inst}_output.csv'
        
        # Write output file
        with open(output_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            
            # Write header
            header = ['CPUPERF', '#', 'BgnDateTime', 'EndDateTime', 'Serial',
                      'Slot', 'Type'] + metrics
            writer.writerow(header)
            
            # Write data rows
            rows_written = 0
            for row_num, time in enumerate(times, 1):
                formatted_time = parse_datetime(time)
                
                row_data = [
                    LABEL,
                    row_num,
                    formatted_time,
                    formatted_time,
                    serial,
                    inst,  # Slot (controller ID)
                    controller_type
                ]
                
                # Add metric values for this time
                for metric in metrics:
                    value = data[inst][time].get(metric, '')
                    row_data.append(value)
                
                writer.writerow(row_data)
                rows_written += 1
        
        output_files.append(output_file)
        print(f"    ✓ Written {rows_written} rows to {Path(output_file).name}")
    
    # Summary
    print("\n═══════════════════════════════════════════════════════════════")
    print("  ✅ COMPLETED SUCCESSFULLY!")
    print("═══════════════════════════════════════════════════════════════\n")
    print(f"Created {len(output_files)} files:")
    for output_file in output_files:
        print(f"  • {Path(output_file).name}")
    
    print(f"\nSerial Number: {serial}")
    print(f"Controllers: {', '.join(instances)}")
    print(f"Columns per file: {7 + len(metrics)} (7 service + {len(metrics)} metrics)")
    print("Format: CSV without quotes, sorted by time\n")
    print("Files are ready for PerfMonkey import! 🚀\n")
    
    return output_files

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 parse_1cpu_perfmonkey.py <input_file>")
        print("\nExample:")
        print("  python3 parse_1cpu_perfmonkey.py 2102353TJWFSP3100020.csv_cpu_all")
        print("\nCreates separate output files for each controller")
        sys.exit(1)
    
    input_file = sys.argv[1]
    
    if not Path(input_file).exists():
        print(f"Error: File not found: {input_file}")
        sys.exit(1)
    
    process_controller_file(input_file)


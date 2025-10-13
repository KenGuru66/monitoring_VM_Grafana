#!/usr/bin/env python3
"""
parse_disk_perfmonkey_single.py - Disk performance parser for PerfMonkey
Creates ONE output file with all disks, sorted by time
Memory-efficient streaming processing
"""

import sys
import csv
import re
from datetime import datetime
from pathlib import Path
from collections import defaultdict

# PerfMonkey format constants
LABEL = "RGPERF"
MPCNT = "1"
PGCNT = "1"
LDCNT = "1"
ALIAS = "-"
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
    """Parse datetime from various formats"""
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

def process_disk_file(input_file):
    """
    Process disk performance file and create single output file with all disks
    Format: All disks for each timepoint, sorted by time
    """
    input_path = Path(input_file)
    
    print("\n═══════════════════════════════════════════════════════════════")
    print("  DISK PERFORMANCE → PERFMONKEY FORMAT (Single File)")
    print("═══════════════════════════════════════════════════════════════\n")
    
    # Extract serial number
    serial = extract_serial(input_path.name)
    print(f"Serial Number: {serial}\n")
    
    print("Pass 1: Reading and organizing data...")
    
    # Data structure: data[instance][time][metric] = value
    data = defaultdict(lambda: defaultdict(dict))
    all_metrics = set()
    all_times = set()
    all_instances = set()
    
    # Read all data
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            instance = row['InstanceName']
            time = row['Time']
            metric = clean_metric_name(row['Metric'])
            value = row['Value']
            
            data[instance][time][metric] = value
            all_metrics.add(metric)
            all_times.add(time)
            all_instances.add(instance)
    
    # Sort everything
    metrics = sorted(all_metrics)
    times = sorted(all_times)
    instances = sorted(all_instances)
    
    print(f"  ✓ Instances (disks): {len(instances)}")
    print(f"  ✓ Timepoints: {len(times)}")
    print(f"  ✓ Metrics: {len(metrics)}")
    print(f"  ✓ Total rows to write: {len(instances) * len(times)}\n")
    
    # Create output filename
    output_file = str(input_path).replace('.csv', '').replace('_disk_all', '') + '_DISK_PERFMONKEY.csv'
    
    print("Pass 2: Writing output file...")
    
    # Write output
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        
        # Write header
        header = ['RGPERF', '#', 'BgnDateTime', 'EndDateTime', 'Serial',
                  'MpCnt', 'Rg', 'PgCnt', 'LdCnt', 'Alias'] + metrics
        writer.writerow(header)
        
        # Write data: for each timepoint, write all instances
        rows_written = 0
        for time_idx, time in enumerate(times, 1):
            formatted_time = parse_datetime(time)
            
            for instance in instances:
                # Check if this instance has data for this time
                # Skip row if all metrics are empty
                metric_values = [data[instance][time].get(metric, '') for metric in metrics]
                if all(v == '' for v in metric_values):
                    continue  # Skip this row - no data for this instance at this time
                
                row_data = [
                    LABEL,
                    time_idx,  # Same row number for all disks at this time
                    formatted_time,
                    formatted_time,
                    serial,
                    MPCNT,
                    instance,
                    PGCNT,
                    LDCNT,
                    ALIAS
                ]
                
                # Add metric values
                row_data.extend(metric_values)
                
                writer.writerow(row_data)
                rows_written += 1
            
            # Progress indicator
            if time_idx % 100 == 0:
                print(f"  • Processed {time_idx}/{len(times)} timepoints ({rows_written} rows)...")
    
    print(f"  ✓ Written {rows_written} rows\n")
    
    # Summary
    print("═══════════════════════════════════════════════════════════════")
    print("  ✅ COMPLETED SUCCESSFULLY!")
    print("═══════════════════════════════════════════════════════════════\n")
    print(f"Output file: {Path(output_file).name}")
    print(f"  • Serial Number: {serial}")
    print(f"  • Disks: {len(instances)}")
    print(f"  • Timepoints: {len(times)}")
    print(f"  • Metrics: {len(metrics)}")
    print(f"  • Total rows: {rows_written}")
    print("\nFile is ready for PerfMonkey import! 🚀\n")
    
    return output_file

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 parse_disk_perfmonkey_single.py <input_file>")
        print("\nExample:")
        print("  python3 parse_disk_perfmonkey_single.py 2102353TJWFSP3100020.csv_disk_all")
        print("\nCreates ONE output file with all disks sorted by time")
        sys.exit(1)
    
    input_file = sys.argv[1]
    
    if not Path(input_file).exists():
        print(f"Error: File not found: {input_file}")
        sys.exit(1)
    
    process_disk_file(input_file)


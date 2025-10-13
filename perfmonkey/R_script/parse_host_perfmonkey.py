#!/usr/bin/env python3
"""
parse_host_perfmonkey.py - Host performance parser for PerfMonkey
Creates ONE output file with all hosts
Synchronized: Only common timepoints across all hosts
Same Row # for same timestamp across all hosts
Memory-efficient streaming processing
"""

import sys
import csv
import re
from datetime import datetime
from pathlib import Path
from collections import defaultdict

# PerfMonkey format constants
LABEL = "HAPERF"
MPCNT = "1"
DACNT = "1"
PGCNT = "1"
RGCNT = "1"
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
            # Handle ISO format with 'Z' (e.g., 2025-09-11T02:05:00Z)
            if time_str.endswith('Z'):
                # Remove 'Z' and parse as naive datetime, then format
                dt = datetime.fromisoformat(time_str[:-1])
                return dt.strftime(OUTPUT_FMT)
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

def process_host_file(input_file):
    """
    Process host performance file and create single output file with all hosts
    Format: All hosts for each timepoint, sorted by time
    Only common timepoints where ALL hosts have data
    """
    input_path = Path(input_file)
    
    print("\n═══════════════════════════════════════════════════════════════")
    print("  HOST PERFORMANCE → PERFMONKEY FORMAT (Single File)")
    print("═══════════════════════════════════════════════════════════════\n")
    
    # Extract serial number
    serial = extract_serial(input_path.name)
    print(f"Serial Number: {serial}\n")
    
    print("Pass 1: Reading and organizing data...")
    
    # Data structure: data[instance][time][metric] = value
    data = defaultdict(lambda: defaultdict(dict))
    all_metrics = set()
    all_times_per_instance = defaultdict(set)  # Track times per instance
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
            all_times_per_instance[instance].add(time)
            all_instances.add(instance)
    
    # Sort instances and metrics
    metrics = sorted(all_metrics)
    instances = sorted(all_instances)
    
    print(f"  ✓ Instances (hosts): {len(instances)}")
    print(f"  ✓ Metrics: {len(metrics)}")
    
    # Show timepoints per instance
    print("\n  Timepoints per host (first 5 hosts):")
    for i, inst in enumerate(instances[:5]):
        print(f"    • {inst}: {len(all_times_per_instance[inst])} timepoints")
    if len(instances) > 5:
        print(f"    ... and {len(instances) - 5} more hosts")
    
    # Find common timepoints across all hosts
    print("\n  Finding common timepoints across all hosts...")
    if not instances:
        common_times = []
    else:
        common_times_set = set(all_times_per_instance[instances[0]])
        for inst in instances[1:]:
            common_times_set = common_times_set.intersection(all_times_per_instance[inst])
        
        # Sort common timepoints
        common_times_candidate = sorted(list(common_times_set))
        
        # Additional filter: Keep only times where ALL hosts have at least one metric with data
        common_times = []
        for time in common_times_candidate:
            # Check if all hosts have at least one non-empty metric for this time
            all_hosts_have_data = True
            for inst in instances:
                metric_values = [data[inst][time].get(metric, '') for metric in metrics]
                if all(v == '' for v in metric_values):
                    all_hosts_have_data = False
                    break
            
            if all_hosts_have_data:
                common_times.append(time)
    
    # Calculate filtered out timepoints
    total_unique_times = len(set().union(*all_times_per_instance.values()))
    filtered_out = total_unique_times - len(common_times)
    
    print(f"  ✓ Total unique timepoints: {total_unique_times}")
    print(f"  ✓ Common timepoints (all {len(instances)} hosts): {len(common_times)}")
    if filtered_out > 0:
        print(f"  ⚠ Filtered out {filtered_out} non-common timepoints")
    print(f"  ✓ Total rows to write: {len(instances) * len(common_times)}\n")
    
    # Create output filename
    output_file = str(input_path).replace('.csv', '').replace('_host_all', '') + '_HOST_PERFMONKEY.csv'
    
    print("Pass 2: Writing output file...")
    
    # Write output
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        
        # Write header
        header = ['HAPERF', '#', 'BgnDateTime', 'EndDateTime', 'Serial',
                  'DefMp', 'DaCnt', 'RgCnt', 'PgCnt', 'Alias'] + metrics
        writer.writerow(header)
        
        # Write data: for each COMMON timepoint, write all instances
        rows_written = 0
        for time_idx, time in enumerate(common_times, 1):
            formatted_time = parse_datetime(time)
            
            for instance in instances:
                # Get metric values for this instance at this time
                # Since we're using common_times, all instances should have this time
                metric_values = [data[instance][time].get(metric, '') for metric in metrics]
                
                row_data = [
                    LABEL,
                    time_idx,  # Same row number for all hosts at this time
                    formatted_time,
                    formatted_time,
                    serial,
                    MPCNT,
                    DACNT,
                    RGCNT,
                    PGCNT,
                    instance  # Alias (hostname)
                ]
                
                # Add metric values
                row_data.extend(metric_values)
                
                writer.writerow(row_data)
                rows_written += 1
            
            # Progress indicator
            if time_idx % 100 == 0:
                print(f"  • Processed {time_idx}/{len(common_times)} timepoints ({rows_written} rows)...")
    
    print(f"  ✓ Written {rows_written} rows\n")
    
    # Summary
    print("═══════════════════════════════════════════════════════════════")
    print("  ✅ COMPLETED SUCCESSFULLY!")
    print("═══════════════════════════════════════════════════════════════\n")
    print(f"Output file: {Path(output_file).name}")
    print(f"  • Serial Number: {serial}")
    print(f"  • Hosts: {len(instances)}")
    print(f"  • Common timepoints: {len(common_times)} (synchronized)")
    if filtered_out > 0:
        print(f"  • Filtered out: {filtered_out} non-common timepoints")
    print(f"  • Metrics: {len(metrics)}")
    print(f"  • Total rows: {rows_written} ({len(instances)} hosts × {len(common_times)} timepoints)")
    print("\nFormat: All hosts in ONE file")
    print("        Same Row # for same timestamp across all hosts")
    print("        Only common timepoints (synchronized)")
    print("\nFile is ready for PerfMonkey import! 🚀\n")
    
    return output_file

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 parse_host_perfmonkey.py <input_file>")
        print("\nExample:")
        print("  python3 parse_host_perfmonkey.py 2102353TJWFSP3100020.csv_host_all")
        print("\nCreates ONE output file with all hosts")
        print("Only common timepoints (synchronized across all hosts)")
        print("Same Row # for same timestamp across all hosts")
        sys.exit(1)
    
    input_file = sys.argv[1]
    
    if not Path(input_file).exists():
        print(f"Error: File not found: {input_file}")
        sys.exit(1)
    
    process_host_file(input_file)


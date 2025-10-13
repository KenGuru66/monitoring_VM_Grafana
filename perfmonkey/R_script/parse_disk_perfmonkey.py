#!/usr/bin/env python3
"""
parse_disk_perfmonkey.py - Disk performance parser for PerfMonkey format
Python replacement for parse_disk.R with memory-efficient streaming processing

Features:
- Automatic serial number extraction from filename
- Metric name cleaning (commas, infinity symbols)
- Time sorting
- Separate output files for each disk
- Memory-efficient processing for large files
- Parallel-ready (can be called multiple times)
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
TIMEDATE_FMT = "%Y/%m/%d %H:%M"
OUTPUT_FMT = "%m/%d/%y %H:%M:%S"

def extract_serial(filename):
    """Extract serial number from filename (15+ alphanumeric chars)"""
    match = re.search(r'[0-9A-Z]{15,}', filename)
    if match:
        return match.group(0)
    return "111111"

def clean_metric_name(metric):
    """Clean metric name for PerfMonkey compatibility"""
    metric = metric.replace(',', '_')
    metric = metric.replace('∞', '8')
    metric = metric.replace('"', '')
    return metric

def parse_datetime(time_str):
    """Parse datetime from various formats"""
    # Try ISO format first (2025-09-11T02:05:00Z)
    try:
        if 'T' in time_str:
            dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
            return dt.strftime(OUTPUT_FMT)
    except:
        pass
    
    # Try default format
    try:
        dt = datetime.strptime(time_str, TIMEDATE_FMT)
        return dt.strftime(OUTPUT_FMT)
    except:
        pass
    
    return time_str

def process_disk_file(input_file):
    """
    Process disk performance file and create separate output files for each disk
    Memory-efficient: processes data in streaming mode
    """
    input_path = Path(input_file)
    
    print("\n═══════════════════════════════════════════════════════════════")
    print("  DISK PERFORMANCE → PERFMONKEY FORMAT CONVERTER (Python)")
    print("═══════════════════════════════════════════════════════════════\n")
    
    # Extract serial number
    serial = extract_serial(input_path.name)
    print(f"Extracting Serial Number from filename...")
    print(f"  ✓ Extracted Serial Number: {serial}\n")
    
    # First pass: collect instances and metrics
    print("Reading CSV file...")
    instances = set()
    metrics_global = set()
    
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            instances.add(row['InstanceName'])
            metrics_global.add(clean_metric_name(row['Metric']))
    
    instances = sorted(instances)
    metrics_global = sorted(metrics_global)
    
    print(f"  ✓ Read file")
    print(f"\nData summary:")
    print(f"  • Unique instances (disks): {len(instances)}")
    print(f"  • Unique metrics: {len(metrics_global)}")
    print(f"  • Disk IDs: {', '.join(instances[:10])}")
    if len(instances) > 10:
        print(f"    ... and {len(instances) - 10} more")
    
    # Process each instance separately
    print("\nProcessing each disk separately...\n")
    output_files = []
    
    for inst in instances:
        print(f"  Processing disk: {inst}")
        
        # Collect data for this instance only
        inst_data = defaultdict(dict)  # inst_data[time][metric] = value
        timepoints = set()
        
        with open(input_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter=';')
            for row in reader:
                if row['InstanceName'] == inst:
                    time = row['Time']
                    metric = clean_metric_name(row['Metric'])
                    value = row['Value']
                    inst_data[time][metric] = value
                    timepoints.add(time)
        
        # Sort timepoints
        timepoints = sorted(timepoints)
        
        print(f"    • Timepoints: {len(timepoints)}")
        print(f"    • Rows: {len(inst_data)}")
        
        # Get metrics for this instance
        metrics = sorted(set(metric for time_data in inst_data.values() for metric in time_data.keys()))
        
        # Create output filename
        inst_clean = inst.replace('.', '_').replace('/', '_')
        output_file = str(input_path).replace('.csv', f'_{inst_clean}_output.csv')
        
        # Write output file
        with open(output_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            
            # Write header
            header = ['RGPERF', '#', 'BgnDateTime', 'EndDateTime', 'Serial',
                      'MpCnt', 'Rg', 'PgCnt', 'LdCnt', 'Alias'] + metrics
            writer.writerow(header)
            
            # Write data rows
            for row_num, time in enumerate(timepoints, 1):
                formatted_time = parse_datetime(time)
                row_data = [
                    LABEL,
                    row_num,
                    formatted_time,
                    formatted_time,
                    serial,
                    MPCNT,
                    inst,
                    PGCNT,
                    LDCNT,
                    ALIAS
                ]
                
                # Add metric values
                for metric in metrics:
                    row_data.append(inst_data[time].get(metric, ''))
                
                writer.writerow(row_data)
        
        output_files.append(output_file)
        print(f"    ✓ Processed {len(timepoints)} rows\n")
    
    # Summary
    print("═══════════════════════════════════════════════════════════════")
    print("  ✅ COMPLETED SUCCESSFULLY!")
    print("═══════════════════════════════════════════════════════════════\n")
    print(f"Total files created: {len(output_files)}")
    print(f"Serial Number: {serial}")
    print(f"Metrics per file: varies by disk\n")
    
    print("Output files created:")
    for output_file in output_files:
        print(f"  ✓ {Path(output_file).name}")
    
    print("\nFiles are ready for PerfMonkey import! 🚀\n")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 parse_disk_perfmonkey.py <input_file>")
        print("\nExample:")
        print("  python3 parse_disk_perfmonkey.py 2102353TJWFSP3100020.csv_disk_all")
        sys.exit(1)
    
    input_file = sys.argv[1]
    
    if not Path(input_file).exists():
        print(f"Error: File not found: {input_file}")
        sys.exit(1)
    
    process_disk_file(input_file)


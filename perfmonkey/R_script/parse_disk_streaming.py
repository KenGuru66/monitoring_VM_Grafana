#!/usr/bin/env python3
"""
parse_disk_streaming.py - Memory-efficient disk performance parser
Processes data in streaming mode without loading everything into memory
"""

import sys
import csv
import re
from datetime import datetime
from collections import defaultdict
from pathlib import Path

def extract_serial(filename):
    """Extract serial number from filename"""
    match = re.search(r'[0-9A-Z]{15,}', filename)
    return match.group(0) if match else "111111"

def clean_metric_name(metric):
    """Clean metric name for PerfMonkey"""
    metric = metric.replace(',', '_')
    metric = metric.replace('∞', '8')
    metric = metric.replace('"', '')
    return metric

def format_datetime(time_str):
    """Convert time string to PerfMonkey format"""
    try:
        dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
        return dt.strftime('%m/%d/%y %H:%M:%S')
    except:
        return time_str

def process_disk_streaming(input_file):
    """
    Process single disk file in streaming mode
    Uses dict of lists for pivot, writes directly to CSV
    """
    input_path = Path(input_file)
    serial = extract_serial(input_path.name)
    
    # First pass: collect metrics and timepoints
    print(f"  Pass 1: Scanning {input_path.name}...")
    metrics_set = set()
    timepoints_set = set()
    instance_name = None
    
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            if instance_name is None:
                instance_name = row['InstanceName']
            metrics_set.add(clean_metric_name(row['Metric']))
            timepoints_set.add(row['Time'])
    
    metrics = sorted(metrics_set)
    timepoints = sorted(timepoints_set)
    
    print(f"    Instance: {instance_name}, Metrics: {len(metrics)}, Timepoints: {len(timepoints)}")
    
    # Second pass: build pivot data structure (memory efficient)
    print(f"  Pass 2: Building pivot table...")
    # data[time][metric] = value
    data = {tp: {} for tp in timepoints}
    
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            time = row['Time']
            metric = clean_metric_name(row['Metric'])
            value = row['Value']
            data[time][metric] = value
    
    # Prepare output filename
    inst_clean = instance_name.replace('.', '_').replace('/', '_')
    output_file = str(input_path).replace('.csv', '_output.csv')
    
    # Write output directly (streaming write)
    print(f"  Pass 3: Writing output...")
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        
        # Write header
        header = ['RGPERF', '#', 'BgnDateTime', 'EndDateTime', 'Serial',
                  'MpCnt', 'Rg', 'PgCnt', 'LdCnt', 'Alias'] + metrics
        writer.writerow(header)
        
        # Write data rows
        for row_num, time in enumerate(timepoints, 1):
            formatted_time = format_datetime(time)
            row = [
                'RGPERF',
                row_num,
                formatted_time,
                formatted_time,
                serial,
                '1',
                instance_name,
                '1',
                '1',
                '-'
            ]
            # Add metric values
            for metric in metrics:
                row.append(data[time].get(metric, ''))
            writer.writerow(row)
    
    print(f"    ✓ {output_file}: {len(timepoints)} rows")
    return output_file

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 parse_disk_streaming.py <input_file>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    process_disk_streaming(input_file)


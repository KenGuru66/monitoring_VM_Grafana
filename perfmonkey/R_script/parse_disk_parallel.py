#!/usr/bin/env python3
"""
parse_disk_parallel.py - Multi-threaded disk performance parser
Uses multiprocessing to utilize all CPU cores efficiently
Memory-efficient: splits data first, then processes in parallel
"""

import sys
import csv
import re
import os
import tempfile
import shutil
from datetime import datetime
from pathlib import Path
from collections import defaultdict
from multiprocessing import Pool, cpu_count
import time

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

def process_single_disk(args):
    """
    Process a single disk file (called by multiprocessing)
    Returns: (instance_name, output_file, num_rows)
    """
    disk_file, serial, output_dir = args
    
    try:
        # Read disk file
        inst_data = defaultdict(dict)
        timepoints = set()
        instance_name = None
        
        with open(disk_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter=';')
            for row in reader:
                if instance_name is None:
                    instance_name = row['InstanceName']
                time = row['Time']
                metric = clean_metric_name(row['Metric'])
                value = row['Value']
                inst_data[time][metric] = value
                timepoints.add(time)
        
        # Sort timepoints
        timepoints = sorted(timepoints)
        
        # Get metrics
        metrics = sorted(set(metric for time_data in inst_data.values() for metric in time_data.keys()))
        
        # Create output filename
        inst_clean = instance_name.replace('.', '_').replace('/', '_')
        disk_basename = Path(disk_file).stem.replace('disk_', '')
        output_file = output_dir / f"{Path(output_dir).name}_{inst_clean}_output.csv"
        
        # Write output
        with open(output_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            
            # Header
            header = ['RGPERF', '#', 'BgnDateTime', 'EndDateTime', 'Serial',
                      'MpCnt', 'Rg', 'PgCnt', 'LdCnt', 'Alias'] + metrics
            writer.writerow(header)
            
            # Data rows
            for row_num, time in enumerate(timepoints, 1):
                formatted_time = parse_datetime(time)
                row_data = [
                    LABEL, row_num, formatted_time, formatted_time, serial,
                    MPCNT, instance_name, PGCNT, LDCNT, ALIAS
                ]
                row_data.extend(inst_data[time].get(metric, '') for metric in metrics)
                writer.writerow(row_data)
        
        return (instance_name, str(output_file), len(timepoints))
    
    except Exception as e:
        return (None, str(disk_file), f"Error: {e}")

def split_by_disks(input_file, temp_dir):
    """
    Split input file by disk instances using pure Python
    Returns list of (instance, file_path) tuples
    """
    print("Step 1: Splitting file by disk instances...")
    start = time.time()
    
    # Read header
    with open(input_file, 'r', encoding='utf-8') as f:
        header = f.readline()
    
    # Open files for each instance
    disk_files = {}
    
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            instance = row['InstanceName']
            inst_clean = instance.replace('.', '_').replace('/', '_')
            
            if instance not in disk_files:
                file_path = temp_dir / f"disk_{inst_clean}.csv"
                disk_files[instance] = open(file_path, 'w', encoding='utf-8')
                disk_files[instance].write(header)
            
            # Write row
            disk_files[instance].write(';'.join([
                row['Resource'], row['Metric'], row['InstanceName'],
                row['Value'], row['Time'], row['UnixTime']
            ]) + '\n')
    
    # Close all files
    for f in disk_files.values():
        f.close()
    
    elapsed = time.time() - start
    disk_file_paths = [(inst, temp_dir / f"disk_{inst.replace('.', '_').replace('/', '_')}.csv") 
                       for inst in sorted(disk_files.keys())]
    
    print(f"  ✓ Split into {len(disk_file_paths)} files in {elapsed:.1f}s\n")
    
    return disk_file_paths

def main(input_file, num_workers=None):
    """
    Main processing function with parallel execution
    """
    input_path = Path(input_file)
    
    if num_workers is None:
        num_workers = max(1, cpu_count() - 2)  # Leave 2 cores for system
    
    print("\n═══════════════════════════════════════════════════════════════")
    print("  DISK PERFORMANCE → PERFMONKEY (PARALLEL MODE)")
    print("═══════════════════════════════════════════════════════════════\n")
    print(f"CPU cores available: {cpu_count()}")
    print(f"Using {num_workers} parallel workers\n")
    
    # Extract serial number
    serial = extract_serial(input_path.name)
    print(f"Serial Number: {serial}\n")
    
    # Create temp directory
    temp_dir = Path(tempfile.mkdtemp(prefix='disk_split_', dir=input_path.parent))
    output_dir = input_path.parent
    
    try:
        # Split file by disks
        disk_files = split_by_disks(input_file, temp_dir)
        
        # Prepare arguments for parallel processing
        process_args = [(file_path, serial, output_dir) for _, file_path in disk_files]
        
        # Process in parallel
        print(f"Step 2: Processing {len(disk_files)} disks in parallel...")
        print(f"(Monitor CPU and memory usage in another terminal)\n")
        
        start = time.time()
        
        with Pool(processes=num_workers) as pool:
            results = pool.map(process_single_disk, process_args)
        
        elapsed = time.time() - start
        
        # Display results
        print("\n═══════════════════════════════════════════════════════════════")
        print("  ✅ COMPLETED SUCCESSFULLY!")
        print("═══════════════════════════════════════════════════════════════\n")
        
        successful = [r for r in results if r[0] is not None]
        
        print(f"Files processed: {len(successful)}/{len(disk_files)}")
        print(f"Processing time: {elapsed:.1f}s")
        print(f"Average per file: {elapsed/len(disk_files):.1f}s")
        print(f"Serial Number: {serial}\n")
        
        print("Output files created:")
        for inst, output_file, rows in successful:
            print(f"  ✓ {Path(output_file).name} ({rows} rows)")
        
        # Show any errors
        errors = [r for r in results if r[0] is None]
        if errors:
            print("\nErrors:")
            for _, file, error in errors:
                print(f"  ✗ {file}: {error}")
        
        print("\nFiles are ready for PerfMonkey import! 🚀\n")
    
    finally:
        # Cleanup temp directory
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 parse_disk_parallel.py <input_file> [num_workers]")
        print("\nExample:")
        print("  python3 parse_disk_parallel.py 2102353TJWFSP3100020.csv_disk_all 30")
        print("\nnum_workers: Number of parallel workers (default: CPU count - 2)")
        sys.exit(1)
    
    input_file = sys.argv[1]
    num_workers = int(sys.argv[2]) if len(sys.argv) > 2 else None
    
    if not Path(input_file).exists():
        print(f"Error: File not found: {input_file}")
        sys.exit(1)
    
    main(input_file, num_workers)


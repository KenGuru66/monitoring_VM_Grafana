#!/usr/bin/env python3
"""
Правильный маппинг ресурсов и метрик Huawei OceanStor.
Каждый ресурс имеет только применимые к нему метрики.
"""

# Маппинг ID ресурсов → названия
RESOURCE_MAPPING = {
    "207": "Controller",
    "212": "FC Port",
    "216": "Storage Pool",
    "266": "Disk Domain",
    "11": "LUN",
    "21": "Host"
}

# Маппинг ID метрик → названия
METRIC_MAPPING = {
    # Common metrics
    "18": "Usage (%)",
    "22": "Total IOPS (IO/s)",
    "25": "Read IOPS (IO/s)",
    "28": "Write IOPS (IO/s)",
    "23": "Read Bandwidth (MB/s)",
    "26": "Write Bandwidth (MB/s)",
    "240": "Average Queue Depth",
    "384": "Avg. Read I/O Response Time (us)",
    "385": "Avg. Write I/O Response Time (us)",
    "24": "Avg. Read I/O Size (KB)",
    "27": "Avg. Write I/O Size (KB)",
    "228": "Avg. I/O Size (KB)",
    "369": "Service Time (us)",
    
    # LUN-specific metrics
    "1079": "SCSI IOPS (IO/s)",
    "1073": "ISCSI IOPS (IO/s)",
    "1158": "WRITE SAME Command Bandwidth (MB/s)",
    "1154": "Unmap Command Bandwidth (MB/s)",
    "1162": "Full Copy Read Request Bandwidth (MB/s)",
    "1166": "Full Copy Write Request Bandwidth (MB/s)",
    "1170": "ODX Read Request Bandwidth (MB/s)",
    "1174": "ODX Write Request Bandwidth (MB/s)",
    "1332": "Post-Process Deduplication Read Bandwidth (MB/s)",
    "1333": "Post-Process Deduplication Write Bandwidth (MB/s)",
    "1334": "Post-Process Deduplication Fingerprint Read Bandwidth (MB/s)",
    "1335": "Post-Process Deduplication Fingerprint Write Bandwidth (MB/s)",
    "1337": "Post-Process Deduplication and Reduction Read Bandwidth (MB/s)",
    "1338": "Post-Process Deduplication and Reduction Write Bandwidth (MB/s)",
    "1188": "VAAI Bandwidth (MB/s)",
    
    # Controller-specific metrics
    "1633": "Avg. Corrected CPU Usage (%)",
    "1298": "Back-End Partition CPU Usage (%)",
    "1297": "Front-End Partition CPU Usage (%)",
    "68": "Avg. CPU Usage (%)",
    "1299": "KV CPU Usage (%)",
    "260": "Back-End Traffic (MB/s)",
    "261": "Back-End Read Traffic (MB/s)",
    "262": "Back-End Write Traffic (MB/s)",
    "93": "Read Cache Hit Ratio (%)",
    "95": "Write Cache Hit Ratio (%)",
    "333": "Cache Water (%)",
    "627": "NFS Operation Count Per Second",
    "1074": "CIFS Operation Count Per Second",
    
    # Disk-specific metrics
    "1075": "Disk Max. Usage (%)",
    
    # I/O Granularity Distribution
    "1182": "Read I/O Granularity Distribution: [0K,4K) (%)",
    "33": "Read I/O Granularity Distribution: [4K,8K) (%)",
    "34": "Read I/O Granularity Distribution: [8K,16K) (%)",
    "35": "Read I/O Granularity Distribution: [16K,32K) (%)",
    "36": "Read I/O Granularity Distribution: [32K,64K) (%)",
    "37": "Read I/O Granularity Distribution: [64K,128K) (%)",
    "1183": "Read I/O Granularity Distribution: [128K,+∞) (%)",
    "1184": "Write I/O Granularity Distribution: [0K,4K) (%)",
    "44": "Write I/O Granularity Distribution: [4K,8K) (%)",
    "45": "Write I/O Granularity Distribution: [8K,16K) (%)",
    "46": "Write I/O Granularity Distribution: [16K,32K) (%)",
    "47": "Write I/O Granularity Distribution: [32K,64K) (%)",
    "48": "Write I/O Granularity Distribution: [64K,128K) (%)",
    "1185": "Write I/O Granularity Distribution: [128K,+∞) (%)",
}

# Маппинг: Ресурс → Список применимых метрик
RESOURCE_TO_METRICS = {
    "207": [  # Controller
        "1633", "1298", "1297", "68", "1299",  # CPU метрики
        "260", "261", "262",  # Back-end traffic
        "93", "95", "333",  # Cache metrics
        "22", "25", "28", "23", "26",  # IOPS & Bandwidth
        "240", "384", "385", "24", "27", "228", "369",  # Performance
        "627", "1074",  # NFS/CIFS operations
        "1182", "33", "34", "35", "36", "37", "1183",  # Read I/O Distribution
        "1184", "44", "45", "46", "47", "48", "1185",  # Write I/O Distribution
    ],
    "212": [  # FC Port
        "22", "25", "28", "23", "26",  # IOPS & Bandwidth
        "240", "384", "385", "24", "27", "228", "369",  # Performance
        "1182", "33", "34", "35", "36", "37", "1183",  # Read I/O Distribution
        "1184", "44", "45", "46", "47", "48", "1185",  # Write I/O Distribution
    ],
    "216": [  # Storage Pool
        "18",  # Usage
        "22", "25", "28", "23", "26",  # IOPS & Bandwidth
        "240", "384", "385", "24", "27", "228", "369",  # Performance
    ],
    "266": [  # Disk Domain
        "1075",  # Disk Max Usage
        "22", "25", "28", "23", "26",  # IOPS & Bandwidth
        "240", "384", "385", "24", "27", "228", "369",  # Performance
        "1182", "33", "34", "35", "36", "37", "1183",  # Read I/O Distribution
        "1184", "44", "45", "46", "47", "48", "1185",  # Write I/O Distribution
    ],
    "11": [  # LUN
        "18",  # Usage
        "1079", "1073",  # SCSI/ISCSI IOPS
        "22", "25", "28", "23", "26",  # IOPS & Bandwidth
        "240", "384", "385", "24", "27", "228", "369",  # Performance
        "1158", "1154", "1162", "1166", "1170", "1174",  # Commands
        "1332", "1333", "1334", "1335", "1337", "1338",  # Deduplication
        "1188",  # VAAI
        "1182", "33", "34", "35", "36", "37", "1183",  # Read I/O Distribution
        "1184", "44", "45", "46", "47", "48", "1185",  # Write I/O Distribution
    ],
    "21": [  # Host
        "22", "25", "28", "23", "26",  # IOPS & Bandwidth
        "240", "384", "385", "24", "27", "228", "369",  # Performance
        "1182", "33", "34", "35", "36", "37", "1183",  # Read I/O Distribution
        "1184", "44", "45", "46", "47", "48", "1185",  # Write I/O Distribution
    ],
}

# Список ресурсов по умолчанию
DEFAULT_RESOURCES = ["207", "212", "216", "266", "11", "21"]

if __name__ == "__main__":
    print("=== Ресурсы и их метрики ===\n")
    for res_id in DEFAULT_RESOURCES:
        res_name = RESOURCE_MAPPING[res_id]
        metrics = RESOURCE_TO_METRICS[res_id]
        print(f"📊 {res_name} (ID: {res_id})")
        print(f"   Метрик: {len(metrics)}")
        for metric_id in metrics[:5]:  # Show first 5
            print(f"   - {metric_id}: {METRIC_MAPPING[metric_id]}")
        if len(metrics) > 5:
            print(f"   ... и еще {len(metrics) - 5} метрик")
        print()


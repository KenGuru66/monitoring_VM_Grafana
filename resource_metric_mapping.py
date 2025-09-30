#!/usr/bin/env python3
"""
Маппинг ID ресурсов и метрик Huawei OceanStor к их названиям.
Используется для генерации дашбордов Grafana.
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

# Маппинг ID метрик → названия (на основе документации Huawei OceanStor)
METRIC_MAPPING = {
    "18": "Usage (%)",
    "22": "Total IOPS (IO/s)",
    "25": "Read IOPS (IO/s)",
    "28": "Write IOPS (IO/s)",
    "23": "Read Bandwidth (MB/s)",
    "26": "Write Bandwidth (MB/s)",
    "1079": "SCSI IOPS (IO/s)",
    "1073": "ISCSI IOPS (IO/s)",
    "627": "NFS Operation Count Per Second",
    "1074": "CIFS Operation Count Per Second",
    "240": "Average Queue Depth",
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
    "1633": "Avg. Corrected CPU Usage (%)",
    "260": "Back-End Traffic (MB/s)",
    "261": "Back-End Read Traffic (MB/s)",
    "262": "Back-End Write Traffic (MB/s)",
    "1298": "Back-End Partition CPU Usage (%)",
    "1297": "Front-End Partition CPU Usage (%)",
    "68": "Avg. CPU Usage (%)",
    "1299": "KV CPU Usage (%)",
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
    "1188": "VAAI Bandwidth (MB/s)",
    "93": "Read Cache Hit Ratio (%)",
    "95": "Write Cache Hit Ratio (%)",
    "333": "Cache Water (%)",
    "384": "Avg. Read I/O Response Time (us)",
    "385": "Avg. Write I/O Response Time (us)",
    "24": "Avg. Read I/O Size (KB)",
    "27": "Avg. Write I/O Size (KB)",
    "228": "Avg. I/O Size (KB)",
    "369": "Service Time (us)",
    "1075": "Disk Max. Usage (%)"
}

# Группы ресурсов для дашборда
DEFAULT_RESOURCES = ["207", "212", "216", "266", "11", "21"]

# Группы метрик для дашборда
DEFAULT_METRICS = [
    "18", "22", "25", "28", "23", "26", "1079", "1073", "627", "1074",
    "240", "1158", "1154", "1162", "1166", "1170", "1174", "1332", "1333",
    "1334", "1335", "1337", "1338", "1633", "260", "261", "262", "1298",
    "1297", "68", "1299", "1182", "33", "34", "35", "36", "37", "1183",
    "1184", "44", "45", "46", "47", "48", "1185", "1188", "93", "95",
    "333", "384", "385", "24", "27", "228", "369", "1075"
]

if __name__ == "__main__":
    print("=== Ресурсы ===")
    for res_id in DEFAULT_RESOURCES:
        print(f"{res_id}: {RESOURCE_MAPPING[res_id]}")
    
    print(f"\n=== Метрики (всего {len(DEFAULT_METRICS)}) ===")
    for metric_id in DEFAULT_METRICS:
        print(f"{metric_id}: {METRIC_MAPPING[metric_id]}")

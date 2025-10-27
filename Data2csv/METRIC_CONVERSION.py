#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
METRIC_CONVERSION - Словарь конверсии единиц измерения для метрик Huawei OceanStor

Используется для метрик, где сырые данные в .dat файлах имеют другие единицы 
измерения, чем указано в названии метрики.

Ключ: metric_id (str)
Значение: коэффициент деления (int) - сырое_значение / коэффициент

Примеры:
- Bandwidth метрики: сырые данные в KB/s, название метрики в MB/s → делим на 1024
- Latency метрики: сырые данные в us (микросекундах), название в ms → делим на 1000
"""

METRIC_CONVERSION = {
    # ========================================================================
    # BANDWIDTH: KB/s → MB/s (divide by 1024)
    # ========================================================================
    "311": 1024,  # Throughput (MB/s) - реально в KB/s
    "312": 1024,  # Read throughput (MB/s) - реально в KB/s
    "313": 1024,  # Write throughput (MB/s) - реально в KB/s
    "511": 1024,  # File bandwidth(MB/s) - реально в KB/s
    "512": 1024,  # Throughput (MB/s) - реально в KB/s
    "1164": 1/1024, #"Avg. Full Copy Read Request Size (KB)"
    "1168": 1/1024, #"Avg. Full Copy Write Request Size (KB)"
    #"1172": 1/1024, #"Avg. ODX Read Request Size (KB)" - под вопросом
    #"1176": 1/1024, #"Avg. ODX Write Request Size (KB)" - под вопросом
    #"1180": 1/1024, #"Avg. ODX Write Zero Request Size (KB)" - под вопросом
    "1156": 1/1024, #"Avg. Unmap Command Size (KB)" 
    "1160": 1/1024, #"Avg. WRITE SAME Command Size (KB)" 
    "1245": 1/1024, #"Avg. Full Copy Command Size (KB)"
    "1090": 1000, #"Data Reduction Ratio"
    
    


    # ========================================================================
    # LATENCY / RESPONSE TIME: us → ms (divide by 1000)
    # ========================================================================
    
    # I/O Response Time (основные метрики)
    #"369": 1000,   # Service Time(us)
    #"370": 1000,   # Avg. I/O Response Time (us)
    #"371": 1000,   # Max. I/O Response Time (us)
    #"384": 1000,   # Avg. Read I/O Response Time(us)
    #"385": 1000,   # Avg. Write I/O Response Time(us)
    "1315": 1000,   #"Maximum Configuration Request Duration (ms)",#NEW
    "1316": 1000,   #"Maximum Configuration Request Queue Duration (ms)",#NEW
    
    # Operations Latency (NFS/CIFS)
    "429": 1000,   # Max Latency For Operations (ms) - реально в us
    "472": 1000,   # Min Latency For Operations (ms) - реально в us
    "508": 1000,   # Average Latency For Operations (ms) - реально в us
    "509": 1000,   # Max Latency For Operations (ms) - реально в us
    "510": 1000,   # Min Latency For Operations (ms) - реально в us
    
    # Service time
    "523": 1000,   # Service time (ms) - реально в us
    "524": 1000,   # Average Read OPS Response Time (ms) - реально в us
    "525": 1000,   # Average Write OPS Response Time (ms) - реально в us
    
    # NFS/CIFS I/O Response Time
    "745": 1000,   # Avg. Response Time of NFS I/Os(us)
    "748": 1000,   # Avg. Response Time of CIFS I/Os(us)
    "751": 1000,   # Avg. Response Time of NFS Read I/Os(us)
    "754": 1000,   # Avg. Response Time of CIFS Read I/Os(us)
    "757": 1000,   # Avg. Response Time of NFS Write I/Os(us)
    "760": 1000,   # Avg. Response Time of CIFS Write I/Os(us)
    "763": 1000,   # Avg. Response Time of Other NFS I/Os(us)
    "766": 1000,   # Avg. Response Time of Other CIFS I/Os(us)
    
    # Back-End Response Time
    #"807": 1000,   # Avg. Back-End Response Time (us)
    
    # Link Transmission Latency
    #"1139": 1000,  # Avg. Read I/O Link Transmission Latency(us)
    #"1140": 1000,  # Avg. Write I/O Link Transmission Latency(us)
    
    # Command Response Time
    #"1157": 1000,  # Avg. Unmap Command Response Time (us)
    #"1161": 1000,  # Avg. WRITE SAME Command Response Time (us)
    #"1165": 1000,  # Avg. Full Copy Read Request Response Time (us)
    #"1169": 1000,  # Avg. Full Copy Write Request Response Time (us)
    #"1173": 1000,  # Avg. ODX Read Request Response Time (us)
    #"1177": 1000,  # Avg. ODX Write Request Response Time (us)
    #"1181": 1000,  # Avg. ODX Write Zero Request Response Time (us)
    #"1191": 1000,  # Avg. VAAI Response Time (us)
    #"1195": 1000,  # Avg. DR Read Request Response Time (us)
    #"1199": 1000,  # Avg. DR Write Request Response Time (us)
    #"1211": 1000,  # Normalized Latency (us)
    #"1246": 1000,  # Avg. Full Copy Command Response Time (us)
    #"1250": 1000,  # Avg. ODX Command Response Time (us)
    
    # DataTurbo I/O Response Time
    #"1264": 1000,  # Average response time of other DataTurbo I/Os(us)
    #"1271": 1000,  # Average DataTurbo I/O response time(us)
    #"1272": 1000,  # Average DataTurbo read I/O response time(us)
    #"1273": 1000,  # Average DataTurbo write I/O response time(us)
    
    # DR Response Time
    #"1319": 1000,  # Avg. DR Request Response Time (us)
    
    # NFS OPS Response Time
    "30013": 1000, # NFS write OPS average response time (us)
    "30015": 1000, # NFS read OPS average response time (us)
}

# Статистика
BANDWIDTH_CONVERSIONS = len([k for k, v in METRIC_CONVERSION.items() if v == 1024])
LATENCY_CONVERSIONS = len([k for k, v in METRIC_CONVERSION.items() if v == 1000])
TOTAL_CONVERSIONS = len(METRIC_CONVERSION)

if __name__ == "__main__":
    print("=" * 80)
    print("METRIC_CONVERSION DICTIONARY")
    print("=" * 80)
    print(f"\nВсего метрик с конверсией: {TOTAL_CONVERSIONS}")
    print(f"  - Bandwidth (KB/s → MB/s, ÷1024): {BANDWIDTH_CONVERSIONS}")
    print(f"  - Latency (us → ms, ÷1000): {LATENCY_CONVERSIONS}")
    print("\n" + "=" * 80)
    print("BANDWIDTH CONVERSIONS (KB/s → MB/s)")
    print("=" * 80)
    for metric_id, factor in sorted(METRIC_CONVERSION.items()):
        if factor == 1024:
            from METRIC_DICT import METRIC_NAME_DICT
            name = METRIC_NAME_DICT.get(metric_id, f"UNKNOWN_{metric_id}")
            print(f"  {metric_id:6s}: {name}")
    
    print("\n" + "=" * 80)
    print("LATENCY CONVERSIONS (us → ms)")
    print("=" * 80)
    for metric_id, factor in sorted(METRIC_CONVERSION.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 999999):
        if factor == 1000:
            from METRIC_DICT import METRIC_NAME_DICT
            name = METRIC_NAME_DICT.get(metric_id, f"UNKNOWN_{metric_id}")
            print(f"  {metric_id:6s}: {name}")



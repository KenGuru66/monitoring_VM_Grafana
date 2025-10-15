# -*- coding:utf-8 -*-
#!/usr/bin/python
import getopt
import re
import os
import shutil
import struct
from datetime import datetime
from datetime import timedelta
import time
import tarfile
import sys

input_path = None
output_path = None
log_path = None
resources = None
metrics = None
is_delete_after_parse = None
# default parse such objects:
# LUN(11)
# Controller(207)
# Host(21)
# FrontPort:FC Port(212),bond port(235),Ethernet Port(213),LIF(279),IB_Port(16500)
defualt_resources = ["11","207","21","212","235","213","279","16500"]
# default parse such data types:
# Band:Read bandwidth(23),Write bandwidth(26),Block Bandwidth(21)
# IOPS:Read IOPS(25),Write IOPS(28),Total IOPS(22)
# response time:Avg. read I/O response timems:197),Avg. write I/O response time(ms:198),Avg. I/O response time(ms:78)
# Usage(18)
default_metrics = ["23","26","21","25","28","22","197","198","78","18"]

i="InputFilePath"
o="OutputFilePath"
l="LogPath"
d="AutoDelete"
r="Resources"
m="Metrics"
metric_name_dict = {"396": "Read I/O Latency Distribution: [5ms,10ms) (%)", "333": "Cache water (%)",
                    "693": "NFS Write I/O count: [256K,+∞)", "692": "NFS Write I/O count: [128K,256K)",
                    "691": "NFS Write I/O count: [64K,128K)", "690": "NFS Write I/O count: [32K,64K)",
                    "689": "NFS Write I/O count: [16K,32K)", "688": "NFS Write I/O count: [8K,16K)",
                    "687": "NFS Write I/O count: [4K,8K)", "686": "NFS Write I/O count: [2K,4K)",
                    "685": "NFS Write I/O count: [1K,2K)", "684": "NFS Write I/O count: [512B,1K)",
                    "683": "NFS Write I/O count: [0K,512B)", "682": "NFS Read I/O count: [256K,+∞)",
                    "681": "NFS Read I/O count: [128K,256K)", "680": "NFS Read I/O count: [64K,128K)",
                    "679": "NFS Read I/O count: [32K,64K)", "678": "NFS Read I/O count: [16K,32K)",
                    "677": "NFS Read I/O count: [8K,16K)", "676": "NFS Read I/O count: [4K,8K)",
                    "313": "Write throughput (MB/s)", "675": "NFS Read I/O count: [2K,4K)",
                    "312": "Read throughput (MB/s)", "674": "NFS Read I/O count: [1K,2K)", "311": "Throughput (MB/s)",
                    "673": "NFS Read I/O count: [512B,1K)", "310": "Faulty I/O ratio (%)",
                    "672": "NFS Read I/O count: [0K,512B)", "671": "NFS V4 Write I/O count: [256K,+∞)",
                    "670": "NFS V4 Write I/O count: [128K,256K)", "309": "Number of failed I/Os per second",
                    "308": "Total number of failed I/Os", "307": "Max. IOPS (IO/s)",
                    "669": "NFS V4 Write I/O count: [64K,128K)", "306": "Random write ratio (%)",
                    "668": "NFS V4 Write I/O count: [32K,64K)", "305": "Random read ratio (%)",
                    "667": "NFS V4 Write I/O count: [16K,32K)", "304": "Miss ratio (%)",
                    "666": "NFS V4 Write I/O count: [8K,16K)", "303": "Hit ratio (%)",
                    "665": "NFS V4 Write I/O count: [4K,8K)", "302": "Number of randomly hit requests per second",
                    "664": "NFS V4 Write I/O count: [2K,4K)", "301": "Max. number of dirty data pages",
                    "663": "NFS V4 Write I/O count: [1K,2K)", "300": "Port average requests size",
                    "662": "NFS V4 Write I/O count: [512B,1K)", "661": "NFS V4 Write I/O count: [0K,512B)",
                    "660": "NFS V4 Read I/O count: [256K,+∞)", "659": "NFS V4 Read I/O count: [128K,256K)",
                    "658": "NFS V4 Read I/O count: [64K,128K)", "657": "NFS V4 Read I/O count: [32K,64K)",
                    "656": "NFS V4 Read I/O count: [16K,32K)", "655": "NFS V4 Read I/O count: [8K,16K)",
                    "654": "NFS V4 Read I/O count: [4K,8K)", "653": "NFS V4 Read I/O count: [2K,4K)",
                    "652": "NFS V4 Read I/O count: [1K,2K)", "651": "NFS V4 Read I/O count: [512B,1K)",
                    "650": "NFS V4 Read I/O count: [0K,512B)", "649": "NFS V3 Write I/O count: [256K,+∞)",
                    "648": "NFS V3 Write I/O count: [128K,256K)", "647": "NFS V3 Write I/O count: [64K,128K)",
                    "646": "NFS V3 Write I/O count: [32K,64K)", "645": "NFS V3 Write I/O count: [16K,32K)",
                    "644": "NFS V3 Write I/O count: [8K,16K)", "643": "NFS V3 Write I/O count: [4K,8K)",
                    "642": "NFS V3 Write I/O count: [2K,4K)", "641": "NFS V3 Write I/O count: [1K,2K)",
                    "640": "NFS V3 Write I/O count: [512B,1K)", "639": "NFS V3 Write I/O count: [0K,512B)",
                    "638": "NFS V3 Read I/O count: [256K,+∞)", "637": "NFS V3 Read I/O count: [128K,256K)",
                    "636": "NFS V3 Read I/O count: [64K,128K)", "635": "NFS V3 Read I/O count: [32K,64K)",
                    "634": "NFS V3 Read I/O count: [16K,32K)", "633": "NFS V3 Read I/O count: [8K,16K)",
                    "632": "NFS V3 Read I/O count: [4K,8K)", "631": "NFS V3 Read I/O count: [2K,4K)",
                    "630": "NFS V3 Read I/O count: [1K,2K)", "629": "NFS V3 Read I/O count: [512B,1K)",
                    "628": "NFS V3 Read I/O count: [0K,512B)", "627": "NFS operation count per second",
                    "626": "NFS V4 operations average latency excluding read and write",
                    "625": "NFS V3 procedures average latency excluding read and write",
                    "624": "NFS V4 RELEASE_LOCKOWNER operation count", "623": "NFS V4 WRITE operation count",
                    "622": "NFS V4 VERIFY operation count", "621": "NFS V4 SETCLIENTID_CONFIRM operation count",
                    "620": "NFS V4 SETCLIENTID operation count", "619": "NFS V4 SETATTR operation count",
                    "618": "NFS V4 SECINFO operation count", "617": "NFS V4 SAVEFH operation count",
                    "616": "NFS V4 RESTOREFH operation count", "615": "NFS V4 RENEW operation count",
                    "614": "NFS V4 RENAME operation count", "613": "NFS V4 REMOVE operation count",
                    "612": "NFS V4 READLINK operation count", "611": "NFS V4 READDIR operation count",
                    "610": "NFS V4 READ operation count", "609": "NFS V4 PUTROOTFH operation count",
                    "608": "NFS V4 PUTPUBFH operation count", "607": "NFS V4 PUTFH operation count",
                    "606": "NFS V4 OPEN_DOWNGRADE operation count", "605": "NFS V4 OPEN_CONFIRM operation count",
                    "604": "NFS V4 OPENATTR operation count", "603": "NFS V4 OPEN operation count",
                    "602": "NFS V4 NVERIFY operation count", "601": "NFS V4 LOOKUPP operation count",
                    "600": "NFS V4 LOOKUP operation count", "1094": "Thin LUN Space Saving Rate (%)",
                    "1093": "Overall Space Saving Ratio", "1092": "Compression Ratio", "1091": "Deduplication Ratio",
                    "1090": "Data Reduction Ratio", "1079": "SCSI IOPS(IO/s)", "1078": "Write Disk IOPS(IO/s)",
                    "1077": "Read Disk IOPS(IO/s)", "1076": "Total Disk IOPS(IO/s)", "1075": "Disk Max. Usage(%)",
                    "1074": "CIFS operation count per second", "1073": "ISCSI IOPS(IO/s)",
                    "1072": "Swift Post Failed Number(client's cause)", "1071": "Swift Post Failed Number",
                    "1070": "Swift Post Number", "1069": "Swift Head Failed Number(client's cause)",
                    "1068": "Swift Head Failed Number", "1067": "Swift Head Number",
                    "1066": "S3 Post Failed Number(client's cause)", "1065": "S3 Post Failed Number",
                    "1064": "S3 Post Number", "1063": "S3 Head Failed Number(client's cause)",
                    "1062": "S3 Head Failed Number", "1061": "S3 Head Number", "1060": "The cache chunk preservation",
                    "1059": "The cache page preservation", "1057": "Cache pageUnit utilization (%)",
                    "1056": "Cache chunk utilization (%)", "1055": "Cache page utilization (%)",
                    "1054": "Synchronization Duration (s)", "299": "Back-end write traffic (MB/s)",
                    "298": "Back-end read traffic (MB/s)", "297": "Read/write IOPS on ports",
                    "296": "Read/write traffic on ports (MB/s)", "295": "Read/write traffic (MB/s)",
                    "294": "Data transfer write  requests per second", "293": "Data transfer read  requests per second",
                    "292": "Data transfer requests per second", "291": "I/Os per second",
                    "290": "Read request hit ratio (%)", "289": "Hit ratio of read/write requests (%)",
                    "288": "Ratio of write requests to total requests (%)",
                    "287": "Ratio of read requests to total requests (%)",
                    "286": "Number of lost write requests on all the front-end host ports per second",
                    "285": "Number of lost read requests on all the front-end host ports per second",
                    "284": "Number of lost requests per second",
                    "283": "Number of hit write requests sent by front-end host ports per second",
                    "282": "Number of hit read requests sent by front-end host ports per second",
                    "281": "Number of data transfer write requests from front-end host ports to cache per second",
                    "280": "Number of data transfer read requests from front-end host ports to cache per second",
                    "279": "Number of data transfer requests from front-end host ports to cache per second",
                    "278": "Ratio of back-end write requests (%)", "277": "Ratio of back-end read requests (%)",
                    "276": "Avg. back-end response time (ms)", "275": "Back-end write response time (ms)",
                    "274": "Back-end read response time (ms)", "273": "Back-end read request queuing time (ms)",
                    "272": "Back-end write request time (ms)", "271": "Back-end read request time (ms)",
                    "270": "Ratio of lost write requests (%)", "269": "Ratio of lost read requests (%)",
                    "268": "Ratio of write I/Os to total write I/Os (%)",
                    "267": "Ratio of read I/Os to total read I/Os (%)", "266": "Ratio of write I/Os to total I/Os (%)",
                    "265": "Ratio of read I/Os to total I/Os (%)", "264": "Write miss response time (ms)",
                    "263": "Read miss response time (ms)", "262": "Back-end write traffic (MB/s)",
                    "261": "Back-end read traffic (MB/s)", "260": "Back-End traffic (MB/s)",
                    "259": "Back-end write requests per second", "258": "Back-end read requests per second",
                    "257": "Back-end read/write requests per second",
                    "256": "Number of sent-by-host write I/Os that cannot be immediately found in the cache per second",
                    "255": "Number of sent-by-host read I/Os that cannot be immediately found in the cache per second",
                    "254": "Number of sent-by-host read/write I/Os that cannot be immediately found in the cache per second",
                    "253": "Number of sent-by-host write I/Os that can be immediately found in the cache per second",
                    "252": "Number of sent-by-host read I/Os that can be immediately found in the cache per second",
                    "251": "Number of sent-by-host read/write I/Os that can be immediately found in the cache per second",
                    "250": "Used cache ratio (%)", "249": "Ratio of dirty data pages to total pages (%)",
                    "248": "Threshold for dirty data page quantity (%)", "247": "Number of dirty data pages",
                    "242": "Verify commands per second", "241": "SCSI commands executed per second",
                    "240": "Average queue depth", "599": "NFS V4 LOCKU operation count", "236": "Bandwidth (KB/s)",
                    "598": "NFS V4 LOCKT operation count", "597": "NFS V4 LOCK operation count",
                    "596": "NFS V4 LINK operation count", "233": "Write OPS (per second)",
                    "595": "NFS V4 GETFH operation count", "232": "Read OPS (per second)",
                    "594": "NFS V4 GETATTR operation count", "231": "Network packet output stream speed (per second)",
                    "593": "NFS V4 DELEGRETURN operation count",
                    "230": "Network packet input stream speed (per second)", "592": "NFS V4 DELEGPURGE operation count",
                    "591": "NFS V4 CREATE operation count", "590": "NFS V4 COMMIT operation count",
                    "229": "Network packet stream speed (per second)", "228": "Avg. I/O size (KB)",
                    "227": "Number of connected CIFS clients", "589": "NFS V4 CLOSE operation count",
                    "226": "Number of connected NFS clients", "588": "NFS V4 ACCESS operation count",
                    "225": "Number of connected clients", "587": "NFS V4 COMPOUND procedure count",
                    "224": "CIFS read bandwidth (KB/s)", "586": "NFS V4 NULL procedure count",
                    "223": "CIFS write bandwidth (KB/s)", "585": "NFS V3 extendcmd procedure count",
                    "222": "CIFS bandwidth (KB/s)", "584": "NFS V3 COMMIT procedure count",
                    "221": "NFS read bandwidth (KB/s)", "583": "NFS V3 PATHCONF procedure count",
                    "220": "NFS write bandwidth (KB/s)", "582": "NFS V3 FSINFO procedure count",
                    "581": "NFS V3 FSSTAT procedure count", "580": "NFS V3 READDIRPLUS procedure count",
                    "219": "NFS bandwidth (KB/s)", "218": "Max. memory usage (%)", "217": "Max. CPU usage (%)",
                    "579": "NFS V3 READDIR procedure count", "578": "NFS V3 LINK procedure count",
                    "577": "NFS V3 RENAME procedure count", "576": "NFS V3 RMDIR procedure count",
                    "575": "NFS V3 REMOVE procedure count", "574": "NFS V3 MKNOD procedure count",
                    "211": "磁盘IOPS(IO/s)", "573": "NFS V3 SYMLINK procedure count",
                    "210": "Write I/O Latency Distribution: [200ms,+∞) (%)", "572": "NFS V3 MKDIR procedure count",
                    "571": "NFS V3 CREATE procedure count", "570": "NFS V3 WRITE procedure count",
                    "209": "Write I/O Latency Distribution: [100ms,200ms) (%)",
                    "208": "Write I/O Latency Distribution: [50ms,100ms) (%)",
                    "207": "Write I/O Latency Distribution: [20ms,50ms) (%)", "569": "NFS V3 READ procedure count",
                    "206": "Write I/O Latency Distribution: [10ms,20ms) (%)", "568": "NFS V3 READLINK procedure count",
                    "205": "Write I/O Latency Distribution: [0ms,10ms) (%)", "567": "NFS V3 ACCESS procedure count",
                    "204": "Read I/O Latency Distribution: [200ms,+∞) (%)", "566": "NFS V3 LOOKUP procedure count",
                    "203": "Read I/O Latency Distribution: [100ms,200ms) (%)", "565": "NFS V3 SETATTR procedure count",
                    "202": "Read I/O Latency Distribution: [50ms,100ms) (%)", "564": "NFS V3 GETATTR procedure count",
                    "201": "Read I/O Latency Distribution: [20ms,50ms) (%)", "563": "NFS V3 NULL procedure count",
                    "562": "Swift Connect Failed Rate(%)", "200": "Read I/O Latency Distribution: [10ms,20ms) (%)",
                    "561": "Swift Put Failed Number(client's cause)", "560": "Swift Put Failed Number",
                    "559": "Swift Put Number", "558": "Swift Get Failed Number(client's cause)",
                    "557": "Swift Get Failed Number", "556": "Swift Get Number",
                    "555": "Swift Delete Failed Number(client's cause)", "554": "Swift Delete Failed Number",
                    "553": "Swift Delete Number", "552": "Swift Write Bandwidth (KB/s)",
                    "551": "Swift Read Bandwidth (KB/s)", "550": "Swift Bandwidth (KB/s)",
                    "549": "S3 Connect Failed Rate(%)", "548": "S3 Put Failed Number(client's cause)",
                    "547": "S3 Put Failed Number", "546": "S3 Put Number",
                    "545": "S3 Get Failed Number(client's cause)", "544": "S3 Get Failed Number",
                    "543": "S3 Get Number", "542": "S3 Delete Failed Number(client's cause)",
                    "541": "S3 Delete Failed Number", "540": "S3 Delete Number", "539": "S3 Write Bandwidth (KB/s)",
                    "538": "S3 Read Bandwidth (KB/s)", "537": "S3 Bandwidth (KB/s)",
                    "536": "File System Write Bandwidth (KB/s)", "535": "File System Read Bandwidth (KB/s)",
                    "534": "File System Bandwidth (KB/s)", "533": "Number of failed write I/Os",
                    "532": "Number of failed read I/Os", "531": "Write I/O Latency Distribution: [0ms,5ms) (%)",
                    "530": "Read I/O Latency Distribution: [0ms,5ms) (%)",
                    "525": "Average Write OPS Response Time (ms)", "524": "Average Read OPS Response Time (ms)",
                    "523": "Service time (ms)", "522": "Amount of data migrated from SSDs to NL-SAS disks",
                    "521": "Amount of data migrated from SSDs to NL-SAS disks",
                    "520": "Amount of data migrated from NL-SAS disks to SAS disks",
                    "519": "Amount of data migrated from SSDs to SAS disks",
                    "518": "Amount of data migrated from NL-SAS disks to SSDs",
                    "517": "Amount of data migrated from SAS disks to SSDs",
                    "516": "Amount of data migrated to NL-SAS disks", "515": "Amount of data migrated to SAS disks",
                    "514": "Amount of data migrated to SSDs", "513": "Total amount of migrated data",
                    "512": "Throughput (MB/s)", "511": "File bandwidth(MB/s)", "510": "Min Latency For Operations (ms)",
                    "509": "Max Latency For Operations (ms)", "9": "平均延迟", "508": "Average Latency For Operations (ms)",
                    "8": "最大延迟", "6": "当前IOPS", "5": "Max. bandwidth (MB/s)", "4": "当前带宽(MB/s)", "3": "写I/O比率(%)",
                    "2": "读I/O比率(%)", "808": "Average usage of member disks(%)",
                    "99": "Time since last synchronization (s)", "98": "Write cache misses per second",
                    "97": "Write cache hits per second", "96": "Write cache rehit ratio (%)",
                    "95": "Write cache hit ratio (%)", "94": "Read cache rehit ratio (%)",
                    "93": "Read cache hit ratio (%)", "92": "Read cache hits by reads per second",
                    "91": "Write cache hits by reads per second", "90": "Read cache misses per second",
                    "89": "Read cache hits per second", "88": "Prefetch rate (%)", "87": "Prefetch traffic (MB/s)",
                    "86": "Full-stripe write request ratio (%)", "85": "Low watermark reaching times",
                    "84": "Cache flushes caused by the timer", "83": "Cache flushes caused by high watermark",
                    "82": "Cache flushing bandwidth (MB/s)", "81": "Cache flushes to write requests ratio (%)",
                    "80": "Dirty page ratio (%)", "79": "Max. I/O response time (ms)",
                    "78": "Avg. I/O response time (ms)", "77": "电压", "76": "功耗", "75": "工作温度", "74": "网络当前出包数量",
                    "73": "网络当前进包数量", "72": "写吞吐量(MB/s)", "71": "读吞吐量(MB/s)", "70": "交换分区占用率(%)",
                    "69": "Avg. cache usage (%)", "68": "Avg. CPU usage (%)", "67": "Usage (%)", "66": "使用率(%)",
                    "65": "随机顺序比例", "64": "周期内读I/O总数", "63": "周期内写I/O总数", "62": "读写I/O分布：512KB", "61": "周期内读I/O总数",
                    "60": "周期内写I/O总数", "59": "读写I/O分布：64KB", "58": "读写I/O分布：32KB", "57": "读写I/O分布：16KB",
                    "56": "读写I/O分布：8KB", "55": "读写I/O分布：4KB", "54": "读写I/O分布：2KB", "53": "读写I/O分布：1KB",
                    "52": "读写I/O分布：512B", "51": "Write I/O granularity distribution: [512K,+∞) (%)",
                    "50": "Write I/O granularity distribution: [256K,512K) (%)",
                    "199": "Read I/O Latency Distribution: [0ms,10ms) (%)", "198": "Avg. write I/O response time (ms)",
                    "197": "Avg. read I/O response time (ms)", "196": "Max. write I/O response time (ms)",
                    "195": "Max. read I/O response time (ms)", "194": "远程复制带宽(KB/s)", "193": "包吞吐率(%)",
                    "192": "Access frequency (%)", "191": "包溢出率(%)", "190": "错误包率(%)",
                    "49": "Write I/O granularity distribution: [128K,256K) (%)",
                    "48": "Write I/O granularity distribution: [64K,128K) (%)",
                    "47": "Write I/O granularity distribution: [32K,64K) (%)",
                    "46": "Write I/O granularity distribution: [16K,32K) (%)",
                    "45": "Write I/O granularity distribution: [8K,16K) (%)",
                    "44": "Write I/O granularity distribution: [4K,8K) (%)",
                    "43": "Write I/O granularity distribution: [2K,4K) (%)",
                    "42": "Write I/O granularity distribution: [1K,2K) (%)",
                    "41": "Write I/O granularity distribution: [0K,1K) (%)",
                    "40": "Read I/O granularity distribution: [512K,+∞) (%)", "90021": "Used File Quantity Quota",
                    "90020": "File Quantity Soft Quota", "189": "丢包率(%)", "188": "包传输速率(Packets/s)", "187": "重删率(%)",
                    "186": "总容量", "185": "已用容量", "184": "硬配额空间容量", "183": "在线用户数", "182": "OPS (per second)",
                    "181": "读写I/O粒度分布：> 2M(%)", "180": "读写I/O粒度分布：<= 2M(%)",
                    "39": "Read I/O granularity distribution: [256K,512K) (%)",
                    "38": "Read I/O granularity distribution: [128K,256K) (%)",
                    "37": "Read I/O granularity distribution: [64K,128K) (%)",
                    "36": "Read I/O granularity distribution: [32K,64K) (%)",
                    "35": "Read I/O granularity distribution: [16K,32K) (%)",
                    "34": "Read I/O granularity distribution: [8K,16K) (%)", "90019": "File Quantity Hard Quota",
                    "33": "Read I/O granularity distribution: [4K,8K) (%)", "90018": "Used Space Quota(MB)",
                    "32": "Read I/O granularity distribution: [2K,4K) (%)", "90017": "Space Soft Quota(MB)",
                    "31": "Read I/O granularity distribution: [1K,2K) (%)", "90016": "Space Hard Quota(MB)",
                    "30": "Read I/O granularity distribution: [0K,1K) (%)", "179": "读写I/O粒度分布：<= 1M(%)",
                    "178": "读写I/O粒度分布：<= 512K(%)", "177": "读写I/O粒度分布：<= 256K(%)", "176": "读写I/O粒度分布：<= 128K(%)",
                    "175": "读写I/O粒度分布：<= 64K(%)", "174": "读写I/O粒度分布：<= 32K(%)", "173": "读写I/O粒度分布：<= 16K(%)",
                    "172": "读写I/O粒度分布：<= 8K(%)", "171": "读写I/O粒度分布：< 4K(%)", "170": "写I/O粒度分布：> 2M(%)",
                    "29": "Service time (ms)", "28": "Write IOPS (IO/s)", "27": "Avg. write I/O size (KB)",
                    "26": "Write bandwidth (MB/s)", "25": "Read IOPS (IO/s)", "24": "Avg. read I/O size (KB)",
                    "23": "Read bandwidth (MB/s)", "22": "Total IOPS (IO/s)", "21": "Block bandwidth (MB/s)",
                    "20": "响应时间(ms)", "90006": "Free capacity ratio (%)", "90005": "Allocated capacity (MB)",
                    "90004": "Capacity usage (%)", "90003": "Free capacity (MB)", "90002": "Used capacity (MB)",
                    "90001": "Total capacity (MB)", "169": "写I/O粒度分布：<= 2M(%)", "168": "写I/O粒度分布：<= 1M(%)",
                    "167": "写I/O粒度分布：<= 512K(%)", "166": "写I/O粒度分布：<= 256K(%)", "165": "写I/O粒度分布：<= 128K(%)",
                    "164": "写I/O粒度分布：<= 64K(%)", "163": "写I/O粒度分布：<= 32K(%)", "162": "写I/O粒度分布：<= 16K(%)",
                    "161": "写I/O粒度分布：<= 8K(%)", "160": "写I/O粒度分布：< 4K(%)", "19": "Queue length", "18": "Usage (%)",
                    "17": "最小功耗", "16": "平均功耗", "15": "最大功耗", "14": "写I/O流量", "13": "读I/O流量",
                    "12": "Mirror write cache usage (%)", "11": "本地写Cache利用率(%)", "10": "Cache hit ratio (%)",
                    "159": "读I/O粒度分布：> 2M(%)", "158": "读I/O粒度分布：≤ 2M(%)", "157": "读I/O粒度分布：≤ 1M(%)",
                    "156": "读I/O粒度分布：≤ 512K(%)", "155": "读I/O粒度分布：≤ 256K(%)", "154": "读I/O粒度分布：≤ 128K(%)",
                    "153": "读I/O粒度分布：≤ 64K(%)", "152": "读I/O粒度分布：≤ 32K(%)", "151": "读I/O粒度分布：≤ 16K(%)",
                    "150": "读I/O粒度分布：≤ 8K(%)", "149": "读I/O粒度分布：< 4K(%)", "148": "I/O平均大小(B控)(sector)",
                    "147": "写等待时间(B控)(ms)", "146": "读等待时间(B控)(ms)", "145": "每秒合并写I/O的个数(个/秒)",
                    "144": "每秒合并读I/O的个数(B控)(个/秒)", "143": "服务时间(B控)(ms)", "142": "队列长度(B控)(个)", "141": "利用率(B控)(%)",
                    "140": "平均I/O响应时间(B控)(ms)", "139": "最大I/O响应时间(B控)(ms)", "138": "写I/O平均大小(B控)(KB)",
                    "137": "读I/O平均大小(B控)(KB)", "136": "I/O平均大小(A控)(sector)", "135": "写等待时间(A控)(ms)",
                    "134": "读等待时间(A控)(ms)", "133": "每秒合并写I/O的个数(A控)(个/秒)", "132": "每秒合并读I/O的个数(A控)(个/秒)",
                    "131": "服务时间(A控)(ms)", "130": "队列长度(A控)(个)", "129": "利用率(A控)(%)", "128": "平均I/O响应时间(A控)(ms)",
                    "127": "最大I/O响应时间(A控)(ms)", "126": "写I/O平均大小(A控)(KB)", "125": "读I/O平均大小(A控)(KB)",
                    "124": "Write bandwidth (KB/s)", "123": "Read bandwidth (KB/s)", "122": "Cache写盘页面数(个)",
                    "121": "Cache写盘I/O数(个)", "120": "Cache write usage (%)", "119": "写请求申请内存的耗时(ms)",
                    "118": "Cache镜像I/O响应时间(ms)", "117": "Cache写I/O响应时间(ms)", "116": "Cache读I/O响应时间(ms)",
                    "115": "释放读请求资源的耗时(ms)", "476": "File OPS(per second)", "114": "执行读请求的耗时(ms)",
                    "475": "File bandwidth(B/s)", "113": "释放写请求资源的耗时(ms)", "112": "设备保存写数据的耗时(ms)",
                    "473": "Logical Bandwidth (MB/s)", "111": "主机下发数据的耗时(ms)", "472": "Min Latency For Operations (ms)",
                    "110": "Cache read usage (%)", "471": "Write I/O Granularity Distribution: [256K,+∞) (%)",
                    "470": "Write I/O Granularity Distribution: [512B,1K) (%)", "109": "镜像Cache利用率(%)",
                    "108": "本地Cache利用率(%)", "469": "Write I/O Granularity Distribution: [0,512B) (%)",
                    "107": "Chunks used by the snapshot copy",
                    "468": "Read I/O Granularity Distribution: [256K,+∞) (%)",
                    "106": "Write requests to the source LUN exceeding the grain size",
                    "467": "Read I/O Granularity Distribution: [512B,1K) (%)",
                    "105": "Write requests to the snapshot LUN", "104": "COW requests from the snapshot LUN",
                    "466": "Read I/O Granularity Distribution: [0,512B) (%)", "103": "COW requests to the source LUN",
                    "465": "Average Write OPS Response Time (ms)", "102": "Read requests redirected to the source LUN",
                    "464": "Average Read OPS Response Time (ms)", "101": "Read requests to the snapshot LUN",
                    "463": "Space Size (MB)", "100": "Unsynchronized data amount (MB)", "462": "Space Usage (%)",
                    "439": "Throughput (Bps)",
                    "437": "Count Of Protocol Read Operation Large Latency Continuous Occurred",
                    "436": "Count Of Protocol Read Operation Large Latency Continuous Occurred For NFS",
                    "435": "Count Of Protocol Read Operation Large Latency Continuous Occurred For CIFS",
                    "433": "Max Latency For Read Operation (ms)", "432": "Average Latency For Read Operation (ms)",
                    "431": "Max Latency For Write Operation (ms)", "430": "Average Latency For Write Operation (ms)",
                    "429": "Max Latency For Operations (ms)", "428": "Average Latency For Operations (ms)",
                    "421": "Protocol Read Operation Max Latency For CIFS (ms)",
                    "420": "Protocol Read Operation Average Latency For CIFS (ms)",
                    "419": "Protocol Write Operation Max Latency For CIFS (ms)",
                    "418": "Protocol Write Operation Average Latency For CIFS (ms)",
                    "417": "Protocol Operations Max Latency For CIFS (ms)",
                    "416": "Protocol Operations Average Latency For CIFS (ms)",
                    "415": "Protocol Read Operation Max Latency For NFS (ms)",
                    "414": "Protocol Read Operation Average Latency For NFS (ms)",
                    "413": "Protocol Write Operation Max Latency For NFS (ms)",
                    "412": "Protocol Write Operation Average Latency For NFS (ms)",
                    "411": "Protocol Operations Max Latency For NFS (ms)",
                    "410": "Protocol Operations Average Latency For NFS (ms)",
                    "402": "Write I/O Latency Distribution: [5ms,10ms) (%)",
                    "60003": "Read/write requests to the snapshot pool",
                    "60002": "Read/write requests to the source LUN", }
resource_name_dict = {"16500": "IB Port", "304": "Heterogeneous iSCSI Link", "303": "Heterogeneous FC Link",
                      "57636": "Controller NFSV4.1", "16458": "Quota Tree", "279": "Logical Port", "16500": "IB Port",
                      "273": "SmartCache Partition", "272": "LUN Priority", "268": "SmartPartition",
                      "266": "Disk Domain", "263": "Remote Replication", "256": "Lun Group", "252": "FCoE Port",
                      "243": "iSCSI Replication Link", "237": "Cache", "235": "Bond Port", "230": "SmartQoS",
                      "16402": "CIFS Share", "16401": "NFS Share", "16400": "Directory", "225": "FC Replication Link",
                      "223": "FC Initiator", "221": "Remote Replication Consistent Group", "219": "LUN Copy",
                      "216": "Storage Pool", "214": "Back-End Port", "213": "Ethernet Port", "212": "FC Port",
                      "207": "Controller", "201": "Array", "252": "FCoE Port", "235": "Bond Port", "16390": "Client",
                      "16385": "Node", "16384": "Cluster", "213": "Ethernet Port", "212": "FC Port",
                      "40": "File System", "1003": "Controller SMB2/3", "1002": "Controller SMB1",
                      "1001": "Controller NFSV4", "1000": "Controller NFSV3", "27": "Snapshot LUN", "21": "Host",
                      "14": "Host Group", "11": "LUN", "57791": "RAID", "404": "Remote eISCSI Link", "10": "Disk", }

trueFlags=["YES","yes","Y","y","TRUE","True","true"]
falseFlags=["NO","no","N","n","FALSE","False","false"]

def process_perf_file(file_path, output_csv_file_path):
    log_repeat_info("Info: Start to procoss file->%s" % file_path)

    fp = open(file_path, 'rb')
    bit_correct = fp.read(32)
    bit_msg_version = fp.read(4)
    bit_equip_sn = fp.read(256)
    bit_equip_name = fp.read(41)
    bit_equip_data_length = fp.read(4)


    #log_repeat_info(str(bit_correct).strip())
    #log_repeat_info(str(bit_msg_version).strip())
    log_repeat_info(bit_equip_sn.replace('\x00', ''))
    log_repeat_info(bit_equip_name.replace('\x00', ''))
    #log_repeat_info(str(bit_equip_data_length).strip())


    #log_repeat_info(str(bit_map_t).strip())
    #log_repeat_info(str(bit_map_length).strip())

    process_finish_flag = False

    bit_map_type = fp.read(4)
    bit_map_length, = struct.unpack("<l", fp.read(4))
    bit_map_value = fp.read(bit_map_length-8)
    if len(bit_map_value) < bit_map_length-8:
        log_repeat_info("Error: Read Data Header Failed, Maybe File Is Not Complete!")
        return False

    fp_csv = open(output_csv_file_path, 'a')
    try:
        while process_finish_flag != True:
            log_repeat_info("process data head")
            result = re.match('{(.*),"Map":{(.*)}}', bit_map_value)
            log_repeat_info("process data head::%s"%result.group()[0])
            data_header = {}
            if result != None:
                result = result.groups()
                map_header = result[0]
                map_content = result[1]

                list_map_header = map_header.split(",")
                for each_key in list_map_header:
                    list_key_value = each_key.split(":")
                    map_key = list_key_value[0].replace('"', '')
                    map_value = list_key_value[1].replace('"', '')
                    data_header[map_key] = map_value.strip()

                data_header['Map'] = []
                result = re.findall('"([0-9]+)":{"IDs":\\[(("[0-9a-zA-Z]+",?)+)\\],"Names":\\[(("[.0-9A-Za-z$ \\[\\]\\(\\):_-]*",?)+)\\],"DataTypes":\\[(([0-9]+,?)+)\\]}', map_content)
                if result != None:
                    for each_result in result:
                        object_type = {}
                        object_type['ObjectTypes'] = each_result[0]
                        object_type['IDs'] = each_result[1].replace('"', '').split(',')
                        object_type['Names'] = each_result[3].replace('"', '').split(',')
                        object_type['DataTypes'] = each_result[5].replace('"', '').split(',')
                        data_header['Map'].append(object_type)

            log_repeat_info("process data_head for file")
            count = 0
            list_data_type = []
            for key in data_header:
                if key =="Map":
                    for type in data_header['Map']:
                        count += len(type['IDs'])*len(type['DataTypes'])*4
                        for index_ids in range(len(type['IDs'])):
                            for index_data_type in type['DataTypes']:
                                list_index = [type['ObjectTypes'], index_data_type, type['Names'][index_ids], []]
                                list_data_type.append(list_index)
                                #log_repeat_info(list_index)
                else:
                    log_repeat_info(key +  data_header[key])

            log_repeat_info("DataTypes count:%d "% (count/4))
            # log_repeat_info("Total" , count * (int(data_header['EndTime'])-int(data_header['StartTime']))/int(data_header['Archive']), 'Bytes')

            size_collect_once = count
            times_collcet = (int(data_header['EndTime'])-int(data_header['StartTime']))/int(data_header['Archive'])
            #log_repeat_info("times_collcet:" ,times_collcet)

            title_row = "ObjectType,IDs,Names,DataTypes,"
            for i in range(times_collcet):
                title_row += "C_%03d," % (i+1)
                # log_repeat_info("DataIndex: C_%03d," % (i+1))
                buffer_read = fp.read(size_collect_once)
                # print "read collect_once,size:",size_collect_once
                if len(buffer_read) < size_collect_once:
                    log_repeat_info("Error: Data Conntent may be not enough!")
                    process_finish_flag = True
                index_in_buffer = 0
                while index_in_buffer < size_collect_once:
                    bytes_read_4 = buffer_read[index_in_buffer:index_in_buffer+4]
                    #        if bytes_read_4 == '\xFF\xFF\xFF\xFF':
                    #            log_repeat_info("Warning: Value is 0xFFFFFFFF, ObjectType: %s, IDs:%s, DataTypes: %s" % (list_data_type[index_in_buffer/4][0], list_data_type[index_in_buffer/4][1], list_data_type[index_in_buffer/4][2]))
                    bytes_read_int, = struct.unpack("<l", bytes_read_4)
                    list_data_type[index_in_buffer/4][3].append(str(bytes_read_int))
                    index_in_buffer += 4


            str_to_csv = "SN,Name,CtrlID,Archive,StartTime,EndTime,Periods\n"
            str_to_csv += '%s,%s,%s,%s,%s,%s,%s\n' %(bit_equip_sn.replace('\x00', ''), bit_equip_name.replace('\x00', ''), data_header['CtrlID'],data_header['Archive'],time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(int(data_header['StartTime']))),time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(int(data_header['EndTime']))), str(times_collcet))

            start_time = datetime.fromtimestamp(long(data_header['StartTime']))
            next_time = start_time
            time_list = []
            for i in xrange(len(list_data_type[0][3])):
                time_list.append(next_time)
                next_time += timedelta(seconds=int(data_header['Archive']))
            for i in range(len(list_data_type)):
                if not isResourceAndDatatypeNeeded(object_id=list_data_type[i][0], datatype_id=list_data_type[i][1]):
                    continue
                str_to_csv = ""
                str_to_csv += resource_name_dict.get(str(list_data_type[i][0])) + ','
                str_to_csv += metric_name_dict.get(str(list_data_type[i][1])) + ','
                str_to_csv += list_data_type[i][2] + ','
                for index in xrange(len(list_data_type[i][3])):
                    point_value = list_data_type[i][3][index]
                    fp_csv.write(('%s%s,%s,%d\n' % (
                    str_to_csv, point_value, time_list[index].strftime("%Y/%m/%d %H:%M"),
                    time.mktime(time_list[index].timetuple()))))

            bit_map_type = fp.read(4)
            log_repeat_info("bit_map_t" + bit_map_type)
            if bit_map_type == '':
                log_repeat_info("Info: Process Findshed!")
                process_finish_flag = True
            elif bit_map_type == '\x00\x00\x00\x00':
                bit_map_length, = struct.unpack("<l", fp.read(4))
                if bit_map_length < 8:
                    log_repeat_info("bit_map_length less than 8")
                    process_finish_flag = True
                else:
                    bit_map_value = fp.read(bit_map_length-8)
                    if len(bit_map_value) < bit_map_length-8:
                        log_repeat_info("Error: Read Data Header Failed, Maybe File Is Not Complete!")
                        return False
                    else:
                        log_repeat_info("Info: Find Next Data Header, Need Process!")
            else:
                process_finish_flag = True
    except Exception,e:
        log_repeat_error("Exception:%s"% e)
        return False

    fp_csv.close()
    fp.close()
    log_repeat_info("Info: Finish to process file.%s" % file_path)
    return True


# filter the resource and metrics
def isResourceAndDatatypeNeeded(object_id, datatype_id):
    if str(object_id) not in resources:
        return False
    if str(datatype_id) not in metrics:
        return False
    return True

#decompress file
def decompress_tgz(file_tgz):
    tar = tarfile.open(file_tgz)
    names = tar.getnames()
    temp_file_path = os.path.join(os.getcwd(), "temp")
    if not os.path.isdir(temp_file_path):
        os.mkdir(temp_file_path)
    if len(names) == 1:
        tar.extract(names[0], temp_file_path)
        return os.path.join(temp_file_path, names[0])
    log_error("perf file content error,perf file:" + input_path)
    return ""


# log
def __log(message, level):
    __init()
    output_log_file = os.path.join(log_path, "process_perf_files.log")
    with open(output_log_file, "a") as f:
        f.writelines("[%s]%s%s\n" % (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), level, message))

def log_error(message):
    __log(message, "[ERROR]")

def log_warn(message):
    __log(message, "[WARN]")

def log_info(message):
    __log(message, "[INFO]")

def __log_repeat(message, level):
    __init()
    output_log_file = os.path.join(log_path, "process_perf_files_repeat.log")
    with open(output_log_file, "a") as f:
        f.writelines("[%s]%s%s\n" % (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), level, message))

def log_repeat_error(message):
    __log_repeat(message, "[ERROR]")

def log_repeat_warn(message):
    __log_repeat(message, "[WARN]")

def log_repeat_info(message):
    __log_repeat(message, "[INFO]")

def split_files_by_sn(files):
    sn_to_perf_file_list = {}
    for file in files:
        file_sn = re.findall(re.compile(r"PerfData_.+SN_(.+)_SP"), file)[0]
        if  not sn_to_perf_file_list.has_key(file_sn):
            sn_to_perf_file_list[file_sn] = []
        sn_to_perf_file_list[file_sn].append(file)
    return sn_to_perf_file_list

def get_model_from_perf_file_name(file):
    return re.findall(re.compile(r"PerfData_(.+?)_SN"), file)[0]

'''
与内置资源类型对比，
如果全部存在于内置资源表，返回None
否则返回第一个不存在于内置资源表的资源
'''
def findFirstInvalidResource(resources):
    for r in resources:
        if not resource_name_dict.has_key(r):
            return r
    return None

'''
与内置资源类型对比，
如果全部存在于内置资源表，返回None
否则返回第一个不存在于内置资源表的资源
'''
def findFirstInvalidMetric(metrics):
    for m in metrics:
        if not metric_name_dict.has_key(m):
            return m
    return None


def process_perf_file_tgz_dir(input_path, output_path, log_path, is_delete_after_parse):
    log_info("begin to process_perf_file_tgz_dir:%s" % input_path)
    if not os.path.isdir(input_path):
        log_error("input is not a path!")
        return
    # list the perf files' directory
    files = os.listdir(input_path)
    # filter the tgz files
    files = filter(lambda x:os.path.isfile(os.path.join(input_path, x)) and x.endswith("tgz"), files)
    if not files:
        log_warn("there is no perf files yet in" + input_path)
    sn_to_perf_file_list = split_files_by_sn(files)
    for sn,sn_files in sn_to_perf_file_list.iteritems():
        # sort the perf files by change time asc
        sn_files.sort()
        find_result = re.findall(r"PerfData_.*SP\d+_\d+_(\d+(DST)*)\.tgz",sn_files[0])
        if not find_result:
            continue
        output_csv_file_name = '%s_%s_%s.csv' % (get_model_from_perf_file_name(sn_files[0]), sn, find_result[0][0])
        output_csv_file_path = os.path.join(output_path, output_csv_file_name)
        for file in sn_files:
            abs_tgz_file_path = os.path.join(input_path, file)
            decompressed_file_path = decompress_tgz(abs_tgz_file_path)
            is_process_successful = process_perf_file(decompressed_file_path, output_csv_file_path)
            # delete temp dat file
            os.remove(decompressed_file_path)
            # move source perf file to parse_error directory if not parsed successfully
            if not is_process_successful:
                if os.path.isfile(output_csv_file_path) and os.path.getsize(output_csv_file_path)<=0:
                    os.remove(output_csv_file_path)
                parse_error_path = os.path.join(input_path, "errorParse")
                if not os.path.isdir(parse_error_path):
                    os.mkdir(parse_error_path)
                shutil.move(abs_tgz_file_path, os.path.join(parse_error_path, file))
                continue

            # continue
            # delete source perf file if needed
            if is_delete_after_parse:
                os.remove(abs_tgz_file_path)
            else:
                # move the parsed files to directory(parsed_files) in input_path
                parsed_files_path = os.path.join(input_path, "parsed_files")
                if not os.path.isdir(parsed_files_path):
                    os.mkdir(parsed_files_path)
                shutil.move(abs_tgz_file_path, os.path.join(parsed_files_path, file))

def check_and_set_default_param():
    global input_path
    global output_path
    global log_path
    global is_delete_after_parse
    global resources
    global metrics
    #Mandatory parameter check
    if not input_path or not output_path:
        print "param error,type \"%s -h\" for help." % sys.argv[0]
        return False
    #input_path existence
    if not os.path.isdir(input_path):
        print "%s does not exist." % input_path
        return False
    #log path default
    if not log_path:
        log_path = os.path.join(os.getcwd(), "logPerf")
    #is_delete_after_parse default
    if not is_delete_after_parse:
        is_delete_after_parse = False
    else:
        if is_delete_after_parse in trueFlags:
            is_delete_after_parse = True
        elif is_delete_after_parse in falseFlags:
            is_delete_after_parse = False
        else:
            print "%s param error,type \"%s -h\" for help." % (d,sys.argv[0])
            return False

    if not resources:
        resources = defualt_resources
    else:
        resources = list(set(resources.split(",")))
        #Resource existence
        firstInvalidResource = findFirstInvalidResource(resources)
        if firstInvalidResource:
            print  "invalid resource type:%s" %(firstInvalidResource)
            return False

    if not metrics:
        metrics = default_metrics
    else:
        metrics = list(set(metrics.split(",")))
        #Metric existence
        firstInvalidMetric = findFirstInvalidMetric(metrics)
        if firstInvalidMetric:
            print  "invalid metric type:%s" %(firstInvalidMetric)
            return False

    return True

def __init():
    if not os.path.isdir(log_path):
        os.mkdir(log_path)
    if not os.path.isdir(output_path):
        os.mkdir(output_path)



def usage(argv0):
    print "Usage:"
    print "  python %s -i %s -o %s -r %s -m %s -l %s -d %s" % (argv0,i,o,r,m,l,d)
    print "\n"
    print "Argument introduction:"
    print "  %s:\t%s" %(i,"The path where performance files exported(Mandatory)")
    print "\n"
    print "  %s:\t%s" %(o,"The path where parsed csv files write(Mandatory)")
    print "\n"
    print "  %s:\t\t%s" %(l,'''The path where log files write(Optional,
                        current path default)''')
    print "\n"
    print "  %s:\t\t%s" %(d,'''Whether delete source performance files
                        after parsed.(Optional, default is FALSE)''')
    print "    \t\t\t%s"% "Y/YES/TRUE means delete after parsed"
    print "    \t\t\t%s"% "N/NO/FALSE means do not delete after parsed"
    print "\n"
    print "  %s:\t\t%s" %(r,'''Resource types you want to collect(Optional)
                        Separated by comma.For example:-r 207,11
                        Default is
                        11:LUN,
                        207:Controller,
                        21:Host,
                        212:FC Port,
                        213:Ethernet Port,
                        235:Bond Port,
                        279:Logical Port,
                        16500:IB Port''')
    print "\n"
    print "  %s:\t\t%s" %(m,'''Metric types you want to collect(Optional)
                        Separated by comma.For example:-m 25,26;
                        Default is 23:Read bandwidth (MB/s),
                        26:Write bandwidth (MB/s),
                        21:Block bandwidth (MB/s),
                        25:Read IOPS (IO/s),
                        28:Write IOPS (IO/s),
                        22:Total IOPS (IO/s),
                        197:Avg. read I/O response time (ms),
                        198:Avg. write I/O response time (ms),
                        78:Avg. I/O response time (ms),
                        18:Usage (%)''')


################main#################

try:
    opts, args = getopt.getopt(sys.argv[1:], "hi:o:l:d:r:m:")
    if not opts:
        usage(sys.argv[0])
        sys.exit()
    for op, value in opts:
        if op == "-i":
            input_path = value
        elif op == "-o":
            output_path = value
        elif op == "-l":
            log_path = value
        elif op == "-d":
            is_delete_after_parse = value
        elif op == "-r":
            resources = value
        elif op == "-m":
            metrics = value
        elif op == "-h":
            usage(sys.argv[0])
            sys.exit()
except Exception,e:
        print "param error,type \"%s -h\" for help." % sys.argv[0]
        sys.exit()


if not check_and_set_default_param():
    sys.exit()


__init()
process_perf_file_tgz_dir(input_path, output_path, log_path, is_delete_after_parse)

print "Process End!"

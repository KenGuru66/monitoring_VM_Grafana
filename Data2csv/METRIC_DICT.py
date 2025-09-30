METRIC_NAME_DICT = {
    "2": "读I/O比率(%)",#Read I/O ratio (%)
    "3": "写I/O比率(%)",#Write I/O ratio (%)
    "4": "当前带宽(MB/s)",#Current bandwidth (MB/s)
    "5": "Max. bandwidth (MB/s)",
    "6": "当前IOPS",#Current IOPS
    "8": "最大延迟",#Max latency
    "9": "平均延迟",#Average latency
    "10": "Cache hit ratio (%)",
    "11": "本地写Cache利用率(%)",#Local write cache utilization (%)
    "12": "Mirror write cache usage (%)",
    "13": "读I/O流量",#Read I/O traffic
    "14": "写I/O流量",#Write I/O traffic
    "15": "最大功耗",#Max power consumption
    "16": "平均功耗",#Average power consumption
    "17": "最小功耗",#Min power consumption
    "18": "Usage (%)",
    "19": "Queue length",
    "20": "响应时间(ms)",#Response time (ms)
    "21": "Block bandwidth (MB/s)",
    "22": "Total IOPS (IO/s)",
    "23": "Read bandwidth (MB/s)",
    "24": "Avg. read I/O size (KB)",
    "25": "Read IOPS (IO/s)",
    "26": "Write bandwidth (MB/s)",
    "27": "Avg. write I/O size (KB)",
    "28": "Write IOPS (IO/s)",
    "29": "Service time (ms)",
    "30": "Read I/O granularity distribution: [0K,1K) (%)",
    "31": "Read I/O granularity distribution: [1K,2K) (%)",
    "32": "Read I/O granularity distribution: [2K,4K) (%)",
    "33": "Read I/O granularity distribution: [4K,8K) (%)",
    "34": "Read I/O granularity distribution: [8K,16K) (%)",
    "35": "Read I/O granularity distribution: [16K,32K) (%)",
    "36": "Read I/O granularity distribution: [32K,64K) (%)",
    "37": "Read I/O granularity distribution: [64K,128K) (%)",
    "38": "Read I/O granularity distribution: [128K,256K) (%)",
    "39": "Read I/O granularity distribution: [256K,512K) (%)",
    "40": "Read I/O granularity distribution: [512K,+∞) (%)",
    "41": "Write I/O granularity distribution: [0K,1K) (%)",
    "42": "Write I/O granularity distribution: [1K,2K) (%)",
    "43": "Write I/O granularity distribution: [2K,4K) (%)",
    "44": "Write I/O granularity distribution: [4K,8K) (%)",
    "45": "Write I/O granularity distribution: [8K,16K) (%)",
    "46": "Write I/O granularity distribution: [16K,32K) (%)",
    "47": "Write I/O granularity distribution: [32K,64K) (%)",
    "48": "Write I/O granularity distribution: [64K,128K) (%)",
    "49": "Write I/O granularity distribution: [128K,256K) (%)",
    "50": "Write I/O granularity distribution: [256K,512K) (%)",
    "51": "Write I/O granularity distribution: [512K,+∞) (%)",
    "52": "读写I/O分布：512B",#Read/Write I/O distribution: 512B
    "53": "读写I/O分布：1KB",#Read/Write I/O distribution: 1KB
    "54": "读写I/O分布：2KB",#Read/Write I/O distribution: 2KB
    "55": "读写I/O分布：4KB",#Read/Write I/O distribution: 4KB
    "56": "读写I/O分布：8KB",#Read/Write I/O distribution: 8KB
    "57": "读写I/O分布：16KB",#Read/Write I/O distribution: 16KB
    "58": "读写I/O分布：32KB",#Read/Write I/O distribution: 32KB
    "59": "读写I/O分布：64KB",#Read/Write I/O distribution: 64KB
    "60": "周期内写I/O总数",#Total write I/Os during the period
    "61": "周期内读I/O总数",#Total read I/Os during the period
    "62": "读写I/O分布：512KB",#Read/Write I/O distribution: 512KB
    "63": "周期内写I/O总数",#Total write I/Os during the period
    "64": "周期内读I/O总数",#Total read I/Os during the period
    "65": "随机顺序比例",#Random vs sequential ratio
    "66": "使用率(%)",#Usage (%)
    "67": "Usage (%)",
    "68": "Avg. CPU usage (%)",
    "69": "Avg. cache usage (%)",
    "70": "交换分区占用率(%)",#Swap partition usage (%)
    "71": "读吞吐量(MB/s)",#Read throughput (MB/s)
    "72": "写吞吐量(MB/s)",#Write throughput (MB/s)
    "73": "网络当前进包数量",#Current incoming network packets
    "74": "网络当前出包数量",#Current outgoing network packets
    "75": "工作温度",#Operating temperature
    "76": "功耗",#Power consumption
    "77": "电压",#Voltage
    "78": "Avg. I/O response time (ms)",
    "79": "Max. I/O response time (ms)",
    "80": "Dirty page ratio (%)",
    "81": "Cache flushes to write requests ratio (%)",
    "82": "Cache flushing bandwidth (MB/s)",
    "83": "Cache flushes caused by high watermark",
    "84": "Cache flushes caused by the timer",
    "85": "Low watermark reaching times",
    "86": "Full-stripe write request ratio (%)",
    "87": "Prefetch traffic (MB/s)",
    "88": "Prefetch rate (%)",
    "89": "Read cache hits per second",
    "90": "Read cache misses per second",
    "91": "Write cache hits by reads per second",
    "92": "Read cache hits by reads per second",
    "93": "Read cache hit ratio (%)",
    "94": "Read cache rehit ratio (%)",
    "95": "Write cache hit ratio (%)",
    "96": "Write cache rehit ratio (%)",
    "97": "Write cache hits per second", 
    "98": "Write cache misses per second",
    "99": "Time since last synchronization (s)",
    "100": "Unsynchronized data amount (MB)",
    "101": "Read requests to the snapshot LUN",
    "102": "Read requests redirected to the source LUN",
    "103": "COW requests to the source LUN",
    "104": "COW requests from the snapshot LUN",
    "105": "Write requests to the snapshot LUN",
    "106": "Write requests to the source LUN exceeding the grain size",
    "107": "Chunks used by the snapshot copy",
    "108": "本地Cache利用率(%)",#Local cache usage (%)
    "109": "镜像Cache利用率(%)",#Mirror cache usage (%)
    "110": "Cache read usage (%)",#Cache read usage (%)
    "111": "主机下发数据的耗时(ms)",#Time taken to send data from host (ms)
    "112": "设备保存写数据的耗时(ms)",#Time taken to save write data by device (ms)
    "113": "释放写请求资源的耗时(ms)",#Time taken to release write request resources (ms)
    "114": "执行读请求的耗时(ms)",#Time taken to execute read request (ms)
    "115": "释放读请求资源的耗时(ms)",#Time taken to release read request resources (ms)
    "116": "Cache读I/O响应时间(ms)",#Cache read I/O response time (ms)
    "117": "Cache写I/O响应时间(ms)",#Cache write I/O response time (ms)
    "118": "Cache镜像I/O响应时间(ms)",#Cache mirror I/O response time (ms)
    "119": "写请求申请内存的耗时(ms)",#Time taken to allocate memory for write request (ms)
    "120": "Cache write usage (%)",
    "121": "Cache写盘I/O数(个)",#Number of cache write disk I/Os
    "122": "Cache写盘页面数(个)",#Number of cache write disk pages
    "123": "Read bandwidth (KB/s)",
    "124": "Write bandwidth (KB/s)",
    "125": "读I/O平均大小(A控)(KB)",#Average read I/O size (Controller A) (KB)
    "126": "写I/O平均大小(A控)(KB)",#Average write I/O size (Controller A) (KB)
    "127": "最大I/O响应时间(A控)(ms)",#Max I/O response time (Controller A) (ms)
    "128": "平均I/O响应时间(A控)(ms)",#Average I/O response time (Controller A) (ms)
    "129": "利用率(A控)(%)",#Usage (Controller A) (%)
    "130": "队列长度(A控)(个)",#Queue length (Controller A)
    "131": "服务时间(A控)(ms)",#Service time (Controller A) (ms)
    "132": "每秒合并读I/O的个数(A控)(个/秒)",#Number of merged read I/Os per second (Controller A)
    "133": "每秒合并写I/O的个数(A控)(个/秒)",#Number of merged write I/Os per second (Controller A)
    "134": "读等待时间(A控)(ms)",#Read wait time (Controller A) (ms)
    "135": "写等待时间(A控)(ms)",#Write wait time (Controller A) (ms)
    "136": "I/O平均大小(A控)(sector)",#Average I/O size (Controller A) (sectors)
    "137": "读I/O平均大小(B控)(KB)",#Average read I/O size (Controller B) (KB)
    "138": "写I/O平均大小(B控)(KB)",#Average write I/O size (Controller B) (KB)
    "139": "最大I/O响应时间(B控)(ms)",#Max I/O response time (Controller B) (ms)
    "140": "平均I/O响应时间(B控)(ms)",#Average I/O response time (Controller B) (ms)
    "141": "利用率(B控)(%)",#Usage (Controller B) (%)
    "142": "队列长度(B控)(个)",#Queue length (Controller B)
    "143": "服务时间(B控)(ms)",#Service time (Controller B) (ms)
    "144": "每秒合并读I/O的个数(B控)(个/秒)",#Number of merged read I/Os per second (Controller B)
    "145": "每秒合并写I/O的个数(个/秒)",#Number of merged write I/Os per second (Controller B)
    "146": "读等待时间(B控)(ms)",#Read wait time (Controller B) (ms)
    "147": "写等待时间(B控)(ms)",#Write wait time (Controller B) (ms)
    "148": "I/O平均大小(B控)(sector)",#Average I/O size (Controller B) (sectors)
    "149": "读I/O粒度分布：< 4K(%)",#Read I/O granularity distribution: < 4K (%)
    "150": "读I/O粒度分布：≤ 8K(%)",
    "151": "读I/O粒度分布：≤ 16K(%)",
    "152": "读I/O粒度分布：≤ 32K(%)",
    "153": "读I/O粒度分布：≤ 64K(%)",
    "154": "读I/O粒度分布：≤ 128K(%)",
    "155": "读I/O粒度分布：≤ 256K(%)",
    "156": "读I/O粒度分布：≤ 512K(%)",
    "157": "读I/O粒度分布：≤ 1M(%)",
    "158": "读I/O粒度分布：≤ 2M(%)",
    "159": "读I/O粒度分布：> 2M(%)",
    "160": "写I/O粒度分布：< 4K(%)",#Write I/O granularity distribution: < 4K (%)
    "161": "写I/O粒度分布：<= 8K(%)",
    "162": "写I/O粒度分布：<= 16K(%)",
    "163": "写I/O粒度分布：<= 32K(%)",
    "164": "写I/O粒度分布：<= 64K(%)",
    "165": "写I/O粒度分布：<= 128K(%)",
    "166": "写I/O粒度分布：<= 256K(%)",
    "167": "写I/O粒度分布：<= 512K(%)",
    "168": "写I/O粒度分布：<= 1M(%)",
    "169": "写I/O粒度分布：<= 2M(%)",
    "170": "写I/O粒度分布：> 2M(%)",
    "171": "读写I/O粒度分布：< 4K(%)",#Read/Write I/O granularity distribution: < 4K (%)
    "172": "读写I/O粒度分布：<= 8K(%)",
    "173": "读写I/O粒度分布：<= 16K(%)",
    "174": "读写I/O粒度分布：<= 32K(%)",
    "175": "读写I/O粒度分布：<= 64K(%)",
    "176": "读写I/O粒度分布：<= 128K(%)",
    "177": "读写I/O粒度分布：<= 256K(%)",
    "178": "读写I/O粒度分布：<= 512K(%)",
    "179": "读写I/O粒度分布：<= 1M(%)",
    "180": "读写I/O粒度分布：<= 2M(%)",
    "181": "读写I/O粒度分布：> 2M(%)",
    "182": "OPS (per second)",#Filesystem IOPS
    "183": "在线用户数",#Number of online users
    "184": "硬配额空间容量",#Hard quota space capacity
    "185": "已用容量",#Used capacity
    "186": "总容量",#Total capacity
    "187": "重删率(%)",#Deduplication rate (%)
    "188": "包传输速率(Packets/s)",#Packet transmission rate (Packets/s)
    "189": "丢包率(%)",#Packet loss rate (%)
    "190": "错误包率(%)",#Packet error rate (%)
    "191": "包溢出率(%)",#Packet overflow rate (%)
    "192": "Access frequency (%)",
    "193": "包吞吐率(%)",#Packet throughput rate (%)
    "194": "远程复制带宽(KB/s)",#Remote replication bandwidth (KB/s)
    "195": "Max. read I/O response time (ms)",
    "196": "Max. write I/O response time (ms)",
    "197": "Avg. read I/O response time (ms)",
    "198": "Avg. write I/O response time (ms)",
    "199": "Read I/O Latency Distribution: [0ms,10ms) (%)",
    "200": "Read I/O Latency Distribution: [10ms,20ms) (%)",
    "201": "Read I/O Latency Distribution: [20ms,50ms) (%)",
    "202": "Read I/O Latency Distribution: [50ms,100ms) (%)",
    "203": "Read I/O Latency Distribution: [100ms,200ms) (%)",
    "204": "Read I/O Latency Distribution: [200ms,+∞) (%)",
    "205": "Write I/O Latency Distribution: [0ms,10ms) (%)",
    "206": "Write I/O Latency Distribution: [10ms,20ms) (%)",
    "207": "Write I/O Latency Distribution: [20ms,50ms) (%)",
    "208": "Write I/O Latency Distribution: [50ms,100ms) (%)",
    "209": "Write I/O Latency Distribution: [100ms,200ms) (%)",
    "210": "Write I/O Latency Distribution: [200ms,+∞) (%)",
    "211": "磁盘IOPS(IO/s)",#Disk IOPS (IO/s)
    "217": "Max. CPU usage (%)",
    "218": "Max. memory usage (%)",
    "219": "NFS bandwidth (KB/s)",
    "220": "NFS write bandwidth (KB/s)",
    "221": "NFS read bandwidth (KB/s)",
    "222": "CIFS bandwidth (KB/s)",
    "223": "CIFS write bandwidth (KB/s)",
    "224": "CIFS read bandwidth (KB/s)",
    "225": "Number of connected clients",
    "226": "Number of connected NFS clients",
    "227": "Number of connected CIFS clients",
    "228": "Avg. I/O size (KB)",
    "229": "Network packet stream speed (per second)",
    "230": "Network packet input stream speed (per second)",
    "231": "Network packet output stream speed (per second)",
    "232": "Read OPS (per second)",
    "233": "Write OPS (per second)",
    "236": "Bandwidth (KB/s)",
    "240": "Average queue depth",
    "241": "SCSI commands executed per second",
    "242": "Verify commands per second",
    "247": "Number of dirty data pages",
    "248": "Threshold for dirty data page quantity (%)",
    "249": "Ratio of dirty data pages to total pages (%)",
    "250": "Used cache ratio (%)",
    "251": "Number of sent-by-host read/write I/Os that can be immediately found in the cache per second",
    "252": "Number of sent-by-host read I/Os that can be immediately found in the cache per second",
    "253": "Number of sent-by-host write I/Os that can be immediately found in the cache per second",
    "254": "Number of sent-by-host read/write I/Os that cannot be immediately found in the cache per second",
    "255": "Number of sent-by-host read I/Os that cannot be immediately found in the cache per second",
    "256": "Number of sent-by-host write I/Os that cannot be immediately found in the cache per second",
    "257": "Back-end read/write requests per second",
    "258": "Back-end read requests per second",
    "259": "Back-end write requests per second",
    "260": "Back-End traffic (MB/s)",
    "261": "Back-end read traffic (MB/s)",
    "262": "Back-end write traffic (MB/s)",
    "263": "Read miss response time (ms)",
    "264": "Write miss response time (ms)",
    "265": "Ratio of read I/Os to total I/Os (%)",
    "266": "Ratio of write I/Os to total I/Os (%)",
    "267": "Ratio of read I/Os to total read I/Os (%)",
    "268": "Ratio of write I/Os to total write I/Os (%)",
    "269": "Ratio of lost read requests (%)",
    "270": "Ratio of lost write requests (%)",
    "271": "Back-end read request time (ms)",
    "272": "Back-end write request time (ms)",
    "273": "Back-end read request queuing time (ms)",
    "274": "Back-end read response time (ms)",
    "275": "Back-end write response time (ms)",
    "276": "Avg. back-end response time (ms)",
    "277": "Ratio of back-end read requests (%)",
    "278": "Ratio of back-end write requests (%)",
    "279": "Number of data transfer requests from front-end host ports to cache per second",
    "280": "Number of data transfer read requests from front-end host ports to cache per second",
    "281": "Number of data transfer write requests from front-end host ports to cache per second",
    "282": "Number of hit read requests sent by front-end host ports per second",
    "283": "Number of hit write requests sent by front-end host ports per second",
    "284": "Number of lost requests per second",
    "285": "Number of lost read requests on all the front-end host ports per second",
    "286": "Number of lost write requests on all the front-end host ports per second",
    "287": "Ratio of read requests to total requests (%)",
    "288": "Ratio of write requests to total requests (%)",
    "289": "Hit ratio of read/write requests (%)",
    "290": "Read request hit ratio (%)",
    "291": "I/Os per second",
    "292": "Data transfer requests per second",
    "293": "Data transfer read  requests per second",
    "294": "Data transfer write  requests per second",
    "295": "Read/write traffic (MB/s)",
    "296": "Read/write traffic on ports (MB/s)",
    "297": "Read/write IOPS on ports",
    "298": "Back-end read traffic (MB/s)",
    "299": "Back-end write traffic (MB/s)",
    "300": "Port average requests size",
    "301": "Max. number of dirty data pages",
    "302": "Number of randomly hit requests per second",
    "303": "Hit ratio (%)",
    "304": "Miss ratio (%)",
    "305": "Random read ratio (%)",
    "306": "Random write ratio (%)",
    "307": "Max. IOPS (IO/s)",
    "308": "Total number of failed I/Os",
    "309": "Number of failed I/Os per second",
    "310": "Faulty I/O ratio (%)",
    "311": "Throughput (MB/s)",
    "312": "Read throughput (MB/s)",
    "313": "Write throughput (MB/s)",
    "333": "Cache water (%)",
    "369": "Service Time(us)",#NEW
    "370": "Avg. I/O Response Time (us)",#NEW
    "371": "Max. I/O Response Time (us)",#NEW
    "384": "Avg. Read I/O Response Time(us)",
    "385": "Avg. Write I/O Response Time(us)",
    "392": "Read I/O Latency Distribution: [0 us, 500 us) (%)",#NEW
    "393": "Read I/O Latency Distribution: [500 us, 1 ms) (%)",#NEW
    "394": "Read I/O Latency Distribution: [1 ms, 2 ms) (%)",#NEW   
    "395": "Read I/O Latency Distribution: [2 ms, 5 ms) (%)",#NEW   
    "396": "Read I/O Latency Distribution: [5ms,10ms) (%)",
    "397": "Read I/O Latency Distribution: [10 ms, +∞) (%)",#NEW 
    "398": "Write I/O Latency Distribution: [0 us, 500 us) (%)",#NEW 
    "399": "Write I/O Latency Distribution: [500 us, 1 ms) (%)",#NEW 
    "400": "Write I/O Latency Distribution: [1 ms, 2 ms) (%)",#NEW
    "401": "Write I/O Latency Distribution: [2 ms, 5 ms) (%)",#NEW
    "402": "Write I/O Latency Distribution: [5ms,10ms) (%)",
    "403": "Write I/O Latency Distribution: [10 ms, +∞) (%)",#NEW
    "404": "Read and Write I/O Latency Distribution: [0 us, 500 us) (%)",#NEW
    "405": "Read and Write I/O Latency Distribution: [500 us, 1 ms) (%)",#NEW
    "410": "Protocol Operations Average Latency For NFS (ms)",
    "411": "Protocol Operations Max Latency For NFS (ms)",
    "412": "Protocol Write Operation Average Latency For NFS (ms)",
    "413": "Protocol Write Operation Max Latency For NFS (ms)",
    "414": "Protocol Read Operation Average Latency For NFS (ms)",
    "415": "Protocol Read Operation Max Latency For NFS (ms)",
    "416": "Protocol Operations Average Latency For CIFS (ms)",
    "417": "Protocol Operations Max Latency For CIFS (ms)",
    "418": "Protocol Write Operation Average Latency For CIFS (ms)",
    "419": "Protocol Write Operation Max Latency For CIFS (ms)",
    "420": "Protocol Read Operation Average Latency For CIFS (ms)",
    "421": "Protocol Read Operation Max Latency For CIFS (ms)",
    "428": "Average Latency For Operations (ms)",
    "429": "Max Latency For Operations (ms)",
    "430": "Average Latency For Write Operation (ms)",
    "431": "Max Latency For Write Operation (ms)",
    "432": "Average Latency For Read Operation (ms)",
    "433": "Max Latency For Read Operation (ms)",
    "435": "Count Of Protocol Read Operation Large Latency Continuous Occurred For CIFS",
    "436": "Count Of Protocol Read Operation Large Latency Continuous Occurred For NFS",
    "437": "Count Of Protocol Read Operation Large Latency Continuous Occurred",
    "439": "Throughput (Bps)",
    "462": "Space Usage (%)",
    "463": "Space Size (MB)",
    "464": "Average Read OPS Response Time (ms)",
    "465": "Average Write OPS Response Time (ms)",
    "466": "Read I/O Granularity Distribution: [0,512B) (%)",
    "467": "Read I/O Granularity Distribution: [512B,1K) (%)",
    "468": "Read I/O Granularity Distribution: [256K,+∞) (%)",
    "469": "Write I/O Granularity Distribution: [0,512B) (%)",
    "470": "Write I/O Granularity Distribution: [512B,1K) (%)",
    "471": "Write I/O Granularity Distribution: [256K,+∞) (%)",
    "472": "Min Latency For Operations (ms)",
    "473": "Logical Bandwidth (MB/s)",
    "475": "File bandwidth(B/s)",
    "476": "File OPS(per second)",
    "508": "Average Latency For Operations (ms)",#Avg. Operation Response Time (us)
    "509": "Max Latency For Operations (ms)",
    "510": "Min Latency For Operations (ms)",
    "511": "File bandwidth(MB/s)",#File Bandwidth (KB/s)
    "512": "Throughput (MB/s)",
    "513": "Total amount of migrated data",
    "514": "Amount of data migrated to SSDs",
    "515": "Amount of data migrated to SAS disks",
    "516": "Amount of data migrated to NL-SAS disks",
    "517": "Amount of data migrated from SAS disks to SSDs",
    "518": "Amount of data migrated from NL-SAS disks to SSDs",
    "519": "Amount of data migrated from SSDs to SAS disks",
    "520": "Amount of data migrated from NL-SAS disks to SAS disks",
    "521": "Amount of data migrated from SSDs to NL-SAS disks",
    "522": "Amount of data migrated from SSDs to NL-SAS disks",
    "523": "Service time (ms)",#Service Time(Excluding Queue Time)(us)
    "524": "Average Read OPS Response Time (ms)",#Avg. Read OPS Response Time (us)
    "525": "Average Write OPS Response Time (ms)",#Avg. Write OPS Response Time (us)
    "530": "Read I/O Latency Distribution: [0ms,5ms) (%)",
    "531": "Write I/O Latency Distribution: [0ms,5ms) (%)",
    "532": "Number of failed read I/Os",
    "533": "Number of failed write I/Os",
    "534": "File System Bandwidth (KB/s)",
    "535": "File System Read Bandwidth (KB/s)",
    "536": "File System Write Bandwidth (KB/s)",
    "537": "S3 Bandwidth (KB/s)",
    "538": "S3 Read Bandwidth (KB/s)",
    "539": "S3 Write Bandwidth (KB/s)",
    "540": "S3 Delete Number",
    "541": "S3 Delete Failed Number",
    "542": "S3 Delete Failed Number(client's cause)",
    "543": "S3 Get Number",
    "544": "S3 Get Failed Number",
    "545": "S3 Get Failed Number(client's cause)",
    "546": "S3 Put Number",
    "547": "S3 Put Failed Number",
    "548": "S3 Put Failed Number(client's cause)",
    "549": "S3 Connect Failed Rate(%)",
    "550": "Swift Bandwidth (KB/s)",
    "551": "Swift Read Bandwidth (KB/s)",
    "552": "Swift Write Bandwidth (KB/s)",
    "553": "Swift Delete Number",
    "554": "Swift Delete Failed Number",
    "555": "Swift Delete Failed Number(client's cause)",
    "556": "Swift Get Number",
    "557": "Swift Get Failed Number",
    "558": "Swift Get Failed Number(client's cause)",
    "559": "Swift Put Number",
    "560": "Swift Put Failed Number",
    "561": "Swift Put Failed Number(client's cause)",
    "562": "Swift Connect Failed Rate(%)",
    "563": "NFS V3 NULL procedure count",
    "564": "NFS V3 GETATTR procedure count",
    "565": "NFS V3 SETATTR procedure count",
    "566": "NFS V3 LOOKUP procedure count",
    "567": "NFS V3 ACCESS procedure count",
    "568": "NFS V3 READLINK procedure count",
    "569": "NFS V3 READ procedure count",
    "570": "NFS V3 WRITE procedure count",
    "571": "NFS V3 CREATE procedure count",
    "572": "NFS V3 MKDIR procedure count",
    "573": "NFS V3 SYMLINK procedure count",
    "574": "NFS V3 MKNOD procedure count",
    "575": "NFS V3 REMOVE procedure count",
    "576": "NFS V3 RMDIR procedure count",
    "577": "NFS V3 RENAME procedure count",
    "578": "NFS V3 LINK procedure count",
    "579": "NFS V3 READDIR procedure count",
    "580": "NFS V3 READDIRPLUS procedure count",
    "581": "NFS V3 FSSTAT procedure count",
    "582": "NFS V3 FSINFO procedure count",
    "583": "NFS V3 PATHCONF procedure count",
    "584": "NFS V3 COMMIT procedure count",
    "585": "NFS V3 extendcmd procedure count",
    "586": "NFS V4 NULL procedure count",
    "587": "NFS V4 COMPOUND procedure count",
    "588": "NFS V4 ACCESS operation count",
    "589": "NFS V4 CLOSE operation count",
    "590": "NFS V4 COMMIT operation count",
    "591": "NFS V4 CREATE operation count",
    "592": "NFS V4 DELEGPURGE operation count",
    "593": "NFS V4 DELEGRETURN operation count",
    "594": "NFS V4 GETATTR operation count",
    "595": "NFS V4 GETFH operation count",
    "596": "NFS V4 LINK operation count",
    "597": "NFS V4 LOCK operation count",
    "598": "NFS V4 LOCKT operation count",
    "599": "NFS V4 LOCKU operation count",
    "600": "NFS V4 LOOKUP operation count",
    "601": "NFS V4 LOOKUPP operation count",
    "602": "NFS V4 NVERIFY operation count",
    "603": "NFS V4 OPEN operation count",
    "604": "NFS V4 OPENATTR operation count",
    "605": "NFS V4 OPEN_CONFIRM operation count",
    "606": "NFS V4 OPEN_DOWNGRADE operation count",
    "607": "NFS V4 PUTFH operation count",
    "608": "NFS V4 PUTPUBFH operation count",
    "609": "NFS V4 PUTROOTFH operation count",
    "610": "NFS V4 READ operation count",
    "611": "NFS V4 READDIR operation count",
    "612": "NFS V4 READLINK operation count",
    "613": "NFS V4 REMOVE operation count",
    "614": "NFS V4 RENAME operation count",
    "615": "NFS V4 RENEW operation count",
    "616": "NFS V4 RESTOREFH operation count",
    "617": "NFS V4 SAVEFH operation count",
    "618": "NFS V4 SECINFO operation count",
    "619": "NFS V4 SETATTR operation count",
    "620": "NFS V4 SETCLIENTID operation count",
    "621": "NFS V4 SETCLIENTID_CONFIRM operation count",
    "622": "NFS V4 VERIFY operation count",
    "623": "NFS V4 WRITE operation count",
    "624": "NFS V4 RELEASE_LOCKOWNER operation count",
    "625": "NFS V3 procedures average latency excluding read and write",
    "626": "NFS V4 operations average latency excluding read and write",
    "627": "NFS operation count per second",
    "628": "NFS V3 Read I/O count: [0K,512B)",
    "629": "NFS V3 Read I/O count: [512B,1K)",
    "630": "NFS V3 Read I/O count: [1K,2K)",
    "631": "NFS V3 Read I/O count: [2K,4K)",
    "632": "NFS V3 Read I/O count: [4K,8K)",
    "633": "NFS V3 Read I/O count: [8K,16K)",
    "634": "NFS V3 Read I/O count: [16K,32K)",
    "635": "NFS V3 Read I/O count: [32K,64K)",
    "636": "NFS V3 Read I/O count: [64K,128K)",
    "637": "NFS V3 Read I/O count: [128K,256K)",
    "638": "NFS V3 Read I/O count: [256K,+∞)",
    "639": "NFS V3 Write I/O count: [0K,512B)",
    "640": "NFS V3 Write I/O count: [512B,1K)",
    "641": "NFS V3 Write I/O count: [1K,2K)",
    "642": "NFS V3 Write I/O count: [2K,4K)",
    "643": "NFS V3 Write I/O count: [4K,8K)",
    "644": "NFS V3 Write I/O count: [8K,16K)",
    "645": "NFS V3 Write I/O count: [16K,32K)",
    "646": "NFS V3 Write I/O count: [32K,64K)",
    "647": "NFS V3 Write I/O count: [64K,128K)",
    "648": "NFS V3 Write I/O count: [128K,256K)",
    "649": "NFS V3 Write I/O count: [256K,+∞)",
    "650": "NFS V4 Read I/O count: [0K,512B)",
    "651": "NFS V4 Read I/O count: [512B,1K)",
    "652": "NFS V4 Read I/O count: [1K,2K)",
    "653": "NFS V4 Read I/O count: [2K,4K)",
    "654": "NFS V4 Read I/O count: [4K,8K)",
    "655": "NFS V4 Read I/O count: [8K,16K)",
    "656": "NFS V4 Read I/O count: [16K,32K)",
    "657": "NFS V4 Read I/O count: [32K,64K)",
    "658": "NFS V4 Read I/O count: [64K,128K)",
    "659": "NFS V4 Read I/O count: [128K,256K)",
    "660": "NFS V4 Read I/O count: [256K,+∞)",
    "661": "NFS V4 Write I/O count: [0K,512B)",
    "662": "NFS V4 Write I/O count: [512B,1K)",
    "663": "NFS V4 Write I/O count: [1K,2K)",
    "664": "NFS V4 Write I/O count: [2K,4K)",
    "665": "NFS V4 Write I/O count: [4K,8K)",
    "666": "NFS V4 Write I/O count: [8K,16K)",
    "667": "NFS V4 Write I/O count: [16K,32K)",
    "668": "NFS V4 Write I/O count: [32K,64K)",
    "669": "NFS V4 Write I/O count: [64K,128K)",
    "670": "NFS V4 Write I/O count: [128K,256K)",
    "671": "NFS V4 Write I/O count: [256K,+∞)",
    "672": "NFS Read I/O count: [0K,512B)",
    "673": "NFS Read I/O count: [512B,1K)",
    "674": "NFS Read I/O count: [1K,2K)",
    "675": "NFS Read I/O count: [2K,4K)",
    "676": "NFS Read I/O count: [4K,8K)",
    "677": "NFS Read I/O count: [8K,16K)",
    "678": "NFS Read I/O count: [16K,32K)",
    "679": "NFS Read I/O count: [32K,64K)",
    "680": "NFS Read I/O count: [64K,128K)",
    "681": "NFS Read I/O count: [128K,256K)",
    "682": "NFS Read I/O count: [256K,+∞)",
    "683": "NFS Write I/O count: [0K,512B)",
    "684": "NFS Write I/O count: [512B,1K)",
    "685": "NFS Write I/O count: [1K,2K)",
    "686": "NFS Write I/O count: [2K,4K)",
    "687": "NFS Write I/O count: [4K,8K)",
    "688": "NFS Write I/O count: [8K,16K)",
    "689": "NFS Write I/O count: [16K,32K)",
    "690": "NFS Write I/O count: [32K,64K)",
    "691": "NFS Write I/O count: [64K,128K)",
    "692": "NFS Write I/O count: [128K,256K)",
    "693": "NFS Write I/O count: [256K,+∞)",
    "703": "Total NFS Bandwidth (KB/s)",#NEW
    "706": "Total CIFS Bandwidth (KB/s)",#NEW
    "709": "NFS Read Bandwidth (KB/s)",#NEW
    "712": "CIFS Read Bandwidth (KB/s)",#NEW
    "715": "NFS Write Bandwidth (KB/s)",#NEW
    "718": "CIFS Write Bandwidth (KB/s)",#NEW
    "721": "Total NFS OPS",#NEW
    "724": "Total CIFS OPS",#NEW
    "727": "Total NFS Read OPS",#NEW
    "730": "Total CIFS read OPS",#NEW
    "733": "Total NFS write OPS",#NEW
    "736": "Total CIFS Write OPS",#NEW
    "739": "Other NFS OPS",#NEW
    "742": "Other CIFS OPS",#NEW
    "745": "Avg. Response Time of NFS I/Os(us)",#NEW
    "748": "Avg. Response Time of CIFS I/Os(us)",#NEW
    "751": "Avg. Response Time of NFS Read I/Os(us)",#NEW
    "754": "Avg. Response Time of CIFS Read I/Os(us)",#NEW
    "757": "Avg. Response Time of NFS Write I/Os(us)",#NEW
    "760": "Avg. Response Time of CIFS Write I/Os(us)",#NEW
    "763": "Avg. Response Time of Other NFS I/Os(us)",#NEW
    "766": "Avg. Response Time of Other CIFS I/Os(us)",#NEW
    "770": "File Read Bandwidth (KB/s)",#NEW
    "771": "File Write Bandwidth (KB/s)",#NEW
    "802": "Max. Read I/O Size (KB)",#NEW
    "803": "Max. Write I/O Size (KB)",#NEW
    "804": "Max. I/O Size (KB)",#NEW
    "807": "Avg. Back-End Response Time (us)",#NEW
    "808": "Average usage of member disks(%)",#Avg. Member Disk Usage (%)
    "1054": "Synchronization Duration (s)",
    "1055": "Cache page utilization (%)",
    "1056": "Cache chunk utilization (%)",
    "1057": "Cache pageUnit utilization (%)",
    "1059": "The cache page preservation",
    "1060": "The cache chunk preservation",
    "1061": "S3 Head Number",
    "1062": "S3 Head Failed Number",
    "1063": "S3 Head Failed Number(client's cause)",
    "1064": "S3 Post Number",
    "1065": "S3 Post Failed Number",
    "1066": "S3 Post Failed Number(client's cause)",
    "1067": "Swift Head Number",
    "1068": "Swift Head Failed Number",
    "1069": "Swift Head Failed Number(client's cause)",
    "1070": "Swift Post Number",
    "1071": "Swift Post Failed Number",
    "1072": "Swift Post Failed Number(client's cause)",
    "1073": "ISCSI IOPS(IO/s)",
    "1074": "CIFS operation count per second",
    "1075": "Disk Max. Usage(%)",
    "1076": "Total Disk IOPS(IO/s)",
    "1077": "Read Disk IOPS(IO/s)",
    "1078": "Write Disk IOPS(IO/s)",
    "1079": "SCSI IOPS(IO/s)",
    "1090": "Data Reduction Ratio",
    "1091": "Deduplication Ratio",
    "1092": "Compression Ratio",
    "1093": "Overall Space Saving Ratio",
    "1094": "Thin LUN Space Saving Rate (%)",
    "1139": "Avg. Read I/O Link Transmission Latency(us)",#NEW
    "1140": "Avg. Write I/O Link Transmission Latency(us)",#NEW
    "1141": "CIFS Tree Quantity",#NEW
    "1142": "CIFS Session Quantity",#NEW
    "1143": "NFS Connection Quantity",#NEW
    "1154": "Unmap Command Bandwidth (MB/s)",#NEW
    "1155": "Unmap Command IOPS (IO/s)",#NEW
    "1156": "Avg. Unmap Command Size (KB)",#NEW
    "1157": "Avg. Unmap Command Response Time (us)",#NEW
    "1158": "WRITE SAME Command Bandwidth (MB/s)",#NEW
    "1159": "WRITE SAME Command IOPS (IO/s)",#NEW
    "1160": "Avg. WRITE SAME Command Size (KB)",#NEW
    "1161": "Avg. WRITE SAME Command Response Time (us)",#NEW
    "1162": "Full Copy Read Request Bandwidth (MB/s)",#NEW
    "1163": "Full Copy Read Request IOPS (IO/s)",#NEW
    "1164": "Avg. Full Copy Read Request Size (KB)",#NEW
    "1165": "Avg. Full Copy Read Request Response Time (us)",#NEW
    "1166": "Full Copy Write Request Bandwidth (MB/s)",#NEW
    "1167": "Full Copy Write Request IOPS (IO/s)",#NEW
    "1168": "Avg. Full Copy Write Request Size (KB)",#NEW
    "1169": "Avg. Full Copy Write Request Response Time (us)",#NEW
    "1170": "ODX Read Request Bandwidth (MB/s)",#NEW
    "1171": "ODX Read Request IOPS (IO/s)",#NEW
    "1172": "Avg. ODX Read Request Size (KB)",#NEW
    "1173": "Avg. ODX Read Request Response Time (us)",#NEW
    "1174": "ODX Write Request Bandwidth (MB/s)",#NEW
    "1175": "ODX Write Request IOPS (IO/s)",#NEW
    "1176": "Avg. ODX Write Request Size (KB)",#NEW
    "1177": "Avg. ODX Write Request Response Time (us)",#NEW
    "1178": "ODX Write Zero Request Bandwidth (MB/s)",#NEW
    "1179": "ODX Write Zero Request IOPS (IO/s)",#NEW
    "1180": "Avg. ODX Write Zero Request Size (KB)",#NEW
    "1181": "Avg. ODX Write Zero Request Response Time (us)",#NEW
    "1182": "Read I/O Granularity Distribution: [0K,4K)(%)",#NEW
    "1183": "Read I/O Granularity Distribution: [128K,+∞)(%)",#NEW
    "1184": "Write I/O Granularity Distribution: [0K,4K)(%)",#NEW
    "1185": "Write I/O Granularity Distribution: [128K,+∞)(%)",#NEW
    "1188": "VAAI Bandwidth (MB/s)",#NEW
    "1189": "VAAI IOPS (IO/s)",#NEW
    "1190": "Avg. VAAI Size (KB)",#NEW
    "1191": "Avg. VAAI Response Time (us)",#NEW
    "1192": "DR Read Request Bandwidth (MB/s)",#NEW
    "1193": "DR Read Request IOPS (IO/s)",#NEW
    "1194": "Avg. DR Read Request Size (KB)",#NEW
    "1195": "Avg. DR Read Request Response Time (us)",#NEW
    "1196": "DR Write Request Bandwidth (MB/s)",#NEW
    "1197": "DR Write Request IOPS (IO/s)",#NEW
    "1198": "Avg. DR Write Request Size (KB)",#NEW
    "1199": "Avg. DR Write Request Response Time (us)",#NEW
    "1200": "OBS Storage total bandwidth (KB/s)",#NEW
    "1201": "OBS Storage read bamdwidth (KB/s)",#NEW
    "1202": "OBS Storage write bamdwidth (KB/s)",#NEW
    "1211": "Normalized Latency (us)",#NEW
    "1233": "I/O Sequentiality(%)",#NEW
    "1234": "Read SmartCache Hit Ratio (%)",#NEW
    "1243": "Full Copy Command Bandwidth (MB/s)",#NEW
    "1244": "Full Copy Command IOPS (IO/s)",#NEW
    "1245": "Avg. Full Copy Command Size (KB)",#NEW
    "1246": "Avg. Full Copy Command Response Time (us)",#NEW
    "1247": "ODX Command Bandwidth (MB/s)",#NEW
    "1248": "ODX Command IOPS (IO/s)",#NEW
    "1249": "Avg. ODX Command Size (KB)",#NEW
    "1250": "Avg. ODX Command Response Time (us)",#NEW
    "1251": "Total Block IOPS(IO/s)",#NEW
    "1252": "Total Block Bandwidth (MB/s)",#NEW
    "1263": "Other DataTurbo OPS",#NEW
    "1264": "Average response time of other DataTurbo I/Os(us)",#NEW
    "1265": "Total DataTurbo Bandwidth (KB/s)",#NEW
    "1266": "DataTurbo Read Bandwidth (KB/s)",#NEW
    "1267": "DataTurbo Write Bandwidth (KB/s)",#NEW
    "1268": "Total DataTurbo OPS",#NEW
    "1269": "Total DataTurbo Read OPS",#NEW
    "1270": "Total DataTurbo write OPS",#NEW
    "1271": "Average DataTurbo I/O response time(us)",#NEW
    "1272": "Average DataTurbo read I/O response time(us)",#NEW
    "1273": "Average DataTurbo write I/O response time(us)",#NEW
    "1277": "Background Copy Bandwidth (KB/s)",#NEW
    "1299": "KV CPU Usage (%)",#NEW
    "1303": "RX Packets",#NEW
    "1304": "TX Packets",#NEW
    "1305": "RX Bandwidth (KB/s)",#NEW
    "1306": "TX Bandwidth (KB/s)",#NEW
    "1307": "Query Request Frequency (per Second)",#NEW
    "1308": "Average Query Request Queue Duration (ms)",#NEW
    "1309": "Average Query Request Duration (ms)",#NEW
    "1310": "Maximum Query Request Duration (ms)",#NEW
    "1311": "Maximum Query Request Queue Duration (ms)",#NEW
    "1312": "Configuration Request Frequency (per Second)",#NEW
    "1313": "Average Configuration Request Queue Duration (ms)",#NEW
    "1314": "Average Configuration Request Duration (ms)",#NEW
    "1315": "Maximum Configuration Request Duration (ms)",#NEW
    "1316": "Maximum Configuration Request Queue Duration (ms)",#NEW
    "1317": "DR Request Bandwidth (MB/s)",#NEW
    "1318": "DR Request IOPS (IO/s)",#NEW
    "1319": "Avg. DR Request Response Time (us)",#NEW
    "1324": "Normalized Read IOPS (IO/s)",#NEW
    "1325": "Normalized Write IOPS (IO/s)",#NEW
    "1332": "Post-Process Deduplication Read Bandwidth(MB/s)",#NEW
    "1333": "Post-Process Deduplication Write Bandwidth(MB/s)",#NEW
    "1334": "Post-Process Deduplication Fingerprint Read Bandwidth(MB/s)",#NEW
    "1335": "Post-Process Deduplication Fingerprint Write Bandwidth(MB/s)",#NEW
    "1336": "NAS Migration Copy Bandwidth (KB/s)",#NEW
    "1337": "Post-Process Deduplication and Reduction Read Bandwidth(MB/s)",#NEW
    "1338": "Post-Process Deduplication and Reduction Write Bandwidth(MB/s)",#NEW
    "1633": "Avg. Corrected CPU usage (%)",#NEW
    "1298": "Back-End Partition CPU Usage (%)",#NEW
    "1297": "Front-End Partition CPU Usage (%)",#NEW
    "1296": "Network Partition CPU Usage (%)",#NEW
    "30001": "NFS read bandwidth (KB/s)",#NEW
    "30002": "NFS write bandwidth (KB/s)",#NEW
    "30003": "NFS Total bandwidth (KB/s)",#NEW
    "30004": "NFS read OPS",#NEW
    "30005": "NFS write OPS",#NEW
    "30006": "NFS total OPS",#NEW
    "30008": "NFS connected client Number",#NEW
    "30013": "NFS write OPS average response time (us)",#NEW
    "30015": "NFS read OPS average response time (us)",#NEW
    "30043": "DPC read bandwidth (MB/s)",#NEW
    "30044": "DPC write bandwidth (MB/s)",#NEW
    "30045": "DPC read OPS",#NEW
    "30046": "DPC write OPS",#NEW
    "30051": "DPC total bandwidth (MB/s)",#NEW
    "30052": "DPC Total OPS",#NEW
    "30053": "CIFS read bandwidth (KB/s)",#NEW
    "30054": "CIFS write bandwidth (KB/s)",#NEW
    "30055": "CIFS total bandwidth (KB/s)",#NEW
    "30056": "CIFS read OPS",#NEW
    "30057": "CIFS write OPS",#NEW
    "30058": "CIFS total OPS",#NEW
    "50001": "OBS read bandwidth (KB/s)",#NEW
    "50002": "OBS write bandwidth (KB/s)",#NEW
    "50003": "OBS total bandwidth (KB/s)",#NEW
    "50004": "OBS read OPS",#NEW
    "50005": "OBS write OPS",#NEW
    "50006": "OBS total OPS",#NEW
    "60002": "Read/write requests to the source LUN",
    "60003": "Read/write requests to the snapshot pool",
    "90001": "Total capacity (MB)",
    "90002": "Used capacity (MB)",
    "90003": "Free capacity (MB)",
    "90004": "Capacity usage (%)",
    "90005": "Allocated capacity (MB)",
    "90006": "Free capacity ratio (%)",
    "90016": "Space Hard Quota(MB)",
    "90017": "Space Soft Quota(MB)",
    "90018": "Used Space Quota(MB)",
    "90019": "File Quantity Hard Quota",
    "90020": "File Quantity Soft Quota",
    "90021": "Used File Quantity Quota",
}

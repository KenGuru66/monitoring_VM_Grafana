# -*- coding: utf-8 -*-
RESOURCE_NAME_DICT = {
    "10": "Disk",
    "11": "LUN",
    "14": "Host Group",
    "21": "Host",
    "27": "Snapshot LUN",
    "40": "File System",
    "201": "Array",
    "207": "Controller",
    "212": "FC Port",
    "213": "Ethernet Port",
    "214": "Back-End Port",#SAS Port
    "216": "Storage Pool",
    "218": "SmartCache Pool",
    "219": "LUN Copy",
    "221": "Remote Replication Consistent Group",
    "223": "FC Initiator",
    "224": "Remote Device",
    "225": "FC Replication Link",
    "230": "SmartQoS",#IO Class
    "235": "Bond Port",
    "237": "Cache",
    "243": "iSCSI Replication Link",
    "252": "FCoE Port",
    "253": "SmartMigration",
    "256": "Lun Group",
    "263": "Remote Replication",#Remote Replication Pair
    "266": "Disk Domain",
    "268": "SmartPartition",
    "272": "LUN Priority",
    "273": "SmartCache Partition",
    "279": "Logical Port",
    "303": "Heterogeneous FC Link",#eFC_LINK
    "304": "Heterogeneous iSCSI Link",#eISCSI_LINK
    "404": "Remote eISCSI Link",
    "659": "DataTurbo Controller",
    "1000": "Controller NFSV3",
    "1001": "Controller NFSV4",
    "1002": "Controller SMB1",
    "1003": "Controller SMB2/3",
    "16384": "Cluster",
    "16385": "Node",
    "16390": "Client",
    "16400": "Directory",
    "16401": "NFS Share",
    "16402": "CIFS Share",
    "16452": "UNKNOWN_RESOURCE_16452",  # Найден в Perf_3000v6_NFSv3.zip (2025-10-29)
    "16453": "UNKNOWN_RESOURCE_16453",  # Найден в Perf_3000v6_NFSv3.zip (2025-10-29)
    "16458": "Quota Tree",
    "16500": "IB Port",
    "20486": "IP Replication Link",
    "57636": "Controller NFSV4.1",
    "57791": "RAID",
    "57867": "ETH_EXP_Port",
    "57890": "ETH Expansion Port",  # Ethernet расширенные порты CTE0 (2025-10-29)
    # ============================================================================
    # 📄 Ресурсы из PDF документации (обновлено 2025-12-02)
    # ============================================================================
    # Источник: OceanStor Dorado V700R001C10 REST Interface Reference.pdf
    # Извлечено из Appendix: Performance Indicators (раздел 4.3.5 Protocol)
    # 
    # ВАЖНО: Названия извлечены из заголовков столбцов таблиц Performance Indicators
    # Строка с названиями ресурсов находится НАД строкой Type с ID
    "824": "SmartMove FsPair",  # 📄 PDF: SmartMoveFsPair (раздел Data Protection)
    "1006": "SmartMove",  # 📄 PDF: SmartMove (раздел Data Protection)
    "1053": "Controller S3",  # 📄 PDF: ControllerS3 (раздел Protocol) - Amazon S3 протокол!
    "11110": "LUN Clone",  # 📄 PDF: lun clone (раздел Data Protection)
    "11111": "LUN Clone Group",  # 📄 PDF: lun clonegroup (раздел Data Protection)
}
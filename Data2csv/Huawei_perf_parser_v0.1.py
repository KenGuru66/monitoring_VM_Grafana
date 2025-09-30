""" script for parsing Huawei performance data
    adopted to python3 refactored and improved by Alexey Opolchenov, edited by Sergey Terekhin
"""

import inspect
import logging
from pathlib import Path
from METRIC_DICT import METRIC_NAME_DICT
from RESOURCE_DICT import RESOURCE_NAME_DICT


import re
import os
import struct
from datetime import datetime
from datetime import timedelta
import tarfile
import time
import zipfile
import shutil

import click
import pandas as pd
import tqdm

LOGDIR = 'log'
LOGFILE = 'process_perf_files.log'
LOGFILE_REPEAT = 'process_perf_files_repeat.log'
if not (Path() / LOGDIR).is_dir():
    (Path() / LOGDIR).mkdir()
logging.root.handlers = []
logging.basicConfig(
    format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    # handlers=[],
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)
log_repeat = logging.getLogger("repeat")

log_format = logging.Formatter("[%(asctime)s][%(levelname)s] %(message)s")
log_handler = logging.FileHandler(f"{LOGDIR}/{LOGFILE}", mode="a", encoding="utf-8")
log_repeat_handler = logging.FileHandler(f"{LOGDIR}/{LOGFILE_REPEAT}", mode="a", encoding="utf-8")

log_handler.setFormatter(log_format)
log_repeat_handler.setFormatter(log_format)

logger.handlers.clear()
logger.addHandler(log_handler)
log_repeat.handlers.clear()
log_repeat.addHandler(log_repeat_handler)

# Try to import influxdb (optional dependency)
try:
    from influxdb import DataFrameClient
    INFLUXDB_AVAILABLE = True
except ImportError:
    INFLUXDB_AVAILABLE = False
    logger.warning("influxdb module not available, --to_db option will not work")

# default parse such objects:
# LUN(11)
# Controller(207)
# Host(21)
# FrontPort:FC Port(212),bond port(235),Ethernet Port(213),LIF(279),IB_Port(16500)
#DEFAULT_RESOURCES = ["11", "207", "21", "212", "235", "213", "279", "16500"]
DEFAULT_RESOURCES = [
    "207", #"Controller"
    "212", #"FC Port"
    "225", #"FC Replication Link"
    "216",  #Storage Pool
    "266", #"Disk Domain"
    "10", #Disk
    "11", #LUN
    "21" # "Host"
]
# default parse such data types:
# Band:Read bandwidth(23),Write bandwidth(26),Block Bandwidth(21)
# IOPS:Read IOPS(25),Write IOPS(28),Total IOPS(22)
# response time:Avg. read I/O response timems:197),Avg. write I/O response time(ms:198),Avg. I/O response time(ms:78)
# Usage(18), Avg. Member Disk Usage (%)(808),"1075": "Disk Max. Usage(%)",,"370": "Avg. I/O Response Time (us)"
# DEFAULT_METRICS = ["23", "26", "21", "25", "28", "22", "197", "198", "78", "18"]
#DEFAULT_METRICS = [
#    "18", "19", "21", "22", "23", "24", "25", "26", "27", "28", "29", "67", "68", "69", "78",  "79", "120", "197", "198",
#    "110", "120", "218", "333", "384", "385"
#]


DEFAULT_METRICS = [
    "18", #Usage
    "22", # "Total IOPS (IO/s)"
    "25", #"Read IOPS (IO/s)"
    "28", #"Write IOPS (IO/s)"
    "23", #"Read bandwidth (MB/s)"
    "26", #"Write bandwidth (MB/s)"
    "1079", #"SCSI IOPS(IO/s)"
    "1073", #"ISCSI IOPS(IO/s)"
    "627", #"NFS operation count per second"
    "1074", #"CIFS operation count per second"
    "240", #"Average queue depth"
    "1158", #"WRITE SAME Command Bandwidth (MB/s)"
    "1154", #"Unmap Command Bandwidth (MB/s)"
    "1162", #"Full Copy Read Request Bandwidth (MB/s)"
    "1166", #"Full Copy Write Request Bandwidth (MB/s)"
    "1170", #"ODX Read Request Bandwidth (MB/s)"
    "1174", #"ODX Write Request Bandwidth (MB/s)
    "1332", #"Post-Process Deduplication Read Bandwidth(MB/s)",#NEW
    "1333", #"Post-Process Deduplication Write Bandwidth(MB/s)",#NEW
    "1334", #"Post-Process Deduplication Fingerprint Read Bandwidth(MB/s)",#NEW
    "1335", #"Post-Process Deduplication Fingerprint Write Bandwidth(MB/s)",#NEW
    "1337", #"Post-Process Deduplication and Reduction Read Bandwidth(MB/s)",#NEW
    "1338", #"Post-Process Deduplication and Reduction Write Bandwidth(MB/s)",#NEW
    "1633", #"Avg. Corrected CPU usage (%)",#NEW
    "260", #"Back-End traffic (MB/s)",
    "261", #"Back-end read traffic (MB/s)",
    "262", #"Back-end write traffic (MB/s)",
    "1298", #"Back-End Partition CPU Usage (%)",#NEW
    "1297", #"Front-End Partition CPU Usage (%)",#NEW
    "68", #Avg. CPU usage (%)
    "1299", #KV CPU Usage (%)
    "1182", #"Read I/O Granularity Distribution: [0K,4K)(%)",#NEW
    "33", #"Read I/O granularity distribution: [4K,8K) (%)",
    "34", #"Read I/O granularity distribution: [8K,16K) (%)",
    "35", #"Read I/O granularity distribution: [16K,32K) (%)",
    "36", #"Read I/O granularity distribution: [32K,64K) (%)",
    "37", #"Read I/O granularity distribution: [64K,128K) (%)",
    "1183", #"Read I/O Granularity Distribution: [128K,+∞)(%)",#NEW
    "1184", #"Write I/O Granularity Distribution: [0K,4K)(%)",#NEW
    "44", #"Write I/O granularity distribution: [4K,8K) (%)",
    "45", #"Write I/O granularity distribution: [8K,16K) (%)",
    "46", #"Write I/O granularity distribution: [16K,32K) (%)",
    "47", #"Write I/O granularity distribution: [32K,64K) (%)",
    "48", #"Write I/O granularity distribution: [64K,128K) (%)",
    "1185", #"Write I/O Granularity Distribution: [128K,+∞)(%)",#NEW
    "1188", #"VAAI Bandwidth (MB/s)",#NEW
    "93", #"Read cache hit ratio (%)"
    "95", #"Write cache hit ratio (%)"
    "333", #"Cache water (%)"
    "384", #"Avg. Read I/O Response Time(us)",
    "385", #"Avg. Write I/O Response Time(us)",
    "24", #"Avg. read I/O size (KB)",
    "27", #"Avg. write I/O size (KB)"
    "228", #Avg. I/O size (KB)
    "369", #"Service Time(us)"
    "808", #Avg. Member Disk Usage (%)
    "812", #Transmitting Bandwidth for replication(KB/s) 
    "813", #Receiving Bandwidth for replication(KB/s) 
    "1075" #"Disk Max. Usage(%)"
]


# i="InputFilePath"
# o="OutputFilePath"
# l="LogPath"
# d="AutoDelete"
# r="Resources"
# m="Metrics"


# -----------------------------------------------------------------------------
def construct_data_header(result):
    """ construct data header
        {
            'EndTime': '1664312940', 'StartTime': '1664312040', 'Archive': '60',
            'CtrlID': '1129',
            'Map': [{
                'ObjectTypes': '10',
                'IDs': ['134234114', '134234112', ...],
                'Names': ['DAE010.2', 'DAE010.0', ...],
                'DataTypes': ['5', '18', ...]
            }]
        }
    """
    data_header = {}
    if result:
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
        result = re.findall(
            '"([0-9]+)":{"IDs":\\[(("[0-9a-zA-Z]+",?)+)\\],'
            '"Names":\\[(("[.0-9A-Za-z$ \\[\\]\\(\\):_-]*",?)+)\\],'
            '"DataTypes":\\[(([0-9]+,?)+)\\]}',
            map_content
        )
        if result:
            for each_result in result:
                object_type = {}
                object_type['ObjectTypes'] = each_result[0]
                object_type['IDs'] = each_result[1].replace('"', '').split(',')
                object_type['Names'] = each_result[3].replace('"', '').split(',')
                object_type['DataTypes'] = each_result[5].replace('"', '').split(',')
                data_header['Map'].append(object_type)
    return data_header


# -----------------------------------------------------------------------------
def construct_data_type(data_header):
    """ construct data type
        ['10', '5', 'DAE010.2', []]
    """
    list_data_type = []
    size_collect_once = 0
    if 'Map' in data_header:
        for resource_type in data_header['Map']:
            size_collect_once += (
                len(resource_type['IDs']) *
                len(resource_type['DataTypes']) * 4
            )
            for index_ids, _ in enumerate(resource_type['IDs']):
                for index_data_type in resource_type['DataTypes']:
                    list_index = [
                        resource_type['ObjectTypes'],
                        index_data_type,
                        resource_type['Names'][index_ids], []
                    ]
                    list_data_type.append(list_index)

    return list_data_type, size_collect_once


# -----------------------------------------------------------------------------
def process_perf_file(file_path, output_csv_file_path, resources, metrics, to_db=False):
    """ read binary perf file
    """
    log_repeat.info("Start to process file->%s", file_path)

    if to_db:
        if not INFLUXDB_AVAILABLE:
            logger.error("Cannot use --to_db option: influxdb module is not available")
            return False
        client = DataFrameClient(
            host='localhost', port=8428,
        )

    with open(file_path, "rb") as fin:
        bit_correct = fin.read(32)
        bit_msg_version = fin.read(4)
        bit_equip_sn = fin.read(256).decode('utf-8')
        bit_equip_name = fin.read(41).decode('utf-8')
        bit_equip_data_length = fin.read(4)

        log_repeat.info("bit_equip_sn = %s", bit_equip_sn.replace('\x00', ''))
        log_repeat.info("bit_equip_name = %s", bit_equip_name.replace('\x00', ''))

        process_finish_flag = False

        bit_map_type = fin.read(4)
        bit_map_length, = struct.unpack("<l", fin.read(4))
        bit_map_value = fin.read(bit_map_length - 8)
        if len(bit_map_value) < bit_map_length - 8:
            log_repeat.error("Read Data Header Failed, Maybe File Is Not Complete!")
            return False

        with open(output_csv_file_path, 'a', encoding="utf-8") as fout_csv:
            try:
                while not process_finish_flag:

                    # log_repeat.info("process data head")
                    result = re.match(
                        '{(.*),"Map":{(.*)}}', bit_map_value.decode('utf-8')
                    )
                    data_header = construct_data_header(result)
                    list_data_type, size_collect_once = construct_data_type(data_header)

                    log_repeat.info("DataTypes count: %d ", (size_collect_once/4))

                    times_collcet = int(
                        (int(data_header['EndTime'])-int(data_header['StartTime']))/
                        int(data_header['Archive'])
                    )

                    title_row = "ObjectType,IDs,Names,DataTypes,"
                    for i in range(times_collcet):
                        title_row += "C_%03d," % (i + 1)
                        buffer_read = fin.read(size_collect_once)
                        if len(buffer_read) < size_collect_once:
                            log_repeat.error("Data Content may be not enough!")
                            process_finish_flag = True
                        for index_in_buffer in range(0, size_collect_once, 4):
                            bytes_read_4 = buffer_read[index_in_buffer: index_in_buffer + 4]
                            bytes_read_int, = struct.unpack("<l", bytes_read_4)
                            list_data_type[int(index_in_buffer / 4)][3].append(str(bytes_read_int))
                            index_in_buffer += 4

                    start_time = time.strftime(
                        '%Y-%m-%d %H:%M:%S',
                        time.localtime(int(data_header['StartTime']))
                    )
                    end_time = time.strftime(
                        '%Y-%m-%d %H:%M:%S',
                        time.localtime(int(data_header['EndTime']))
                    )
                    str_to_csv = "SN,Name,CtrlID,Archive,StartTime,EndTime,Periods\n"
                    str_to_csv += (
                        f'{bit_equip_sn};{bit_equip_name};{data_header["CtrlID"]};'
                        f'{data_header["Archive"]};{start_time};{end_time};{str(times_collcet)}\n'
                    )

                    start_time = datetime.fromtimestamp(int(data_header['StartTime']))
                    next_time = start_time
                    time_list = []
                    for i, _ in enumerate(list_data_type[0][3]):
                        time_list.append(next_time)
                        next_time += timedelta(seconds=int(data_header['Archive']))

                    for i, data_type in enumerate(list_data_type):
                        if not is_resource_and_datatype_needed(
                            resource_id=data_type[0], metric_id=data_type[1],
                            resources=resources, metrics=metrics,
                        ):
                            # logger.info("Continue! %s, %s", data_type[0], data_type[1])
                            continue
                        # logger.info("Not continue! %s, %s", data_type[0], data_type[1])

                        str_to_csv = ""
                        str_to_csv += RESOURCE_NAME_DICT.get(str(data_type[0])) + ';'
                        str_to_csv += METRIC_NAME_DICT.get(str(data_type[1])) + ';'
                        str_to_csv += data_type[2] + ';'
                        for index, point_value in enumerate(data_type[3]):
                            # logger.info("Inside index %s", index)
                            time_string = time_list[index].strftime("%Y-%m-%dT%H:%M:%SZ")
                            time_qqq = time.mktime(time_list[index].timetuple())
                            fout_csv.write(
                                f'{str_to_csv}{point_value};{time_string};{time_qqq}\n'
                            )
                            if to_db:
                                meas = rename_metric(METRIC_NAME_DICT.get(str(data_type[1])))
                                resource = rename_metric(RESOURCE_NAME_DICT.get(str(data_type[0])), add_prefix=False)
                                # logger.info   (f"ingest {resource} {meas}")
                                # ingest
                                json_body = pd.DataFrame([{
                                    "Resource": resource.strip(),
                                    "Element": data_type[2].strip(),
                                    "SN": bit_equip_sn.strip(),
                                    "Name": bit_equip_name.strip(),
                                    "CtrlID": data_header["CtrlID"].strip(),
                                    "Archive": data_header["Archive"].strip(),
                                    "time": start_time,
                                    "variable": point_value,
                                }]).set_index("time")

                                tag_columns = ["Resource", "Element", "SN", "Name", "CtrlID", "Archive"]
                                client.write_points(
                                    json_body,
                                    # dataframe=dataframe,
                                    measurement=meas,
                                    protocol='line',
                                    tag_columns=tag_columns,
                                )

                    bit_map_type = fin.read(4)
                    # log_repeat.info("bit_map_t%s", bit_map_type)
                    if bit_map_type == '':
                        log_repeat.info("Process Finished!")
                        process_finish_flag = True
                    elif bit_map_type == '\x00\x00\x00\x00':
                        bit_map_length, = struct.unpack("<l", fin.read(4))
                        if bit_map_length < 8:
                            log_repeat.info("bit_map_length less than 8")
                            process_finish_flag = True
                        else:
                            bit_map_value = fin.read(bit_map_length - 8)
                            if len(bit_map_value) < bit_map_length - 8:
                                log_repeat.error(
                                    "Read Data Header Failed, Maybe File Is Not Complete!"
                                )
                                return False
                            else:
                                log_repeat.info("Find Next Data Header, Need Process!")
                    else:
                        process_finish_flag = True
            except Exception as exc_info:
                log_repeat.error(exc_info)
                return False
            # logger.info("str_to_csv:")
            # print (str_to_csv)
        # fp_csv.close()
        # fp.close()
    log_repeat.info("Finish to process file. %s", file_path)
    return True


# -----------------------------------------------------------------------------
# filter the resource and metrics
def is_resource_and_datatype_needed(resource_id, metric_id, resources, metrics):
    return str(resource_id) in resources and str(metric_id) in metrics

# -----------------------------------------------------------------------------
#decompress zip archive
def decompress_zip(zip_path, extract_to=None):
    """
    Извлекает zip архив во временную директорию
    Возвращает путь к директории с извлеченными файлами
    """
    if extract_to is None:
        extract_to = Path("temp_zip_extract")
    else:
        extract_to = Path(extract_to)
    
    if extract_to.exists():
        shutil.rmtree(extract_to)
    extract_to.mkdir(parents=True)
    
    logger.info(f"Extracting zip archive {zip_path} to {extract_to}")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)
    
    logger.info(f"Successfully extracted zip archive to {extract_to}")
    return extract_to

# -----------------------------------------------------------------------------
#decompress file
def decompress_tgz(file_tgz):
    tar = tarfile.open(file_tgz)
    names = tar.getnames()
    temp_file_path = Path("temp")
    if not temp_file_path.is_dir():
        temp_file_path.mkdir()
    if len(names) == 1:
        tar.extract(names[0], temp_file_path)
        return temp_file_path / names[0]
    logger.error("perf file content error, perf file: %s", file_tgz)
    return ""

# -----------------------------------------------------------------------------
def split_files_by_sn(files, prefix=None):
    """
    Группирует файлы по серийному номеру (SN) оборудования.
    
    Args:
        files: Список файлов для обработки
        prefix: Опциональный префикс для фильтрации файлов (например, "PerfData_OceanStorDorado5500V6")
    
    Returns:
        Словарь {serial_number: [список файлов]}
    """
    sn_to_perf_file_list = {}
    for file in files:
        # Логируем имя файла для отладки
        logger.info(f"Processing file: {file.name}")
        
        # Если указан префикс, проверяем, что имя файла начинается с этого префикса
        if prefix and not file.name.startswith(prefix):
            logger.info(f"File {file.name} does not match prefix {prefix}, skipping")
            continue

        # Регулярное выражение для поиска серийного номера и SP
        # Формат: PerfData_MODEL_SN_SERIALNUMBER_SP0_...
        file_sn_matches = re.findall(re.compile(r"_SN_([0-9A-Z]+)_SP\d+"), file.name)
        
        if not file_sn_matches:
            # Если совпадения не найдены, выводим предупреждение и пропускаем файл
            logger.warning(f"Could not extract serial number from file name: {file.name}")
            continue
        
        file_sn = file_sn_matches[0]
        if file_sn not in sn_to_perf_file_list:
            sn_to_perf_file_list[file_sn] = []
        sn_to_perf_file_list[file_sn].append(file)
    
    return sn_to_perf_file_list
# -----------------------------------------------------------------------------
def get_model_from_perf_file_name(file):
    return re.findall(re.compile(r"PerfData_(.+?)_SN"), file.name)[0]

'''
与内置资源类型对比，
如果全部存在于内置资源表，返回None
否则返回第一个不存在于内置资源表的资源
'''
# -----------------------------------------------------------------------------
def find_first_invalid_resource(resources):
    for r in resources:
        if r not in RESOURCE_NAME_DICT:
            return r
    return None

'''
与内置资源类型对比，
如果全部存在于内置资源表，返回None
否则返回第一个不存在于内置资源表的资源
'''
# -----------------------------------------------------------------------------
def find_first_invalid_metric(metrics):
    for m in metrics:
        if m not in METRIC_NAME_DICT:
            return m
    return None


# -----------------------------------------------------------------------------
def rename_metric(metric, add_prefix=True):
    if add_prefix:
        res = "hu_"
    else:
        res = ""
    return (
        res + metric.lower().replace(" ", "_")
        .replace("io/s", "iops")
        .replace("i/os", "io")
        .replace("/", "p")
        .replace("(", "").replace(")", "")
        .replace("[", "").replace("]", "")
        .replace(".", "").replace(",", "")
        .replace(":", "")
        .replace("%", "pct")
    )


# -----------------------------------------------------------------------------
def process_perf_file_tgz_dir(input_path, output_path, is_delete_after_parse, resources, metrics, to_db=False, prefix=None):
    logger.info("%s: start processing  %s", inspect.stack()[0][3], input_path)
    input_path = Path(input_path)
    output_path = Path(output_path)
    
    # Проверяем, является ли входной путь zip файлом
    temp_extract_dir = None
    original_input_path = input_path
    
    if input_path.is_file() and input_path.suffix.lower() == '.zip':
        logger.info("Input is a zip archive, extracting...")
        temp_extract_dir = decompress_zip(input_path)
        input_path = temp_extract_dir
        logger.info(f"Working with extracted directory: {input_path}")
    elif not input_path.is_dir():
        logger.error("%s is not a valid path or zip file!", input_path)
        return

    # Рекурсивный поиск всех .tgz файлов
    files = list(input_path.rglob("*.tgz"))
    if len(files) == 0:
        logger.warning("There are no perf files yet in %s", input_path)
        if temp_extract_dir and temp_extract_dir.exists():
            logger.info(f"Cleaning up temporary directory {temp_extract_dir}")
            shutil.rmtree(temp_extract_dir)
        return

    logger.info(f"Found {len(files)} .tgz files")
    
    sn_to_perf_file_list = split_files_by_sn(files, prefix=prefix)

    for serial, sn_files in sn_to_perf_file_list.items():
        logger.info("Processing array %s", serial)
        sn_files.sort()

        output_csv_file_name = f'{serial}.csv'
        output_csv_file_path = output_path / output_csv_file_name

        logger.info(f"Writing to CSV: {output_csv_file_path}")
        try:
            for file in sn_files:
                logger.info(f"Processing file {file}")
                decompressed_file_path = decompress_tgz(file)
                is_process_successful = process_perf_file(
                    file_path=decompressed_file_path,
                    output_csv_file_path=output_csv_file_path,
                    resources=resources,
                    metrics=metrics,
                    to_db=to_db,
                )
                
                decompressed_file_path.unlink()
                if not is_process_successful:
                    logger.error(f"Failed to process file {file}")
                    continue

                # Если мы работаем с zip архивом, не перемещаем файлы
                if not temp_extract_dir:
                    if is_delete_after_parse:
                        file.unlink()
                    else:
                        parsed_files_path = original_input_path / "parsed_files"
                        if not parsed_files_path.is_dir():
                            parsed_files_path.mkdir()
                        file.replace(parsed_files_path / file.name)
                    
            logger.info(f"Finished writing to {output_csv_file_path}")
        except Exception as e:
            logger.error(f"Error writing to {output_csv_file_path}: {str(e)}")
    
    # Очистка временной директории после обработки zip архива
    if temp_extract_dir and temp_extract_dir.exists():
        logger.info(f"Cleaning up temporary directory {temp_extract_dir}")
        shutil.rmtree(temp_extract_dir)
# -----------------------------------------------------------------------------
def check_resource_existance(resources):
    """ Resource existence
    """
    first_invalid_resource = find_first_invalid_resource(resources)
    if first_invalid_resource:
        logger.error("invalid resource type:%s", find_first_invalid_resource)
        return False
    return True

# -----------------------------------------------------------------------------
def check_metric_existance(metrics):
    """ Metric existence
    """
    first_invalid_metric = find_first_invalid_metric(metrics)
    if first_invalid_metric:
        logger.error("invalid metric type: %s", first_invalid_metric)
        return False
    return True

# -----------------------------------------------------------------------------
def make_dirs(log_path, output_path):
    """ make output folders is not exists
    """
    if not log_path.is_dir():
        log_path.mkdir(parents=True)
    if not output_path.is_dir():
        output_path.mkdir(parents=True)


# def usage(argv0):
#     print ("Usage:")
#     print ("  python %s -i %s -o %s -r %s -m %s -l %s -d %s" % (argv0,i,o,r,m,l,d))
#     print ("\n")
#     print ("Argument introduction:")
#     print ("  %s:\t%s" %(i,"The path where performance files exported(Mandatory)"))
#     print ("\n")
#     print ("  %s:\t%s" %(o,"The path where parsed csv files write(Mandatory)"))
#     print ("\n")
#     print ("  %s:\t\t%s" %(l,'''The path where log files write(Optional,)
#                         current path default)'''))
#     print ("\n")
#     print ("  %s:\t\t%s" %(d,'''Whether delete source performance files)
#                         after parsed.(Optional, default is FALSE)'''))
#     print ("    \t\t\t%s"% "Y/YES/TRUE means delete after parsed")
#     print ("    \t\t\t%s"% "N/NO/FALSE means do not delete after parsed")
#     print ("\n")
#     print ("  %s:\t\t%s" %(r,'''Resource types you want to collect(Optional)
#                         Separated by comma.For example:-r 207,11
#                         Default is
#                         11:LUN,
#                         207:Controller,
#                         21:Host,
#                         212:FC Port,
#                         213:Ethernet Port,
#                         235:Bond Port,
#                         279:Logical Port,
#                         16500:IB Port'''))
#     print ("\n")
#     print ("  %s:\t\t%s" %(m,'''Metric types you want to collect(Optional)
#                         Separated by comma.For example:-m 25,26;
#                         Default is 23:Read bandwidth (MB/s),
#                         26:Write bandwidth (MB/s),
#                         21:Block bandwidth (MB/s),
#                         25:Read IOPS (IO/s),
#                         28:Write IOPS (IO/s),
#                         22:Total IOPS (IO/s),
#                         197:Avg. read I/O response time (ms),
#                         198:Avg. write I/O response time (ms),
#                         78:Avg. I/O response time (ms),
#                         18:Usage (%)'''))


# -----------------------------------------------------------------------------
@click.command()
@click.option("-i", "--input_path", type=click.Path(exists=True), required=True, help='Path to directory with .tgz files or a .zip archive')
@click.option("-o", "--output_path", type=click.Path(), required=True, help='Path to output directory for CSV files')
@click.option("-l", "--log_path", type=click.Path(), default='log', help='Path to log directory')
@click.option("-d", "--is_delete_after_parse", is_flag=True, default=False, help='Delete source files after parsing')
@click.option("-r", "--resources", multiple=True, default=DEFAULT_RESOURCES, help='Resource types to collect (comma-separated)')
@click.option("-m", "--metrics", multiple=True, default=DEFAULT_METRICS, help='Metric types to collect (comma-separated)')
@click.option("-p", "--prefix", type=click.STRING, required=False, default=None, help='Optional: Filter files by name prefix (e.g., "PerfData_OceanStorDorado5500V6"). If not specified, all .tgz files will be processed.')
@click.option("-e", "--ext", type=click.STRING, default="tgz", help='File extension to search for')
@click.option("--to_db", is_flag=True, show_default=True, required=False, default=False, help='Send data to InfluxDB')
def huawei_collect(
    input_path, output_path, log_path, is_delete_after_parse, resources,
    metrics, prefix, ext, to_db
):
    """ process collected data
    """
    # logger.error(1)
    # if not check_resource_existance(resources) or not check_metric_existance(metrics):
    #    return
    #metrics = list(METRIC_NAME_DICT.keys())# - пройтись по всем метрикам в словаре
    #resources = list(RESOURCE_NAME_DICT.keys())# - пройтись по всем ресурсам в словаре

    logger.info("%s: Start", inspect.stack()[0][3])
    make_dirs(Path(log_path), Path(output_path))
    process_perf_file_tgz_dir(
        input_path=input_path,
        output_path=output_path,
        is_delete_after_parse=is_delete_after_parse,
        resources=resources,
        metrics=metrics,
        prefix=prefix,
        to_db=to_db,
    )
    logger.info("%s: done", inspect.stack()[0][3])

    logger.info("Process End!")


# -----------------------------------------------------------------------------
if __name__ == "__main__":
    # logger.error(0)
    huawei_collect()

# logger.error(-1) ЦФЯЫУЧ

# python huawei_pars_v01.py -i /storage/hu/inbox/HistoryPerstat/HistoryPerformanceFile/172.25.18.206/172.25.18.206 \
    # -o /storage/hu/inbox/HistoryPerstat/out/172.25.18.206
#nohup python huawei_pars_v01.py -i /storage/hu/vtb/HS_2024/10.7.39.170/10.7.39.170 -o /storage/hu/vtb/HS_2024/10.7.39.170/res -e tgz -p PerfData_OceanStorDorado8000V6_SN --to_db > progress170.log 2>&1 &
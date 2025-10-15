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

# Импортируем словари из новых файлов
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from METRIC_DICT import METRIC_NAME_DICT as metric_name_dict
from RESOURCE_DICT import RESOURCE_NAME_DICT as resource_name_dict

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
                str_to_csv += resource_name_dict.get(str(list_data_type[i][0])) + ';'
                str_to_csv += metric_name_dict.get(str(list_data_type[i][1])) + ';'
                str_to_csv += list_data_type[i][2] + ';'
                for index in xrange(len(list_data_type[i][3])):
                    point_value = list_data_type[i][3][index]
                    fp_csv.write(('%s%s;%s;%d\n' % (
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
        print("[WARNING] No metrics provided, using defaults!")
        metrics = default_metrics
    else:
        print("[INFO] Metrics string length: %d" % len(metrics))
        metrics = list(set(metrics.split(",")))
        print("[INFO] Number of metrics after split: %d" % len(metrics))
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

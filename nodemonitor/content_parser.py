#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Created on 2017-12-22
@author: foxty

cmd output parser
"""
import logging
import re
from datetime import datetime
from common import TextTable
from model import NSystemReport, NCPUReport, NMemoryReport, NDiskReport, \
    SPidstatReport, SJstatGCReport


_RE_SYSREPORT = re.compile('.*?(?P<users>\\d+)\\suser.*'
                           'age: (?P<load1>\\d+\\.\\d+), (?P<load5>\\d+\\.\\d+), (?P<load15>\\d+\\.\\d+).*',
                           re.S)


def parse_w(aid, collect_time, content):
    """parse the output of w command as follow:
     21:25:14 up 45 days,  3:18,  1 user,  load average: 0.00, 0.03, 0.05
    USER     TTY      FROM             LOGIN@   IDLE   JCPU   PCPU WHAT
    root     pts/0    pc-itian.arrs.ar 27Dec17  2.00s  8:47   0.00s w
    :param aid: agentid
    :param collect_time: collect time from node
    :param content: output of `w`
    :return: NSystemReport
    """
    m = _RE_SYSREPORT.match(content)
    if m:
        days = 0
        users = int(m.group('users'))
        load1 = float(m.group('load1'))
        load5 = float(m.group('load5'))
        load15 = float(m.group('load15'))
        return NSystemReport(aid=aid, timestamp=collect_time, uptime=days*24*3600, users=users,
                             load1=load1, load5=load5, load15=load15,
                             procs_r=None, procs_b=None, sys_in=None, sys_cs=None)
    else:
        logging.warn('invalid content of `w`: %s', content)
        return None


def parse_free(aid, collect_time, content):
    """parse output of `free -m` command get memory usage information:
                 total       used       free     shared    buffers     cached
    Mem:         19991       6428      13562          0        148       2656
    -/+ buffers/cache:       3623      16367
    Swap:        10063          0      10063

    :param aid: agentid
    :param collect_time: collect time from node
    :param content: output of `free -m`
    :return: NMemoryReport
    """
    t = TextTable('col ' + content.lstrip(), vheader=True)
    if t.size >= 2:
        total_mem = t.get_int('Mem:', 'total')
        used_mem = t.get_int('Mem:', 'used')
        free_mem = t.get_int('Mem:', 'free')
        total_swap = t.get_int('Swap:', 'total')
        use_swap = t.get_int('Swap:', 'used')
        free_swap = t.get_int('Swap:', 'free')
        return NMemoryReport(aid=aid, timestamp=collect_time, total_mem=total_mem, used_mem=used_mem,
                             free_mem=free_mem, cache_mem=None, total_swap=total_swap,
                             used_swap=use_swap, free_swap=free_swap)
    else:
        logging.warn('invalid content of`free`: %s', content)
        return None


def parse_vmstat(aid, collect_time, content):
    """parse output of command `vmstat` and extact the system/cpu section.

    Linux output:
    procs -----------memory---------- ---swap-- -----io---- --system-- -----cpu-----
     r  b   swpd   free   buff  cache   si   so    bi    bo   in   cs us sy id wa st
     0  0      0 13540540 161232 2972924    0    0     2    17   84   25  0  0 99  1  0
     0  0      0 13540532 161232 2972956    0    0     0    48  310  550  0  0 99  1  0

    Solaris output:
     kthr      memory            page            disk          faults      cpu
     r b w   swap  free  re  mf pi po fr de sr s0 s1 s2 --   in   sy   cs us sy id
     3 0 0 69302168 22126772 4 62 0 0  0  0  0 -0  0 33  0 2503 4393 3645  2  4 94
     1 0 0 68852484 24149452 11 53 0 0 0  0  0  0  0  0  0 1463 1273 1198  1  1 99

    :param aid:
    :param collect_time:
    :param content:
    :return: (NCPUReport, procs_r, procs_b, sys_in, sys_cs)
    """
    t = TextTable(content, 1)
    if t.size == 2:
        data_rn = -1
        procs_r, procs_b = t.get_int(data_rn,'r'), t.get_int(data_rn,'b')
        sys_in, sys_cs = t.get_int(data_rn,'in'), t.get_int(data_rn,'cs')
        us, sy = t.get_int(data_rn,'us'), t.get_ints(data_rn,'sy')[-1]
        id_, wa = t.get_int(data_rn,'id'), t.get_int(data_rn,'wa')
        st = t.get_int(data_rn,'st')
        r = NCPUReport(aid=aid, timestamp=collect_time,
                       us=us, sy=sy,id=id_, wa=wa, st=st)
        return r, procs_r, procs_b, sys_in, sys_cs
    else:
        logging.warn('invalid content of `vmstat` : %s', content)
        return None, None, None, None, None


def parse_df(aid, collect_time, content):
    """
    Parse the output of df command get disk utilization data
    :param aid: agentid
    :param collect_time: local time in node
    :param content: output of command `df -k`
    :return: list of disk utilization record
    """
    t = TextTable(content)
    if t.size > 1:
        diskreps = []
        for row in t.get_rows():
            cols = row.as_tuple()
            fs, size, used  = cols[0], int(cols[1]), int(cols[2])
            available, used_util, mount_point= int(cols[3]), float(cols[4][:-1]), cols[5]

            diskreps.append(NDiskReport(aid=aid, timestamp=collect_time, fs=fs, size=size, used=used,
                                        available=available, used_util=used_util, mount_point=mount_point))
        return diskreps
    else:
        logging.warn('invalid content of `df` : %s', content)
        return None


def parse_netstat(aid, collect_time, content):
    pass


def parse_dstat(content, data_size):
    """ parse the output of dstat command and get last line of data.
    :param content:
    :param data_size:
    :return: List[str] for data and None if invalid content
    """
    if content:
        data = re.split('\s*\|?\s*', [l.strip() for l in content.splitlines() if l.strip()][-1])
        return data if len(data) == data_size else None
    logging.warn('invalid content for dstat %s', content)
    return None


def parse_dstat_sys(aid, collect_time, content):
    """ parse the output of `dstat -lyp` to NSystemReport
     ---load-avg--- ---system-- ---procs---
     1m   5m  15m | int   csw |run blk new
     0 0.02    0| 401   750 |  0   0 0.4
     0 0.02    0| 223   501 |  0   0   0
    :param aid:
    :param collect_time:
    :param content:
    :return: NSystemReport
    """
    data = parse_dstat(content, 8)
    return NSystemReport(aid=aid, timestamp=collect_time,
                         load1=float(data[0]), load5=float(data[1]), load15=float(data[2]),
                         sys_in=int(data[3]), sys_cs=int(data[4]), procs_r=int(data[5]),
                         procs_b=int(data[6])) if data else None


def parse_dstat_cpu(aid, collect_time, content):
    """ parse the output of `dstat -c` to NCPUReport
     ----total-cpu-usage----
     usr sys idl wai hiq siq
     0   0  99   1   0   0
     0   0 100   0   0   0
    :param aid:
    :param collect_time:
    :param content:
    :return: NCPUReport
    """
    data = parse_dstat(content, 6)
    return NCPUReport(aid=aid, timestamp=collect_time, us=int(data[0]), sy=int(data[1]),
                         id=int(data[2]), wa=int(data[3])) if data else None


def conv_to_mega(value, multiplier=1024):
    if value[-1] in ('G', "g"):
        return float(value[:-1]) * multiplier
    elif value[-1] in ('M', 'm'):
        return float(value[:-1])
    elif value[-1] in ('K', 'k'):
        return float(value[:-1]) / multiplier
    elif value[-1] in ('B', 'b'):
        return float(value[:-1]) / (multiplier ** 2)
    elif value.isdigit():
        return float(value)
    else:
        return None


def conv_to_kilo(value, multiplier=1024):
    if value[-1] in ('G', "g"):
        return float(value[:-1]) * pow(multiplier, 2)
    elif value[-1] in ('M', 'm'):
        return float(value[:-1]) * multiplier
    elif value[-1] in ('K', 'k'):
        return float(value[:-1])
    elif value[-1] in ('B', 'b'):
        return float(value[:-1]) / (multiplier)
    elif value.isdigit():
        return float(value)
    else:
        return None


def parse_dstat_mem(aid, collect_time, content):
    """
    ------memory-usage----- ----swap--- ---paging--
    used  buff  cach  free| used  free|  in   out
    3666M  197M 9.80G 6096M|   0    10G|   0     0
    3666M  197M 9.80G 6096M|   0    10G|   0     0
    :param aid:
    :param collect_time:
    :param content:
    :return: NMemoryReport
    """
    data = parse_dstat(content, 8)
    if data:
        used_mem = conv_to_mega(data[0])
        cache_mem = conv_to_mega(data[2])
        free_mem = conv_to_mega(data[3])
        used_swap = conv_to_mega(data[4])
        free_swap = conv_to_mega(data[5])
        page_in, page_out = int(data[6]), int(data[7])
    return NMemoryReport(aid=aid, timestamp=collect_time, total_mem=used_mem+cache_mem+free_mem,
                         used_mem=used_mem, free_mem=free_mem, cache_mem=cache_mem,
                         total_swap=used_swap+free_swap, used_swap=used_swap,
                         free_swap=free_swap) if data else None


def parse_dstat_sock(aid, collect_time, content):
    pass


def parse_dstat_dio(aid, collect_time, content):
    pass


def parse_pidstat(aid, collect_time, service_id, content):
    t = TextTable(content.replace('#', ''), header_ln=1)
    if t.size > 1:
        prow = t[0]
        tid = int(prow['TID'])
        cpu_us, cpu_sy, cpu_gu, cpu_util = float(prow['%usr']), float(prow['%system']), \
                                           float(prow['%guest']), float(prow['%CPU'])
        mem_minflt, mem_majflt, mem_vsz, mem_rss, mem_util = float(prow['minflt/s']), float(prow['majflt/s']), \
                                                             int(prow['VSZ']), int(prow['RSS']), float(prow['%MEM'])
        disk_rd, disk_wr, disk_ccwr = float(prow['kB_rd/s']), float(prow['kB_wr/s']), float(prow['kB_ccwr/s'])
        rep = SPidstatReport(aid=aid, service_id=service_id, timestamp=collect_time, tid=tid,
                             cpu_us=cpu_us, cpu_sy=cpu_sy, cpu_gu=cpu_gu, cpu_util=cpu_util,
                             mem_minflt=mem_minflt, mem_majflt=mem_majflt,
                             mem_vsz=mem_vsz, mem_rss=mem_rss, mem_util=mem_util,
                             disk_rd=disk_rd, disk_wr=disk_wr, disk_ccwr=disk_ccwr)
        logging.debug('get pidsat report %s', rep)
        return rep
    else:
        logging.warn('invalid content of `pidstat` : %s', content)
        return None


def parse_prstat(aid, collect_time, service_id, content):
    """
    Parsing output of prstat -p from solaris, content as follow:

       PID USERNAME  SIZE   RSS STATE  PRI NICE      TIME  CPU PROCESS/NLWP
        11023 root      192M  154M sleep   59    0   3:31:12 0.0% java/50
        Total: 1 processes, 50 lwps, load averages: 0.33, 7.15, 13.36

    :param aid:
    :param collect_time:
    :param service_id:
    :param content:
    :return: SPidstatReport(partial)
    """
    t = TextTable(content)
    if t.size > 1:
        prow = t[0]
        tid = prow.get_int('PID')
        cpu_util = float(prow.get('CPU')[:-1])
        mem_vsz, mem_rss = conv_to_kilo(prow.get('SIZE')), conv_to_kilo(prow.get('RSS')),
        rep = SPidstatReport(aid=aid, service_id=service_id, timestamp=collect_time, tid=tid,
                             cpu_util=cpu_util, mem_vsz=mem_vsz, mem_rss=mem_rss)
        logging.debug('get prstat report %s', rep)
        return rep
    else:
        logging.warn('invalid content of `prstat` : %s', content)
        return None


def parse_jstatgc(aid, collect_time, service_id, content):
    t = TextTable(content)
    if t.has_body:
        data = t[0]
        ts = data.get_float('Timestamp')
        S0C, S1C = data.get_float('S0C'), data.get_float('S1C')
        S0U, S1U = data.get_float('S0U'), data.get_float('S1U')
        EC, EU = data.get_float('EC'), data.get_float('EU')
        OC, OU = data.get_float('OC'), data.get_float('OU')
        MC, MU = data.get_float('MC'), data.get_float('MU')
        CCSC, CCSU = data.get_float('CCSC'), data.get_float('CCSU')
        YGC, YGCT = data.get_int('YGC'), data.get_float('YGCT')
        FGC, FGCT, GCT = data.get_int('FGC'), data.get_float('FGCT'), data.get_float('GCT')
        rep = SJstatGCReport(aid=aid, service_id=service_id, timestamp=collect_time, ts=ts,
                             s0c=S0C, s1c=S1C, s0u=S0U, s1u=S1U,
                             ec=EC, eu=EU, oc=OC, ou=OU,
                             mc=MC, mu=MU, ccsc=CCSC, ccsu=CCSU,
                             ygc=YGC, ygct=YGCT, fgc=FGC, fgct=FGCT, gct=GCT)
        logging.debug('get jstat-gc report %s', rep)
        return rep
    else:
        logging.warn('invalid content of `jstat-gc` : %s', content)
        return None
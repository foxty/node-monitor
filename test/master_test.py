#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Created on 2017-12-22
@author: foxty
"""

import unittest
import os
import time
import model
import model_test
import content_parser
from datetime import datetime, timedelta
from common import Msg
from master import Master, DataKeeper


class ContentParserTest(unittest.TestCase):

    def test_parse_w_solaris(self):
        ctime = datetime.now()
        r = content_parser.parse_w('2', ctime, content='''
        9:11pm  up 43 day(s),  8:52,  11 user,  load average: 2.38, 2.41, 2.41
        User     tty           login@  idle   JCPU   PCPU  what
        root     pts/4        27Dec17           18         -bash
        ''')
        self.assertEqual('2', r.aid)
        self.assertEqual(ctime, r.timestamp)
        self.assertEqual(0, r.uptime)
        self.assertEqual(11, r.users)
        self.assertEqual(2.38, r.load1)
        self.assertEqual(2.41, r.load5)
        self.assertEqual(2.41, r.load15)
        self.assertIsNone(r.procs_r)
        self.assertIsNone(r.procs_b)
        self.assertIsNone(r.sys_in)
        self.assertIsNone(r.sys_cs)

    def test_parse_w_linux(self):
        ctime = datetime.now()
        r = content_parser.parse_w('2', ctime, content='''
        21:26:13 up  3:32,  3 users,  load average: 0.00, 0.03, 0.00
        USER     TTY      FROM              LOGIN@   IDLE   JCPU   PCPU WHAT
        root     pts/2    pc-llou.arrs.arr 17:53    3:32m  0.00s  0.00s -bash
        root     pts/1    pc-yzhang3.arrs. 17:53    3:32m  0.00s  0.00s -bash
        root     pts/0    pc-itian.arrs.ar 21:20    3:18   0.01s  0.01s -bash
        ''')
        self.assertEqual('2', r.aid)
        self.assertEqual(ctime, r.timestamp)
        self.assertEqual(0, r.uptime)
        self.assertEqual(3, r.users)
        self.assertEqual(0.00, r.load1)
        self.assertEqual(0.03, r.load5)
        self.assertEqual(0.00, r.load15)
        self.assertIsNone(r.procs_r)
        self.assertIsNone(r.procs_b)
        self.assertIsNone(r.sys_in)
        self.assertIsNone(r.sys_cs)

    def test_parse_vmstat_linux(self):
        ctime = datetime.now()
        r, procs_r, procs_b, sys_in, sys_cs = content_parser.parse_vmstat('1', collect_time=ctime, content='''
         procs -----------memory---------- ---swap-- -----io---- --system-- -----cpu-----
         r  b   swpd   free   buff  cache   si   so    bi    bo   in   cs us sy id wa st
         0  0      0 13540540 161232 2972924    0    0     2    17   84   25  0  0 99  1  0
         10  5      0 13540532 161232 2972956    0    0     0    48  310  550  0  0 99  1  0
        ''')
        self.assertEqual('1', r.aid)
        self.assertEqual(ctime, r.timestamp)
        self.assertEqual(0, r.us)
        self.assertEqual(0, r.sy)
        self.assertEqual(99, r.id)
        self.assertEqual(1, r.wa)
        self.assertEqual(0, r.st)
        self.assertEqual(10, procs_r)
        self.assertEqual(5, procs_b)
        self.assertEqual(310, sys_in)
        self.assertEqual(550, sys_cs)

    def test_parse_vmstat_solaris(self):
        ctime = datetime.now()
        r, procs_r, procs_b, sys_in, sys_cs = content_parser.parse_vmstat('1', collect_time=ctime, content='''
         kthr      memory            page            disk          faults      cpu
         r b w   swap  free  re  mf pi po fr de sr s0 s1 s2 --   in   sy   cs us sy id
         1 0 0 40259268 4601776 32 543 3 0 0  0  0 -0  0 20  0 3092 3291 2996  1  5 93
         1 2 0 37758804 2545032 14 53 0 0  0  0  0  0  0  1  0 2236 1625 2002  1  1 98
        ''')
        self.assertEqual('1', r.aid)
        self.assertEqual(ctime, r.timestamp)
        self.assertEqual(1, r.us)
        self.assertEqual(1, r.sy)
        self.assertEqual(98, r.id)
        self.assertEqual(None, r.wa)
        self.assertEqual(None, r.st)
        self.assertEqual(1, procs_r)
        self.assertEqual(2, procs_b)
        self.assertEqual(2236, sys_in)
        self.assertEqual(2002, sys_cs)

    def test_parse_free(self):
        ctime = datetime.now()
        r = content_parser.parse_free('1', collect_time=ctime, content='''
                    total       used       free     shared    buffers     cached
        Mem:         19991       6428      13562          0        148       2656
        -/+ buffers/cache:       3623      16367
        Swap:        10063          0      10063
        ''')
        self.assertEqual('1', r.aid)
        self.assertEqual(ctime, r.timestamp)
        self.assertEqual(19991, r.total_mem)
        self.assertEqual(6428, r.used_mem)
        self.assertEqual(13562, r.free_mem)
        self.assertEqual(None, r.cache_mem)
        self.assertEqual(10063, r.total_swap)
        self.assertEqual(0, r.used_swap)
        self.assertEqual(10063, r.free_swap)

        r = content_parser.parse_free('1', collect_time=ctime, content='''
                      total        used        free      shared  buff/cache   available
        Mem:           1839         408         568          24         863        1230
        Swap:          2047           0        2047
        ''')
        self.assertEqual('1', r.aid)
        self.assertEqual(ctime, r.timestamp)
        self.assertEqual(1839, r.total_mem)
        self.assertEqual(408, r.used_mem)
        self.assertEqual(568, r.free_mem)
        self.assertEqual(None, r.cache_mem)
        self.assertEqual(2047, r.total_swap)
        self.assertEqual(0, r.used_swap)
        self.assertEqual(2047, r.free_swap)

    def _assert_dr(self, aid, ctime, fs, size, used, avai, used_util, mount, dr):
        self.assertEqual(aid, dr.aid)
        self.assertEqual(ctime, dr.timestamp)
        self.assertEqual(fs, dr.fs)
        self.assertEqual(size, dr.size)
        self.assertEqual(used, dr.used)
        self.assertEqual(avai, dr.available)
        self.assertEqual(used_util, dr.used_util)
        self.assertEqual(mount, dr.mount_point)

    def test_parse_invalid_df(self):
        content = '''
        df: unknown option: P
        Usage: df [-F FSType] [-abeghklntVvZ] [-o FSType-specific_options] [directory | block_device | resource]
        '''
        ctime = datetime.now()
        drs = content_parser.parse_df('1', collect_time=ctime, content=content)
        self.assertIsNone(drs)

    def test_parse_df_linux(self):
        content = '''
        Filesystem          1K-blocks    Used Available Use% Mounted on
        /dev/mapper/cl-root  52403200 3294392  49108808   7% /
        devtmpfs               931344       0    931344   0% /dev
        tmpfs                  942056       0    942056   0% /dev/shm
        tmpfs                  942056   25116    916940   3% /run
        tmpfs                  942056       0    942056   0% /sys/fs/cgroup
        /dev/mapper/cl-home 112134660   32944 112101716   1% /home
        /dev/sda1             1038336  187756    850580  19% /boot
        tmpfs                  188412       0    188412   0% /run/user/0
        '''
        ctime = datetime.now()
        drs = content_parser.parse_df('1', ctime, content=content)
        self.assertEqual(8, len(drs))
        self._assert_dr('1', ctime, '/dev/mapper/cl-root', 52403200, 3294392, 49108808,  7, '/', drs[0])
        self._assert_dr('1', ctime, 'tmpfs', 188412, 0, 188412, 0, '/run/user/0', drs[-1])

    def test_parse_df_solaris(self):
        content = '''
        Filesystem            kbytes    used   avail capacity  Mounted on
        /                    369884093 25200224 344683869     7%    /
        /dev                 369884093 25200224 344683869     7%    /dev
        /lib                 842900159 4687993 838212166     1%    /lib
        /platform            842900159 4687993 838212166     1%    /platform
        /sbin                842900159 4687993 838212166     1%    /sbin
        proc                       0       0       0     0%    /proc
        ctfs                       0       0       0     0%    /system/contract
        mnttab                     0       0       0     0%    /etc/mnttab
        objfs                      0       0       0     0%    /system/object
        swap                 1326612     344 1326268     1%    /etc/svc/volatile
        /usr/lib/libc/libc_hwcap1.so.1 369884093 25200224 344683869     7%    /lib/libc.so.1
        fd                         0       0       0     0%    /dev/fd
        swap                 1326624     356 1326268     1%    /tmp
        swap                 1326292      24 1326268     1%    /var/run

        '''
        ctime = datetime.now()
        drs = content_parser.parse_df('1', collect_time=ctime, content=content)
        self.assertEqual(14, len(drs))
        self._assert_dr('1', ctime, '/', 369884093, 25200224, 344683869, 7, '/', drs[0])
        self._assert_dr('1', ctime, 'swap', 1326292, 24, 1326268, 1, '/var/run', drs[-1])

    def test_parse_dstat_sys(self):
        content = """
        [7l---load-avg--- ---system-- ---procs---
         1m   5m  15m | int   csw |run blk new
        0.05 0.18 0.09| 401   749 |  0   0 0.4
        0.05 0.18 0.09| 394   707 |  0   0   0
        """
        ctime = datetime.now()
        sys = content_parser.parse_dstat_sys('1', ctime, content)
        self.assertIsNotNone(sys)
        self.assertEqual('1', sys.aid)
        self.assertEqual(ctime, sys.timestamp)
        self.assertEqual(0.05, sys.load1)
        self.assertEqual(0.18, sys.load5)
        self.assertEqual(0.09, sys.load15)
        self.assertEqual(394, sys.sys_in)
        self.assertEqual(707, sys.sys_cs)
        self.assertEqual(0, sys.procs_r)
        self.assertEqual(0, sys.procs_b)

    def test_parse_dstat_cpu(self):
        c = """
        [7l----total-cpu-usage----
        usr sys idl wai hiq siq
          0   0  99   1   0   0
          1   2  95   2   0   0

        """
        ctime = datetime.now()
        cpu = content_parser.parse_dstat_cpu('1', ctime, c)
        self.assertIsNotNone(cpu)
        self.assertEqual('1', cpu.aid)
        self.assertEqual(ctime, cpu.timestamp)
        self.assertEqual(1, cpu.us)
        self.assertEqual(2, cpu.sy)
        self.assertEqual(95, cpu.id)
        self.assertEqual(2, cpu.wa)
        self.assertEqual(None, cpu.st)

    def test_conv_to_mega(self):
        self.assertEqual(1536, content_parser.conv_to_mega('1.5G'))
        self.assertEqual(1536, content_parser.conv_to_mega('1.5g'))
        self.assertEqual(1.5, content_parser.conv_to_mega('1.5m'))
        self.assertEqual(1.5, content_parser.conv_to_mega('1.5M'))
        self.assertEqual(1.5, content_parser.conv_to_mega('1536k'))
        self.assertEqual(1.5, content_parser.conv_to_mega('1536K'))
        self.assertEqual(1, content_parser.conv_to_mega('1048576b'))
        self.assertEqual(1, content_parser.conv_to_mega('1048576B'))
        self.assertEqual(0, content_parser.conv_to_mega('0'))
        self.assertIsNone(content_parser.conv_to_mega('000a'))

    def test_parse_dstat_mem(self):
        c = """
        [7l------memory-usage----- ----swap--- ---paging--
         used  buff  cach  free| used  free|  in   out 
        3666M  197M 9.80G 6096M|   0    10G|   0     0 
        3666M  197M 9.80G 6096M|   0    10G|   0     0 
        """
        ctime = datetime.now()
        mem = content_parser.parse_dstat_mem('1', ctime, c)
        self.assertIsNotNone(mem)
        self.assertEqual('1', mem.aid)
        self.assertEqual(ctime, mem.timestamp)
        self.assertEqual(9.80*1024+6096+3666, mem.total_mem)
        self.assertEqual(3666, mem.used_mem)
        self.assertEqual(9.8*1024, mem.cache_mem)
        self.assertEqual(6096, mem.free_mem)
        self.assertEqual(10*1024, mem.total_swap)
        self.assertEqual(0, mem.used_swap)
        self.assertEqual(10*1024, mem.free_swap)

    def test_parse_pidstat(self):
        c = '''Linux 2.6.32-431.el6.x86_64 (cycad) 	02/11/2018 	_x86_64_	(4 CPU)

        #      Time      TGID       TID    %usr %system  %guest    %CPU   CPU  minflt/s  majflt/s     VSZ    RSS   %MEM   kB_rd/s   kB_wr/s kB_ccwr/s  Command
         1518318452      9591         0    0.13    0.02    0.00    0.15     0      1.47      0.00 8529320 2109020  10.30      1.00      7.17      2.45  java
         1518318452         0      9591    0.00    0.00    0.00    0.00     0      0.01      0.00 8529320 2109020  10.30      0.00      0.00      0.00  |__java
         1518318452         0      9621    0.00    0.00    0.00    0.00     2      0.09      0.00 8529320 2109020  10.30      0.00      0.00      0.00  |__java
         1518318452         0      9624    0.00    0.00    0.00    0.00     3      0.00      0.00 8529320 2109020  10.30      0.00      0.00      0.00  |__java
         '''
        ctime = datetime.now()
        pidrep = content_parser.parse_pidstat('1', ctime, 'serv1', c)
        self.assertIsNotNone(pidrep)
        self.assertEqual(model.SPidstatReport(aid='1', service_id='serv1', timestamp=ctime, tid=0,
                                           cpu_us=0.13, cpu_sy=0.02, cpu_gu=0.0, cpu_util=0.15,
                                           mem_minflt=1.47, mem_majflt=0.0, mem_vsz=8529320,
                                           mem_rss=2109020, mem_util=10.30,
                                           disk_rd=1.0, disk_wr=7.17, disk_ccwr=2.45),
                         pidrep)

    def test_parse_pidstat_centos7(self):
        c = """
        Linux 3.10.0-123.el7.x86_64 (saa018)    06/27/2018      _x86_64_        (2 CPU)

        #      Time   UID      TGID       TID    %usr %system  %guest    %CPU   CPU  minflt/s  majflt/s     VSZ    RSS   %MEM   kB_rd/s   kB_wr/s kB_ccwr/s  Command
         1530099976     0      7443         0    0.13    0.02    0.00    0.15     1      0.47      0.10  160052   8800   0.23      1.00      7.17      2.45  python
         1530099976     0         0      7443    0.00    0.00    0.00    0.00     1      0.04      0.00  160052   8800   0.23      0.00      0.00      0.00  |__python
         1530099976     0         0      7455    0.00    0.00    0.00    0.00     0      0.14      0.00  160052   8800   0.23      0.00      0.00      0.00  |__python
        """
        ctime = datetime.now()
        pidrep = content_parser.parse_pidstat('1', ctime, 'serv1', c)
        self.assertIsNotNone(pidrep)
        self.assertEqual(model.SPidstatReport(aid='1', service_id='serv1', timestamp=ctime, tid=0,
                                              cpu_us=0.13, cpu_sy=0.02, cpu_gu=0.0, cpu_util=0.15,
                                              mem_minflt=0.47, mem_majflt=0.10, mem_vsz=160052,
                                              mem_rss=8800, mem_util=0.23,
                                              disk_rd=1.0, disk_wr=7.17, disk_ccwr=2.45),
                         pidrep)

    def test_parse_jstatgc(self):
        c = '''
        Timestamp   S0C    S1C      S0U    S1U      EC       EU        OC         OU       MC       MU     CCSC   CCSU      YGC   YGCT    FGC    FGCT     GCT
        13939.4  	0.0    30720.0  0.0    30720.0  342016.0 243712.0 4345856.0   776192.2  66896.0 65355.5 8060.0 7777.3    119   40.678   2      2.100   40.678
'''
        ctime = datetime.now()
        statgc_rep = content_parser.parse_jstatgc('1', ctime, 'serv1', c)
        self.assertIsNotNone(statgc_rep)
        self.assertEqual(model.SJstatGCReport(aid='1', service_id='serv1', timestamp=ctime, ts=13939.4,
                                              s0c=0.0, s1c=30720.0, s0u=0.0, s1u=30720.0,
                                              ec=342016.0, eu=243712.0, oc=4345856.0, ou=776192.2,
                                              mc=66896.0, mu=65355.5, ccsc=8060.0, ccsu=7777.3,
                                              ygc=119, ygct=40.678, fgc=2, fgct=2.1, gct=40.678),
                         statgc_rep)

    def test_parse_prstat(self):
        c = '''   PID USERNAME  SIZE   RSS STATE  PRI NICE      TIME  CPU PROCESS/NLWP
 11023 root      192M  154M sleep   59    0   3:31:31 15.9% java/51
Total: 1 processes, 51 lwps, load averages: 6.75, 4.85, 3.50
'''
        ctime = datetime.now()
        rep = content_parser.parse_prstat('1', ctime, 'serv1', c)
        self.assertIsNotNone(rep)
        self.assertEqual(model.SPidstatReport(aid='1', service_id='serv1', timestamp=ctime, tid=11023,
                                              mem_vsz=192*1024, mem_rss=154*1024, cpu_util=15.9),
                         rep)

    def test_parse_iplinkstat(self):
        aid = '1'
        ctime = datetime.now()
        content = '''
        1: lo: <LOOPBACK,UP,LOWER_UP> mtu 16436 qdisc noqueue state UNKNOWN
            link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00
            RX: bytes  packets  errors  dropped overrun mcast
            1781983109 13777738 1       2       3       4
            TX: bytes  packets  errors  dropped carrier collsns
            1781983109 13777738 0       0       0       0
        2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc mq state UP qlen 1000
            link/ether 00:0c:29:42:7c:d3 brd ff:ff:ff:ff:ff:ff
            RX: bytes  packets  errors  dropped overrun mcast
            3071151682 9787917  0       0       0       162936
            TX: bytes  packets  errors  dropped carrier collsns
            2002149697 6364079  0       0       0       0
        '''
        reps = content_parser.parse_iplinkstat(aid, ctime, content)
        self.assertEqual(2, len(reps))
        self.assertEqual(model.NNetworkReport(timestamp=ctime, aid=aid,
                                              interface='lo',
                                              rx_bytes=1781983109, rx_packets=13777738, rx_errors=1,
                                              rx_dropped=2, rx_overrun=3, rx_mcast=4,
                                              tx_bytes=1781983109, tx_packets=13777738, tx_errors=0,
                                              tx_dropped=0, tx_carrier=0, tx_collsns=0),
                         reps[0])
        self.assertEqual(model.NNetworkReport(timestamp=ctime, aid=aid,
                                              interface='eth0',
                                              rx_bytes=3071151682, rx_packets=9787917, rx_errors=0,
                                              rx_dropped=0, rx_overrun=0, rx_mcast=162936,
                                              tx_bytes=2002149697, tx_packets=6364079, tx_errors=0,
                                              tx_dropped=0, tx_carrier=0, tx_collsns=0), reps[1])


class MasterTest(model_test.BaseDBTest):

    def setUp(self):
        model_test.BaseDBTest.setUp(self)
        config = {
            'master': {
                'server': {
                    'host': '0.0.0.0',
                    'port': 7890
                },
                'data_retention': {
                    'interval': 10,
                    'policy': {}
                }
            }
        }
        self.master = Master(config)

    def test_creation(self):
        master = self.master
        self.assertEqual(('0.0.0.0', 7890), master._addr)
        self.assertEqual(5, len(master._handlers))

    def test_handle_reg(self):
        master = self.master

        # test a new agent join
        regmsg = Msg.create_msg('1', Msg.A_REG, {'os': 'LINUX', 'hostname': 'test-host'})
        master.handle_msg(regmsg)
        agent = master.find_agent('1')
        self.assertEqual('1', agent.aid)
        self.assertEqual('test-host', agent.host)
        self.assertEqual('test-host@LINUX', agent.name)

    def test_handle_hearbeat(self):
        pass

    def test_handle_empty_nmetrics(self):
        m = self.master
        ctime = datetime.now()
        body = {'collect_time': ctime}
        regmsg = Msg.create_msg('2', Msg.A_REG, {'os': 'LINUX', 'hostname': 'test-host'})
        m.handle_msg(regmsg)

        nmmsg = Msg.create_msg('2', Msg.A_NODE_METRIC, body)
        re = m.handle_msg(nmmsg)
        self.assertTrue(re)

    def test_handle_nmetrics_linux(self):
        agent = model.Agent('2', 'localhost', 'localhost', datetime.now())
        agent.save()

        m = self.master
        m._load_agents()
        ctime = datetime.now()
        msgbody = {
            'w': ''' 05:04:07 up 57 days, 10:57,  1 user,  load average: 2.11, 2.54, 2.77
                 USER     TTY      FROM             LOGIN@   IDLE   JCPU   PCPU WHAT
                 root     pts/0    pc-itian.arrs.ar 27Dec17  7.00s  1:14m  0.03s -bash
                 ''',
            'free': '''              total        used        free      shared  buff/cache   available
                    Mem:           1839         408         566          24         864        1229
                    Swap:          2047           0        2047
                    ''',
            'vmstat': '''procs -----------memory---------- ---swap-- -----io---- -system-- ------cpu-----
                         r  b   swpd   free   buff  cache   si   so    bi    bo   in   cs us sy id wa st
                         3  0      0 580284    948 884556    0    0     0     1    8    3  2  0 97  0  0
                         1  0      0 580284    948 884556    0    0     0     0 1091  404 86 14  0  0  0
                      '''
        }
        nmmsg = Msg.create_msg(agent.aid, Msg.A_NODE_METRIC, msgbody)
        nmmsg.set_header(nmmsg.H_COLLECT_AT, ctime)
        re = m.handle_msg(nmmsg)
        self.assertTrue(re)
        agents = model.Agent.query()
        self.assertEqual(1, len(agents))

    def test_handle_smetrics(self):
        aid = '2'
        agent = model.Agent(aid, 'localhost', 'localhost', datetime.now())
        agent.save()

        m = self.master
        ctime = datetime.now()
        msgbody = {'name': 'service1', 'pid': '1', 'metrics': {'m1': 'm1 content', 'm2': 'm2 content'}}
        nmmsg = Msg.create_msg(agent.aid, Msg.A_SERVICE_METRIC, msgbody)
        nmmsg.set_header(Msg.H_COLLECT_AT, ctime)
        re = m.handle_msg(nmmsg)
        self.assertTrue(re)

        smetrics = model.SMetric.query(orderby='category ASC')
        self.assertEqual(2, len(smetrics))
        sm1, sm2 = smetrics[0], smetrics[1]
        self.assertEqual(aid, sm1.aid)
        self.assertEqual(ctime.replace(microsecond=0), sm1.collect_at)
        self.assertEqual('service1', sm1.name)
        self.assertEqual(1, sm1.pid)
        self.assertEqual('m1', sm1.category)
        self.assertEqual('m1 content', sm1.content)

        sinfo = model.SInfo.query_by_aid(aid)[0]
        self.assertEqual(aid, sinfo.aid)
        self.assertEqual('service1', sinfo.name)
        self.assertEqual(1, sinfo.pid)
        self.assertEqual(ctime.replace(microsecond=0), sinfo.last_report_at)
        self.assertEqual(model.SInfo.STATUS_ACT, sinfo.status.strip())

    def test_handle_smetrics_pidchg(self):
        aid = '2'
        agent = model.Agent(aid, 'localhost', 'localhost', datetime.now())
        agent.save()

        m = self.master
        ctime = datetime.now()
        msgbody = {'name': 'service1', 'pid': '1', 'metrics': {'m1': 'm1 content', 'm2': 'm2 content'}}
        nmmsg = Msg.create_msg(agent.aid, Msg.A_SERVICE_METRIC, msgbody)
        nmmsg.set_header(Msg.H_COLLECT_AT, ctime)
        m.handle_msg(nmmsg)

        ctime1 = datetime.now() + timedelta(hours=1)
        msgbody['pid'] = '2'
        nmmsg = Msg.create_msg(agent.aid, Msg.A_SERVICE_METRIC, msgbody)
        nmmsg.set_header(Msg.H_COLLECT_AT, ctime1)
        m.handle_msg(nmmsg)

        smetrics = model.SMetric.query()
        self.assertEqual(4, len(smetrics))

        sinfo = model.SInfo.query_by_aid(aid)[0]
        self.assertEqual(aid, sinfo.aid)
        self.assertEqual('service1', sinfo.name)
        self.assertEqual(2, sinfo.pid)
        self.assertEqual(ctime1.replace(microsecond=0), sinfo.last_report_at)
        self.assertEqual(model.SInfo.STATUS_ACT, sinfo.status.strip())

        sinfohis = model.SInfoHistory.query(orderby='recv_at ASC')
        self.assertEqual(2, len(sinfohis))
        self.assertEqual(1, sinfohis[0].pid)
        self.assertEqual(2, sinfohis[1].pid)


class DataKeeperTest(model_test.BaseDBTest):

    def setUp(self):
        model_test.BaseDBTest.setUp(self)
        config = {
            'interval': 3,
            'policy': {
                'node_metric_raw': 5
            }
        }
        self.data_keeper = DataKeeper(config)

    def test_init(self):
        dk = self.data_keeper
        self.assertEqual(3, dk._interval)
        self.assertEqual({'node_metric_raw': 5}, dk._policy)
        self.assertEqual(0, dk._count)
        self.assertFalse(dk._run)
        self.assertEqual(None, dk._startat)
        self.assertEqual(None, dk._timer)

    def test_start_stop(self):
        dk = self.data_keeper
        dk.start()
        self.assertTrue(dk._run)
        self.assertIsNotNone(dk._timer)
        self.assertIsNotNone(dk._startat)
        time.sleep(dk._interval + 1)
        dk.stop()
        self.assertFalse(dk._run)
        self.assertEqual(1, dk._count)


if __name__ == '__main__':
    unittest.main()
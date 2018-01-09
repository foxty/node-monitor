#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Created on 2017-12-22
@author: foxty
"""

import unittest
import base64
import os
import node_monitor as nm
from datetime import datetime, date, time, timedelta


class GlobalFuncTest(unittest.TestCase):

    def test_dumpjson(self):
        dt = datetime(2018, 1, 8, 17, 26, 26, 999)
        json_dt = nm.dump_json(dt)
        self.assertEqual('"2018-01-08 17:26:26.000999"', json_dt)

        d = dt.date()
        json_d = nm.dump_json(d)
        self.assertEqual('"2018-01-08"', json_d)

        t = dt.time()
        json_t = nm.dump_json(t)
        self.assertEqual('"17:26:26.000999"', json_t)

    def test_loadjson(self):
        json_dt = '{"date":"2018-01-08 17:26:26.000999", ' \
                  '"entry1":{"start_dt":"2018-01-08 17:26:27.999000", "d":"2018-01-01", "t":"01:01:01:100"}}'
        dt = nm.load_json(json_dt)
        self.assertEqual('2018-01-08 17:26:26.000999', dt['date'].strftime(nm._DATETIME_FMT))
        self.assertEqual('2018-01-01', dt['entry1']['d'].strftime(nm._DATE_FMT))


class MonMsgTest(unittest.TestCase):

    def test_create(self):
        m1 = nm.Msg("12345678")
        self.assertEqual("12345678", m1.agentid)
        self.assertEqual(nm.Msg.NONE, m1.msg_type)
        self.assertEqual('', m1.body)

    def test_eq(self):
        m1 = nm.Msg("12345678")
        m2 = nm.Msg("12345678")
        self.assertEqual(m1, m2)

        m2.msg_type = nm.Msg.A_HEARTBEAT
        self.assertNotEqual(m1, m2)

        m1.msg_type = nm.Msg.A_HEARTBEAT
        self.assertEqual(m1, m2)

        m1.body = "123"
        self.assertNotEqual(m1, m2)

    def test_encode_decode(self):
        msg_body = "12\n\t\n\t34"
        msg = nm.Msg("12345678", nm.Msg.A_HEARTBEAT, body=msg_body)
        self.assertEqual(nm.Msg.A_HEARTBEAT, msg.msg_type)

        header_list, encbody = msg.encode()
        self.assertEqual(4, len(header_list))
        self.assertEqual(msg_body, base64.b64decode(encbody))

        msg1 = nm.Msg.decode(header_list, encbody)
        self.assertEqual(msg, msg1)
        self.assertEqual(msg.sendtime, msg1.sendtime)
        self.assertEqual(True, isinstance(msg.sendtime, datetime))


class MasterDAOTest(unittest.TestCase):

    def setUp(self):
        nm._MASTER_DB_NAME = 'test.db'
        if os.path.exists(nm._MASTER_DB_NAME):
            os.remove(nm._MASTER_DB_NAME)
        self.dao = nm.MasterDAO()

    def tearDown(self):
        if os.path.exists(nm._MASTER_DB_NAME):
            os.remove(nm._MASTER_DB_NAME)

    def test_add_agent(self):
        aglist = self.dao.get_agents()
        self.assertEqual(0, len(aglist))

        ag = nm.Agent('12345678', 'agent1', '127.0.0.1', datetime.now())
        self.dao.add_agent(ag)

        aglist = self.dao.get_agents()
        self.assertEqual(1, len(aglist))
        ag1 = aglist[0]
        self.assertEqual(ag.aid, ag1.aid)
        self.assertEqual(ag.host, ag1.host)

    def test_add_nmetrics(self):
        agentid = '12345678'
        collect_time = datetime.now()
        contents = {'w': 'content for w',
                    'vmstat': 'content for vmstat',
                    'netstat': 'content for netstat'}
        self.dao.add_nmetrics(agentid, collect_time, contents)

        nmetrics = self.dao.get_nmetrics(agentid,
                                         datetime.now() - timedelta(days=1),
                                         datetime.now() + timedelta(days=1))
        self.assertEqual(3, len(nmetrics))
        w = filter(lambda x: x.category == 'w', nmetrics)[0]
        self.assertEqual(agentid, w.aid)
        self.assertEqual('w', w.category)

    def test_add_nmemory(self):
        mem = nm.NMemoryReport(aid='12345678', collect_at=datetime.now(),
                               total_mem=100, used_mem=50, cache_mem=10, free_mem=50,
                               total_swap=100, used_swap=20, free_swap=80)
        self.dao.add_memreport(mem)

        mems = self.dao.get_memreports('12345678',
                                       datetime.now() - timedelta(days=1),
                                       datetime.now() + timedelta(days=1))
        self.assertEqual(1, len(mems))
        self.assertEqual(mem.aid, mems[0].aid)
        self.assertEqual(mem.total_mem, mems[0].total_mem)
        self.assertEqual(mem.used_mem, mems[0].used_mem)


if __name__ == '__main__':
    unittest.main()
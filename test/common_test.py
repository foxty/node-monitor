#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Created on 2017-12-22
@author: foxty
"""
import unittest
import pickle
from common import *


class CommonTest(unittest.TestCase):

    def test_dumpjson_date(self):
        dt = datetime(2018, 1, 8, 17, 26, 26, 999)
        json_dt = dump_json(dt)
        self.assertEqual('"2018-01-08 17:26:26"', json_dt)

        d = dt.date()
        json_d = dump_json(d)
        self.assertEqual('"2018-01-08"', json_d)

        t = dt.time()
        json_t = dump_json(t)
        self.assertEqual('"17:26:26"', json_t)

    def test_loadjson_date(self):
        json_dt = '{"date":"2018-01-08 17:26:26", ' \
                  '"entry1":{"start_dt":"2018-01-08 17:26:27", "d":"2018-01-01", "t":"01:01:01"}}'
        dt = load_json(json_dt)
        self.assertEqual('2018-01-08 17:26:26', dt['date'].strftime(DATETIME_FMT))
        self.assertEqual('2018-01-01', dt['entry1']['d'].strftime(DATE_FMT))
        self.assertEqual('01:01:01', dt['entry1']['t'].strftime(TIME_FMT))


class TextTableTest(unittest.TestCase):

    _TABLE = '''
        A     b   c   d   e   f    g   g    
        a1  b1  c1  d1  e1  f1   g1  g2
    1   2   3   4   5   6    7  77
        1.1  2.2  3.3  4.4  5.5  6.6  7.7 77.77
        '''

    def test_creation(self):
        t = TextTable(self._TABLE)

        self.assertEqual(3, t.size)
        self.assertEqual(8, len(t._hheader))
        self.assertEqual('Abcdefgg', ''.join(t._hheader))
        rows = t.get_rows()
        self.assertEqual(3, len(rows))
        self.assertEqual(('a1', 'b1', 'c1', 'd1', 'e1', 'f1', 'g1', 'g2'), rows[0])
        self.assertEqual(('1', '2', '3', '4', '5', '6', '7', '77'), rows[1])
        self.assertEqual(('1.1', '2.2', '3.3', '4.4', '5.5', '6.6', '7.7', '77.77'), rows[2])

        t = TextTable(self._TABLE, 1)
        self.assertEqual(2, t.size)
        self.assertEqual(8, len(t._hheader))
        self.assertEqual(('1', '2', '3', '4', '5', '6', '7', '77'), t.get_rows()[0])
        self.assertEqual('a1b1c1d1e1f1g1g2', ''.join(t._hheader))

        t = TextTable(self._TABLE, 2)
        self.assertEqual(1, t.size)
        self.assertEqual(8, len(t._hheader))
        self.assertEqual(('1.1', '2.2', '3.3', '4.4', '5.5', '6.6', '7.7', '77.77'), t.get_rows()[0])
        self.assertEqual('123456777', ''.join(t._hheader))

    def test_gets(self):
        t = TextTable(self._TABLE)
        self.assertEqual('a1', t.get(0, 'A'))
        self.assertEqual('b1', t.get(0, 'b'))
        self.assertEqual('g1', t.get(0, 'g'))
        self.assertEqual(['g1', 'g2'], t.gets(0, 'g'))
        self.assertIsNone(t.get(0, 'non-exist'))
        self.assertEqual('aa', t.get(0, 'non-exist', 'aa'))

        self.assertEqual(1, t.get_int(1, 'A'))
        self.assertEqual(2, t.get_int(1, 'b'))
        self.assertEqual(7, t.get_int(1, 'g'))
        self.assertEqual([7, 77], t.get_ints(1, 'g'))
        self.assertIsNone(t.get(1, 'non-exist'))
        self.assertEqual(8, t.get(1, 'non-exist', 8))

        self.assertEqual(1.1, t.get_float(2, 'A'))
        self.assertEqual(2.2, t.get_float(2, 'b'))
        self.assertEqual(7.7, t.get_float(2, 'g'))
        self.assertEqual([7.7, 77.77], t.get_floats(2, 'g'))
        self.assertIsNone(t.get(2, 'non-exist'))
        self.assertEqual(8.8, t.get(1, 'non-exist', 8.8))


class MonMsgTest(unittest.TestCase):

    def test_create(self):
        m1 = Msg.create_msg('12345678', Msg.NONE)
        self.assertEqual('12345678', m1.agentid)
        self.assertEqual(Msg.NONE, m1.msg_type)
        self.assertEqual('', m1.body)

    def test_collectat(self):
        now = datetime.now()
        m = Msg.create_msg('1', Msg.A_SERVICE_METRIC)
        m.set_header(m.H_COLLECT_AT, now)
        self.assertEqual(now.replace(microsecond=0), m.collect_at)

    def test_sendat(self):
        now  = datetime.now()
        m = Msg.create_msg('1', Msg.A_SERVICE_METRIC)
        m.set_header(m.H_SEND_AT, now)
        self.assertEqual(now.replace(microsecond=0), m.send_at)

    def test_eq(self):
        m1 = Msg.create_msg('12345678', Msg.NONE)
        m2 = Msg.create_msg('12345678', Msg.NONE)
        self.assertEqual(m1, m2)

        m2.set_header(Msg.H_MSGTYPE, Msg.A_HEARTBEAT)
        self.assertNotEqual(m1, m2)

        m1.set_header(Msg.H_MSGTYPE, Msg.A_HEARTBEAT)
        self.assertEqual(m1, m2)

        m1.set_body("123")
        self.assertNotEqual(m1, m2)

    def test_encode_decode(self):
        msg_body = "12\n\t\n\t34"
        msg = Msg.create_msg('12345678', Msg.A_HEARTBEAT, msg_body)
        self.assertEqual(Msg.A_HEARTBEAT, msg.msg_type)

        header_list, encbody = msg.encode()
        self.assertEqual(2, len(header_list))
        self.assertEqual(msg_body, pickle.loads(base64.b64decode(encbody)))

        msg1 = Msg.decode(header_list, encbody)
        self.assertEqual(msg, msg1)
        self.assertIsNone(msg1.send_at)


if __name__ == '__main__':
    unittest.main()
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
        self.assertEqual('"2018-01-08T17:26:26Z"', json_dt)

        d = dt.date()
        json_d = dump_json(d)
        self.assertEqual('"2018-01-08"', json_d)

        t = dt.time()
        json_t = dump_json(t)
        self.assertEqual('"17:26:26"', json_t)

    def test_loadjson_date(self):
        json_dt = '{"date":"2018-01-08T17:26:26Z", ' \
                  '"entry1":{"start_dt":"2018-01-08T17:26:27Z", "d":"2018-01-01", "t":"01:01:01"}}'
        dt = load_json(json_dt)
        self.assertEqual('2018-01-08T17:26:26Z', dt['date'].strftime(DATETIME_FMT))
        self.assertEqual('2018-01-01', dt['entry1']['d'].strftime(DATE_FMT))
        self.assertEqual('01:01:01', dt['entry1']['t'].strftime(TIME_FMT))

    def test_interpret_str(self):
        context = {
            'var1': 1,
            'var2': 'v2',
            'var3': 3.33
        }
        self.assertEqual('1abc2', interpret_str('1abc2', context))
        self.assertEqual('1', interpret_str('${var1}', context))
        self.assertEqual('a1-bv2', interpret_str('a${var1}-b${var2}', context))
        self.assertEqual('1v23.33', interpret_str('${var1}${var2}${var3}', context))
        self.assertEqual('default', interpret_str('${v4:default}', context))


class TextTableTest(unittest.TestCase):

    _TABLE = '''
        A     b   c   d   e   f    g   g    
        a1  b1  c1  d1  e1  f1   g1  g2
    1   2   3   4   5   6    7  77
        1.1  2.2  3.3  4.4  5.5  6.6  7.7 77.77
        '''

    def test_creation(self):
        t = TextTable(self._TABLE)

        self.assertTrue(t.has_body)
        self.assertEqual(3, t.size)
        self.assertEqual(8, len(t._hheader))
        self.assertEqual('Abcdefgg', ''.join(t._hheader))
        rows = t.get_rows()
        self.assertEqual(3, len(rows))
        self.assertEqual(('a1', 'b1', 'c1', 'd1', 'e1', 'f1', 'g1', 'g2'), rows[0].as_tuple())
        self.assertEqual(('1', '2', '3', '4', '5', '6', '7', '77'), rows[1].as_tuple())
        self.assertEqual(('1.1', '2.2', '3.3', '4.4', '5.5', '6.6', '7.7', '77.77'), rows[2].as_tuple())

        t = TextTable(self._TABLE, 1)
        self.assertTrue(t.has_body)
        self.assertEqual(2, t.size)
        self.assertEqual(8, len(t._hheader))
        self.assertEqual(('1', '2', '3', '4', '5', '6', '7', '77'), t.get_rows()[0].as_tuple())
        self.assertEqual('a1b1c1d1e1f1g1g2', ''.join(t._hheader))

        t = TextTable(self._TABLE, 2)
        self.assertTrue(t.has_body)
        self.assertEqual(1, t.size)
        self.assertEqual(8, len(t._hheader))
        self.assertEqual(('1.1', '2.2', '3.3', '4.4', '5.5', '6.6', '7.7', '77.77'), t.get_rows()[0].as_tuple())
        self.assertEqual('123456777', ''.join(t._hheader))

    def test_gets(self):
        t = TextTable(self._TABLE)
        r0 = t[0]
        self.assertEqual('a1', t.get(0, 'A'))
        self.assertEqual('a1a1a1', r0['A'] + r0[0] + r0.get('A'))
        self.assertEqual('b1', t.get(0, 'b'))
        self.assertEqual('g1', t.get(0, 'g'))
        self.assertEqual(['g1', 'g2'], t.gets(0, 'g'))
        self.assertIsNone(t.get(0, 'non-exist'))
        self.assertEqual('aa', t.get(0, 'non-exist', 'aa'))

        r1 = t[1]
        self.assertEqual(1, t.get_int(1, 'A'))
        self.assertEqual('1', r1['A'])
        self.assertEqual(1, r1.get_int('A'))
        self.assertEqual(2, t.get_int(1, 'b'))
        self.assertEqual(7, t.get_int(1, 'g'))
        self.assertEqual([7, 77], t.get_ints(1, 'g'))
        self.assertIsNone(t.get(1, 'non-exist'))
        self.assertEqual(8, t.get(1, 'non-exist', 8))

        r2 = t[2]
        self.assertEqual(1.1, t.get_float(2, 'A'))
        self.assertEqual(1.1, r2.get_float('A'))
        self.assertEqual(2.2, t.get_float(2, 'b'))
        self.assertEqual(7.7, t.get_float(2, 'g'))
        self.assertEqual([7.7, 77.77], t.get_floats(2, 'g'))
        self.assertEqual([7.7, 77.77], r2.get_floats('g'))
        self.assertIsNone(t.get(2, 'non-exist'))
        self.assertIsNone(r2.get('non-exist'))
        self.assertEqual(8.8, t.get(1, 'non-exist', 8.8))
        self.assertEqual(8.8, r2.get('non-exist', 8.8))


class MonMsgTest(unittest.TestCase):

    def test_create(self):
        m1 = Msg.create_msg('12345678', Msg.NONE)
        self.assertEqual('12345678', m1.agentid)
        self.assertEqual(Msg.NONE, m1.msg_type)
        self.assertEqual('', m1.body)

    def test_specialchar_header(self):
        msg = Msg.create_msg('123\n456', Msg.A_REG)
        self.assertEqual('123\n456', msg.agentid)

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
        self.assertEqual(msg_body, pickle.loads(standard_b64decode(encbody)))

        msg1 = Msg.decode(header_list, encbody)
        self.assertEqual(msg, msg1)
        self.assertIsNone(msg1.send_at)

    def test_special_char_enc_dec(self):
        msg_body = "12\n\t\n\t34中文"
        msg = Msg.create_msg('1234\n5678', Msg.A_HEARTBEAT, msg_body)
        self.assertEqual(Msg.A_HEARTBEAT, msg.msg_type)

        header_list, encbody = msg.encode()
        self.assertEqual(2, len(header_list))
        self.assertEqual(msg_body, pickle.loads(standard_b64decode(encbody)))

        msg1 = Msg.decode(header_list, encbody)
        self.assertEqual(msg, msg1)
        self.assertIsNone(msg1.send_at)


class YAMLConfigTest(unittest.TestCase):

    def setUp(self):
        self._cfgurl = os.path.join(os.path.dirname(__file__), 'common_test_master.yaml')
        self._cfg = YAMLConfig(self._cfgurl)

    def test_creation(self):
        cfg = self._cfg
        self.assertEqual(self._cfgurl, cfg._url)
        self.assertIsNotNone(cfg._config)
        self.assertTrue(type(cfg['master']) is YAMLConfig)

    def test_get(self):
        cfg = self._cfg
        self.assertEqual("0.0.0.0", cfg['master']['server']['host'])
        self.assertEqual(30079, cfg['master']['server']['port'])
        self.assertEqual('localhost', cfg['master']['database']['tsd']['host'])
        self.assertEqual('4242', cfg['master']['database']['tsd']['port'])

    def test_get_exp(self):
        cfg = self._cfg
        os.environ['TSDB_HOST'] = 'test.tsdb.com'
        os.environ['TSDB_PORT'] = '1234'
        self.assertEqual('test.tsdb.com', cfg['master']['database']['tsd']['host'])
        self.assertEqual('1234', cfg['master']['database']['tsd']['port'])


    def test_setconfig(self):
        with self.assertRaises(ConfigError) as ce:
            self._cfg['test'] = 1
        self.assertEqual('config is immutable.', ce.exception.message)


if __name__ == '__main__':
    unittest.main()
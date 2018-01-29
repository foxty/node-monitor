#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Created on 2017-12-22
@author: foxty
"""
import os
import unittest
from master_cli import download_py, _FILE_OF_PY27, parse_nodelist


class Tests(unittest.TestCase):

    def test_download_py(self):
        download_py()
        self.assertTrue(os.path.exists(_FILE_OF_PY27))
        self.assertEqual(17176758, os.stat(_FILE_OF_PY27).st_size)

    def test_parsenodelist(self):
        nodelist = parse_nodelist('./master_cli_test_nodes.txt')
        self.assertEqual(4, len(nodelist))
        self.assertEqual(('node1', 'root', '123456'), nodelist[0])
        self.assertEqual(('node2', 'root', '123456@!#'), nodelist[1])
        self.assertEqual(('node3', 'root', '0987654321!@#'), nodelist[2])
        self.assertEqual(('node5', 'haha', 'passfree123'), nodelist[3])


if __name__ == '__main__':
    unittest.main()
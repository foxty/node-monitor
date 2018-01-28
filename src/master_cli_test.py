#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Created on 2017-12-22
@author: foxty
"""
import os
import unittest
from master_cli import download_py, _FILE_OF_PY27


class Tests(unittest.TestCase):

    def test_download_py(self):
        download_py()
        self.assertTrue(os.path.exists(_FILE_OF_PY27))
        self.assertEqual(17176758, os.stat(_FILE_OF_PY27).st_size)


if __name__ == '__main__':
    unittest.main()
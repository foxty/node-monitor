#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Created on 2018-6-22
@author: foxty

Build scirpt for node-monitor
"""


import os, sys
import logging
from datetime import timedelta, datetime
from subprocess import check_call, check_output, CalledProcessError

BASE_PATH = sys.path[0]
VERSION = '1.0.0-SNAPSHOT'
DOCKER_IMG_TAG = 'registry.cn-shenzhen.aliyuncs.com/foxty/node-monitor:%s' % VERSION


def run_cmd(title, cmd):
    """
    Checking tools is valid on current platform.
    :return: True/False
    """
    t0 = datetime.now()
    ret = True
    try:
        logging.info(title)
        check_call(cmd, shell=True)
    except CalledProcessError:
        logging.error('run cmd %s failed', cmd)
        ret = False
    t1 = datetime.now()
    logging.info('%s %s, take %s seconds',
                 title,
                 'succeed' if ret else 'failed',
                 (t1 - t0).seconds)
    return ret


def build_ui():
    """
    Build ui component by using webpack and nodejs
    :return:
    """
    logging.info('[ui] build ui component')
    # step 1 install js libs
    ret = run_cmd('[ui] install javascript libraries',
                  ["cd", "web", "&&", "npm", "install", "--production"])
    # step 2 webpack build
    ret = run_cmd('[ui] webpack build', ['cd', 'web', '&&', 'npm', 'run', 'build']) if ret else False

    # step 3 build docker image for UI
    # TODO
    logging.info('')
    return ret


def build_master():
    """
    Build master with Docker
    :return:
    """
    logging.info('[master] build master')
    ret = run_cmd('[master] build docker image %s' % DOCKER_IMG_TAG,
                  ['docker', 'build', '-t', DOCKER_IMG_TAG, '.'])

    ret = run_cmd('push docker image %s'% DOCKER_IMG_TAG, ['docker', 'push', DOCKER_IMG_TAG]) if ret else False
    logging.info('')
    return ret


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    start = datetime.now()
    logging.info('start build node-monitor@%s...', VERSION)
    res = build_ui() and build_master()
    logging.info('node-monitor@%s build %s, take %s seconds',
                 VERSION,
                 'succeed' if res else 'failed.',
                 (datetime.now() - start).seconds)


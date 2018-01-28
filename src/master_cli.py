#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Created on 2017-12-22
@author: foxty

"""
# ==============================
#   Master Cli and scripts
# ==============================
import os
import sys
import socket
import logging
from multiprocessing import Process
from common import SetupError
from master import master_main
from master_ui import ui_main
_FILES_TO_COPY = ['common.py', 'agent.py', 'agent.json']
_INSTALL_PY27 = True
_FILE_OF_PY27 = 'Python-2.7.14.tgz'


class NodeConnector(object):
    """Using ssh connect to node and provide list of operation utils"""

    APP_DIR = 'node_monitor'

    def __init__(self, node_host, username, password):
        self.node_host = node_host
        self.username = username
        self.password = password

    def __enter__(self):
        from paramiko import SSHClient, AutoAddPolicy
        self.ssh = SSHClient()
        self.ssh.set_missing_host_key_policy(AutoAddPolicy())
        logging.info('checking node %s', self.node_host)
        self.ssh.connect(hostname=self.node_host, username=self.username, password=self.password)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.ssh.close()
        logging.info('exit node collector from %s', self.node_host)

    def py27_installed(self):
        ins, ous, ers = self.ssh.exec_command('python -V')
        out_msg = ous.readline()
        err_msg = ers.readline()
        logging.debug('out=%s, err=%s', out_msg, err_msg)
        return 'Python 2.7' in (out_msg or err_msg)

    def install_py(self, filename):
        logging.info('install %s ...', filename)
        ins, outs, errs = self.ssh.exec_command('tar xvfz %s/Python-2.7.14.tgz && cd Python-2.7.14 '
                                                '&& ./configure && make && make install && python2 -V' %
                                                self.APP_DIR)
        if self.py27_installed():
            logging.info('%s installed success.', filename)
        else:
            logging.error(errs.readlines())
            raise SetupError('install py27 failed.')

    def trans_files(self, files=[]):
        with self.ssh.open_sftp() as sftp:
            dirs = sftp.listdir()
            if  self.APP_DIR not in dirs:
                # already have nodem folder
                logging.info('%s not exist in home, create it', self.APP_DIR)
                sftp.mkdir(self.APP_DIR)
            logging.info('copying files %s to node', files)
            for f in files:
                sftp.put(f, '%s/%s' % (self.APP_DIR, f))
                logging.info('file %s transferred successfully', f)

    def launch_agent(self, mhost):
        """Launch remote agent via ssh channel"""
        logging.info('start agent on %s, master=%s', self.node_host, mhost)
        self.ssh.exec_command('cd %s && nohup python ./agent.py %s > agent.log 2>&1 & ' %
                              (self.APP_DIR, mhost))
        logging.info('agent started on host %s', mhost)

    def stop_agent(self):
        """Stop agent in remote node"""
        logging.info('try to stop agent on %s', self.node_host)
        self.ssh.exec_command("ps -ef|grep agent.py | grep -v grep| awk '{print $2}' | xargs kill -9")
        logging.info('agent on %s stopped', self.node_host)


def download_py():
    """Download python installation package from www

    py2:https://www.python.org/ftp/python/2.7.14/Python-2.7.14.tgz
    py3:https://www.python.org/ftp/python/3.6.4/Python-3.6.4.tgz
    """
    logging.info('start download %s', _FILE_OF_PY27)
    import requests
    r = requests.get('https://www.python.org/ftp/python/2.7.14/Python-2.7.14.tgz')
    with file(_FILE_OF_PY27, 'wb') as f:
        f.write(r.content)


def push_to_nodes(nodelist):
    """push agent script to remote node and start the agent via ssh
    node list should contains list of tuple like (host, userame, password)
    """
    mhost = socket.gethostbyaddr(socket.gethostname())[0]
    for node in nodelist:
        host, user, password = node
        with NodeConnector(host, user, password) as nc:
            logging.info('checking node %s', host)
            need_py27 = _INSTALL_PY27 and not nc.py27_installed()
            if need_py27:
                if not os.path.exists(_FILE_OF_PY27):
                    download_py()
                nc.trans_files(_FILES_TO_COPY + [_FILE_OF_PY27])
                nc.install_py(_FILE_OF_PY27)
            else:
                nc.trans_files(_FILES_TO_COPY)
                logging.info('py27 already installed, skip installation process.')
            nc.stop_agent()
            nc.launch_agent(mhost)
    return nodelist


if __name__ == '__main__':

    # try:
    #     opts, args = getopt.getopt(sys.argv[:], "hma:", ['help', 'master', 'agent='])
    # except getopt.GetoptError as e:
    #     print('Wrong usage')
    #     sys.exit(2)
    #
    # for opt, v in opts:
    #     if opt in ['-m', '--master']:
    nodelist = [
        #('cycad.ip.lab.chn.arrisi.com', 'root', 'no$go^'),
        ('saaszdev107.ip.lab.chn.arrisi.com', 'root', 'no$go^')
    ]

    if 'push' in sys.argv:
        push_to_nodes(nodelist)
    else:
        master_proc = Process(target=master_main)
        masterui_proc = Process(target=ui_main)
        master_proc.start()
        logging.info('master backend process started: %s', master_proc)
        masterui_proc.start()
        logging.info('master ui process started: %s', masterui_proc)

        master_proc.join()
        masterui_proc.join()
        logging.info('master exited.')
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
import getopt
from multiprocessing import Process
from common import SetupError, OSType
_FILES_TO_COPY = ['common.py', 'agent.py', 'agent_service_solaris.xml', 'nmagent.sh']
_VALID_PY = ['Python 2.4', 'Python 2.5', 'Python 2.6', 'Python 2.7']
_INSTALL_PY27 = True
_FILE_OF_PY27 = 'Python-2.7.14.tgz'


class NodeConnector(object):
    """Using ssh connect to node and provide list of operation utils"""

    APP_DIR = 'node-monitor'

    def __init__(self, node_host, username, password):
        self.node_host = node_host
        self.username = username
        self.password = password
        self.ostype = OSType.LINUX

    def __enter__(self):
        from paramiko import SSHClient, AutoAddPolicy
        self.ssh = SSHClient()
        self.ssh.set_missing_host_key_policy(AutoAddPolicy())
        logging.info('connect to node %s', self.node_host)
        self.ssh.connect(hostname=self.node_host, username=self.username, password=self.password)
        success, message = self.exec_cmd('uname')
        if success:
            self.ostype = OSType.SUNOS if 'SunOS' in message[0] else OSType.LINUX
            logging.info('remote os type was %s' % self.ostype)
        else:
            logging.warn('can\'t detect os type use %s as default' % self.ostype)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.ssh.close()
        logging.info('exit node collector from %s', self.node_host)

    def exec_cmd(self, cmd):
        """
        Execute cmd in remote server.
        :param cmd:
        :return: (success, messages)
        """
        _, stdout, stderr = self.ssh.exec_command(cmd)
        out = stdout.readlines()
        err = stdout.readlines()
        return len(err) == 0, out + err

    def is_py_installed(self):
        ins, ous, ers = self.ssh.exec_command('python -V')
        out_msg = ous.readline()
        err_msg = ers.readline()
        logging.debug('out=%s, err=%s', out_msg, err_msg)
        return len([py for py in _VALID_PY if py in (out_msg or err_msg)]) > 0

    def install_py(self, filename):
        logging.info('install %s ...', filename)
        ins, outs, errs = self.ssh.exec_command('tar xvfz %s/Python-2.7.14.tgz && cd Python-2.7.14 '
                                                '&& ./configure && make && make install && python2 -V' %
                                                self.APP_DIR)
        if self.is_py_installed():
            logging.info('%s installed success.', filename)
        else:
            logging.error('\n'.join(errs.readlines()))
            raise SetupError('install py27 failed.')

    def trans_files(self, files=[]):
        """
        send files to remote host and convert to unix file.
        :param files:
        :return:
        """
        with self.ssh.open_sftp() as sftp:
            dirs = sftp.listdir()
            if self.APP_DIR not in dirs:
                logging.info('%s not exist in home, create it', self.APP_DIR)
                sftp.mkdir(self.APP_DIR)
            logging.info('copying files %s to node', files)
            for f in files:
                sftp.put(f, '%s/%s' % (self.APP_DIR, f))
                self.exec_cmd('dos2unix %s/%s %s/%s.1' % (self.APP_DIR, f, self.APP_DIR, f))
                self.exec_cmd('mv %s/%s.1 %s/%s' % (self.APP_DIR, f, self.APP_DIR, f))
                logging.info('file %s transferred successfully', f)

    def install_service(self, mhost):
        logging.info('install agent service on %s[%s]', self.node_host, self.ostype)
        self.exec_cmd("sed 's/master_host/%s/' %s/nmagent.sh > /etc/init.d/nmagent" %
                      (mhost, self.APP_DIR))
        self.exec_cmd('chmod +x /etc/init.d/nmagent')
        if self.ostype == OSType.LINUX:
            self.exec_cmd('chkconfig --add nmagent')
        else:
            self.exec_cmd('svccfg import %s' % self.APP_DIR + '/agent_service_solaris.xml')

    def launch_agent(self, mhost):
        """Launch remote agent via ssh channel"""
        cmd = 'service nmagent start' if self.ostype == OSType.LINUX else 'svcadm enable nmagent'
        success, message = self.exec_cmd(cmd)
        if success:
            logging.info('agent started on node %s, message=%s', self.node_host, message)
        else:
            logging.error('failed to start agent on node %s, message=%s', self.node_host, message)

    def stop_agent(self):
        """Stop agent in remote node"""
        logging.info('try to stop agent on %s', self.node_host)
        cmd = 'service nmagent stop' if self.ostype == OSType.LINUX else 'svcadm disable nmagent'
        success, message = self.exec_cmd(cmd)
        if success:
            logging.info('agent stopped on %s' % self.node_host)
        else:
            logging.warn('faile to stop agent on %s, error=%s', self.node_host, message)


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


def parse_nodelist(path):
    with open(path, 'r') as nf:
        return [tuple(field.strip() for field in line.strip().split(','))
                for line in nf.readlines() if line.strip() and not line.strip().startswith('#')]


def push_to_nodes(nodelist):
    """push agent script to remote node and start the agent via ssh
    node list should contains list of tuple like (host, userame, password)
    """
    logging.info('star pushing to nodes %s', nodelist)
    mhost = socket.gethostbyaddr(socket.gethostname())[0]
    for node in nodelist:
        host, user, password = node
        try:
            with NodeConnector(host, user, password) as nc:
                logging.info('checking node %s', host)
                need_py27 = _INSTALL_PY27 and not nc.is_py_installed()
                if need_py27:
                    logging.info('no suitble python, now intall python 2.7 to %s' % host)
                    if not os.path.exists(_FILE_OF_PY27):
                        download_py()
                    nc.trans_files(_FILES_TO_COPY + [_FILE_OF_PY27])
                    nc.install_py(_FILE_OF_PY27)

                nc.trans_files(_FILES_TO_COPY)
                nc.stop_agent()
                nc.install_service(mhost)
                nc.launch_agent(mhost)
        except Exception as e:
            logging.exception('error while push to %s', host)
    return nodelist


def stop_agents(nodes):
    for node in nodes:
        host, user, password = node
        try:
            with NodeConnector(host, user, password) as nc:
                nc.stop_agent()
        except Exception as e:
            logging.exception('error while stop agnet on %s', host)


def usage():
    pass


if __name__ == '__main__':
    logging.info('starting master cli:')
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hi:p:m", ['help', 'install=', 'push=', 'master', 'stop-agents='])
    except getopt.GetoptError as e:
        print('Wrong usage', e)
        sys.exit(2)
    for opt, v in opts:
        if opt in ['-p', '--push', '-i', '--install']:
            with open(v, 'r') as f:
                nodelist = [[ele.strip() for ele in l.strip().split(',')]
                            for l in f.readlines() if l.strip() and not l.strip().startswith('#')]
            push_to_nodes(nodelist)
        elif opt in ['-m', '--master']:
            from master import master_main
            from master_ui import ui_main
            master_proc = Process(target=master_main)
            masterui_proc = Process(target=ui_main)
            master_proc.start()
            logging.info('master backend process started: %s', master_proc)
            masterui_proc.start()
            logging.info('master ui process started: %s', masterui_proc)

            master_proc.join()
            masterui_proc.join()
            logging.info('master exited.')
        elif opt == '--stop-agents':
            with open(v, 'r') as f:
                nodelist = [[ele.strip() for ele in l.strip().split(',')]
                            for l in f.readlines() if l and not l.strip().startswith('#') and l.strip()]
            stop_agents(nodelist)
        elif opt in ['-h', '--help']:
            logging.info('print help')
        else:
            print('invalid options %s', ' '.join(sys.argv))
            exit(-1)
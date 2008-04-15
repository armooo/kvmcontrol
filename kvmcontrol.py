#!/usr/bin/python

import sys
import os
import errno
import glob
import subprocess
import socket

class KVMException(Exception):
    pass

class KVM:
    def __init__(self, path):
        self.path = path

    def getOptions(self):
        DISK_NAMES = ['fda', 'fdb', 'hda', 'hdb', 'hdc', 'hdd', 'cdrom']

        opts = []
        for disk_name in DISK_NAMES:
            files = glob.glob( os.path.join(self.path, disk_name + '*') )
            if len(files) == 1:
                opts.append('-' + disk_name)
                opts.append(files[0])

        conf_path = os.path.join(self.path, 'conf')
        if os.path.exists(conf_path):
            for file_name in os.listdir(conf_path):
                file_path = os.path.join(conf_path, file_name)
                for line in open(file_path):
                    opts.append('-' + os.path.basename(file_name))
                    value = line.strip()
                    if value:
                        opts.append(value)

        return opts

    def getPid(self):
        pid_file = os.path.join( self.path, 'pid')
        if os.path.exists(pid_file):
            pid = open(pid_file).read(256).strip()
            return int(pid)
        else:
            return None

    def setPid(self,pid):
        pid_file = os.path.join( self.path, 'pid')
        if pid == None:
            os.unlink(pid_file)
        else:
            open(pid_file, 'w').write(str(pid))

    def getMonPort(self):
        monport_file = os.path.join( self.path, 'monport')
        if os.path.exists(monport_file):
            monport = open(monport_file).read(256).strip()
            return int(monport)
        else:
            return None

    def setMonPort(self, port):
        monport_file = os.path.join( self.path, 'monport')
        if port == None:
            os.unlink(monport_file)
        else:
            open(monport_file, 'w').write(str(port))

    def isRunning(self):
        pid = self.getPid()
        if pid:
            try:
                os.kill(pid, 0)
            except os.error, e:
                if e.errno == errno.ESRCH:
                    self.setPid(None)
                    return False
                else:
                    return True
            else:
                return True

        return False

    def sendMonComand(self, command):
        port = self.getMonPort()
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(('localhost', port))
        s.send(command + '\r\n')

    def start(self):
        if self.isRunning():
            raise KVMException('Already running')

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(('', 0))
        monport = s.getsockname()[1]
        del s

        opts = []
        opts.append('kvm')
        opts.append('-monitor')
        opts.append('tcp:localhost:%s,server,nowait' % monport)
        opts.extend(self.getOptions())

        p = subprocess.Popen(opts)
        self.setPid(p.pid)
        self.setMonPort(monport)
        print 'Started (pid %s)' % p.pid

    def stop(self):
        if not self.isRunning():
            raise KVMException('Not running')

        pid = self.getPid()
        os.kill(pid, 15)
        self.setPid(None)
        self.setMonPort(None)
        print 'Stoped (pid %s)' % pid


    def info(self):
        print '\tOptions: '
        for opt in self.getOptions():
            if opt.startswith('-'):
                print '\t\t%s ' % opt,
            else:
                print opt

        if self.isRunning():
            print 'Running (pid %s)' % self.getPid()
        else:
            print 'Stopped'

    def reboot(self):
        self.sendMonComand('system_reset')
        print 'Rebooted'

def usage():
    print '<start|stop|info> [machine dir]*'

def main(argv):
    OPTIONS = {
        'start' : KVM.start,
        'stop' : KVM.stop,
        'info' : KVM.info,
        'reboot' : KVM.reboot,
    }

    option = argv[1]
    machines = argv[2:]

    if option not in OPTIONS:
        usage()

    for machine in machines:
        if os.path.isdir(machine):
            print 'Machine %s' % os.path.basename(machine)
            m = KVM(machine)
            try:
                OPTIONS[option](m)
            except KVMException, e:
                print e
            print

if __name__ == '__main__':
    main(sys.argv)


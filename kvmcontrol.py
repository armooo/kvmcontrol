#!/usr/bin/python

import sys
import os
import errno
import glob
import subprocess
import socket
import stat
import random
import string

class KVMException(Exception):
    pass

class KVM:

    def __init__(self, path):
        self.path = path
        self.taps = []

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

    def getVNCDisplay(self):
        vnc_file = os.path.join( self.path, 'vnc')
        if os.path.exists(vnc_file):
            vncdisplay = open(vnc_file).read(256).strip()
            return int(vncdisplay)
        else:
            return None

    def setVNCDisplay(self, vncdisplay):
        vnc_file = os.path.join( self.path, 'vnc')
        if vncdisplay == None:
            os.unlink(vnc_file)
        else:
            open(vnc_file, 'w').write(str(vncdisplay))

    def getVNCPassword(self):
        vncpass_file = os.path.join( self.path, 'vncpass')
        if os.path.exists(vncpass_file):
            password = open(vncpass_file).read(256).strip()
            return password
        else:
            return None

    def setVNCPassword(self, password):
        vncpass_file = os.path.join( self.path, 'vncpass')
        if password == None:
            os.unlink(vncpass_file)
        else:
            f = open(vncpass_file, 'w')
            os.chmod(vncpass_file, stat.S_IRUSR | stat.S_IWUSR)
            f.write(str(password))

        self.sendMonComand('change vnc password\r\n%s\r\n' % password)

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
        mon_socket = os.path.join(self.path, 'mon')
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.connect(mon_socket)
        s.send(command + '\r\n')

    def start(self):
        if self.isRunning():
            raise KVMException('Already running')

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(('', 0))
        vncdisplay = s.getsockname()[1] - 5900
        del s

        mon_socket = os.path.join(self.path, 'mon')

        password = ''.join([random.choice(string.printable) for i in range(8)])

        opts = []
        opts.append('kvm')
        opts.append('-monitor')
        opts.append('unix:%s,server,nowait' % mon_socket)
        opts.append('-vnc')
        opts.append('localhost:%s' % vncdisplay)
        opts.append('-usbdevice')
        opts.append('tablet')

        opts.extend(self.getOptions())

        p = subprocess.Popen(opts)
        self.setPid(p.pid)
        self.setVNCDisplay(vncdisplay)

        #VNC passwords don't seem to want to work
        #while not os.path.exists(mon_socket):
        #    pass
        #self.setVNCPassword(password)
        print 'Started (pid %s)' % p.pid

    def stop(self):
        if not self.isRunning():
            raise KVMException('Not running')

        mon_socket = os.path.join(self.path, 'mon')

        pid = self.getPid()
        os.kill(pid, 15)
        self.setPid(None)
        self.setVNCDisplay(None)
        os.unlink(mon_socket)
        print 'Stoped (pid %s)' % pid

    def info(self):
        print '\tOptions: '
        for opt in self.getOptions():
            if opt.startswith('-'):
                print '\t\t%s ' % opt,
            else:
                print opt
        self. status()

    def status(self):
        if self.isRunning():
            print 'Running (pid %s)' % self.getPid()
        else:
            print 'Stopped'

    def reboot(self):
        self.sendMonComand('system_reset')
        print 'Rebooted'

    def display(self):
        if not self.isRunning():
            raise KVMException('Not running')

        opts = []
        opts.append('vncviewer')
        opts.append('-Log=*:stderr:0')
        opts.append('-passwd')
        opts.append( os.path.join(self.path, 'vncpass') )
        opts.append('localhost:%s' % (self.getVNCDisplay() + 5900))
        #my vnc viewer like uses port numbers when the value is over 100

        p = subprocess.Popen(opts)


    OPTIONS = {
        'start' : start,
        'stop' : stop,
        'info' : info,
        'reboot' : reboot,
        'display' : display,
        'status' : status,
    }



def usage():
    print '<%s> [machine dirs]' % ('|'.join(KVM.OPTIONS.keys()))

def main(argv):

    option = argv[1]
    machines = argv[2:]

    if option not in KVM.OPTIONS:
        usage()
        return

    for machine in machines:
        if os.path.isdir(machine):
            if machine.endswith('/'):
                machine = machine[:-1]
            print 'Machine %s' % os.path.basename(machine)
            m = KVM(machine)
            try:
                KVM.OPTIONS[option](m)
            except KVMException, e:
                print e
            print

if __name__ == '__main__':
    main(sys.argv)


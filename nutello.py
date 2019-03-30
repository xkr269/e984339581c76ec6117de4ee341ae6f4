#! /usr/bin/python

"""
Python interface for Tello Drone

"""

import socket
import threading
import sys
from datetime import datetime
import time

class Stats:
    def __init__(self, command, id):
        self.command = command
        self.response = None
        self.id = id

        self.start_time = datetime.now()
        self.end_time = None
        self.duration = None

    def add_response(self, response):
        self.response = response
        self.end_time = datetime.now()
        self.duration = self.get_duration()

    def get_duration(self):
        diff = self.end_time - self.start_time
        return diff.total_seconds()

    def print_stats(self):
        print '\nid: %s' % self.id
        print 'command: %s' % self.command
        print 'response: %s' % self.response
        print 'start time: %s' % self.start_time
        print 'end_time: %s' % self.end_time
        print 'duration: %s\n' % self.duration

    def got_response(self):
        if self.response is None:
            return False
        else:
            return True

    def return_stats(self):
        _str = ''
        _str +=  '\nid: %s\n' % self.id
        _str += 'command: %s\n' % self.command
        _str += 'response: %s\n' % self.response
        _str += 'start time: %s\n' % self.start_time
        _str += 'end_time: %s\n' % self.end_time
        _str += 'duration: %s\n' % self.duration
        return _str


class Tello:
    def __init__(self):
        self.local_ip = ''
        self.local_port = 8889
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # socket for sending cmd
        self.socket.bind((self.local_ip, self.local_port))

        # thread for receiving cmd ack
        self.receive_thread = threading.Thread(target=self._receive_thread)
        self.receive_thread.daemon = True
        self.receive_thread.start()

        self.tello_ip = '192.168.10.1'
        self.tello_port = 8889
        self.tello_adderss = (self.tello_ip, self.tello_port)
        self.log = []

        self.MAX_TIME_OUT = 15.0

    def send_command(self, command):
        """
        Send a command to the ip address. Will be blocked until
        the last command receives an 'OK'.
        If the command fails (either b/c time out or error),
        will try to resend the command
        :param command: (str) the command to send
        :param ip: (str) the ip of Tello
        :return: The latest command response
        """
        self.log.append(Stats(command, len(self.log)))

        self.socket.sendto(command.encode('utf-8'), self.tello_adderss)
        print 'sending command: %s to %s' % (command, self.tello_ip)

        start = time.time()
        while not self.log[-1].got_response():
            now = time.time()
            diff = now - start
            if diff > self.MAX_TIME_OUT:
                print 'Max timeout exceeded... command %s' % command
                # TODO: is timeout considered failure or next command still get executed
                # now, next one got executed
                return "NOK"
        print 'Done!!! sent command: %s to %s' % (command, self.tello_ip)
        return "OK"

    def _receive_thread(self):
        """Listen to responses from the Tello.
        Runs as a thread, sets self.response to whatever the Tello last returned.
        """
        while True:
            try:
                self.response, ip = self.socket.recvfrom(1024)
                print('from %s: %s' % (ip, self.response))

                self.log[-1].add_response(self.response)
            except socket.error, exc:
                print "Caught exception socket.error : %s" % exc

    def on_close(self):
        pass
        # for ip in self.tello_ip_list:
        #     self.socket.sendto('land'.encode('utf-8'), (ip, 8889))
        # self.socket.close()

    def get_log(self):
        return self.log







#######################       MAIN FUNCTION       ##################

commands = ["command"]
commands.append("takeoff")
commands.append("go 100 50 0 100")
# commands.append("forward 50")
commands.append("cw 180")
commands.append("go 100 50 0 100")
# commands.append("forward 50")
commands.append("land")


def main():
    start_time = str(datetime.now())

    tello = Tello()
    for command in commands:
        if command != '' and command != '\n':
            command = command.rstrip()

            if command.find('delay') != -1:
                sec = float(command.partition('delay')[2])
                print 'delay %s' % sec
                time.sleep(sec)
                pass
            else:
                status = tello.send_command(command)
                if command.find('takeoff') != -1:
                    time.sleep(5)
                if status == "NOK"
                    command = "land"
                    tello.send_command(command)


    log = tello.get_log()

    for stat in log:
        stat.print_stats()



if __name__ == '__main__':
    main()

import os
from subprocess import Popen, PIPE, TimeoutExpired
import psutil
from threading import Thread
import threading
from time import sleep


def open_hole(localport):
    l = open("stunlist.txt","r")
    s_r = open("stun_resp.txt", "w+")
    abriu=False
    for line in l:
        cmd = "../stunserver/client/stunclient "+line.split()[0]+" "+line.split()[1]+" --localport "+str(localport)
        stun_req = Popen(cmd.split(),stdout=s_r)
        try:
            stun_req.wait(5)
            abriu = True
        except TimeoutExpired:
            parent = psutil.Process(stun_req.pid)
            for child in parent.children(recursive=True):
                child.kill()
            parent.kill()
        if abriu:
            s_r.flush()
            s_r.seek(0)
            response_lines = s_r.readlines()
            s_r.close()
            try:
                os.remove("stun_resp.txt")
            except FileNotFoundError:
                print("stun_resp.txt nao foi encontrado para ser deletado")
            if len(response_lines) == 3:
                porta_aberta = int(response_lines[2].strip('\n').split(':')[2])
                return porta_aberta
        return 0


class KeepHoleAlive(Thread):

    def __init__(self, socket, secs):
        super(KeepHoleAlive, self).__init__()
        self.socket = socket
        self._stop_event = threading.Event()
        self.secs=secs

    def keep_alive(self):
        while not self.stopped():
            self.socket.sendto("graduation project. contact: thomasovaletec@gmail.com".encode('utf-8'), ("1.1.1.1", 20000))
            sleep(self.secs)

    def run(self) -> None:
        self.keep_alive()

    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()



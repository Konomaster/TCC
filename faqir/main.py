import socket
import threading
from time import sleep
from subprocess import Popen, TimeoutExpired
import iperf3
import psutil
from stun import open_hole, KeepHoleAlive

import io
import sys

class PoC:
    def __init__(self):
        self.listaPares=[]
        self.public_address=""
        self.hole_port1=0
        self.public_port1=0

        self.porta_udp = 37710
        self.s2 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        #i think its not necessary
        self.hole_address = ""

        self.testDone = False

    def makeTest(self,direcao):

        ipPeer, idPeer = "", ""
        portaPeer, portaCanal = 0, 0

        for i in range(0, len(self.listaPares)):
            par = self.listaPares[i].split(',')
            if par[0] != self.public_address and int(par[3]) == self.hole_port1:
                ipPeer, portaPeer, idPeer, portaCanal = self.listaPares[i].split(',')

        portaPeer = int(portaPeer)
        portaCanal = int(portaCanal)

        if portaPeer == 0:
            return

        # proceeds to do testing
        myMappedAddr = list(map(int, self.public_address.split('.')))
        peerMappedAddr = list(map(int, ipPeer.split('.')))

        # 0 to server, 1 to client
        clientOrServer = -1
        if direcao == "normal":
            if self.public_port1 > portaPeer:
                clientOrServer = 1
            elif self.public_port1 < portaPeer:
                clientOrServer = 0
            elif myMappedAddr > peerMappedAddr:
                clientOrServer = 1
            elif myMappedAddr < peerMappedAddr:
                clientOrServer = 0
        elif direcao == "reverso":
            if self.public_port1 > portaPeer:
                clientOrServer = 0
            elif self.public_port1 < portaPeer:
                clientOrServer = 1
            elif myMappedAddr > peerMappedAddr:
                clientOrServer = 0
            elif myMappedAddr < peerMappedAddr:
                clientOrServer = 1

        if clientOrServer==1:
            sleep(7)
            c = iperf3.Client()
            c.server_hostname = "localhost"
            c.port = 5000
            # hole punch eh udp
            c.protocol = 'udp'
            # deixar iperf determinar o tamanho do bloco
            c.blksize = 0
            # trocar esse valor depois pelo que der no tcp
            c.bandwidth = 1000000

            cmd = "socat -d -d tcp-listen:5000,reuseaddr udp:3.83.34.94:2001,sp=2001"
            cmd2 = "socat -d -d udp-listen:5000,reuseaddr udp:3.83.34.94:2000,sp=2000"
            '''
                   socat -d -d tcp-listen:5000,reuseaddr udp:3.83.34.94:2001,sp=2001
                   socat -d -d udp-listen:5000,reuseaddr udp:3.83.34.94:2000,sp=2000
            '''

            print(cmd)
            print(cmd2)

            tunnelTCP_UDP = Popen(cmd.split())
            tunnelUDP = Popen(cmd2.split())

            try:
                c.run()
            except:
                print("erro no teste (cliente)")

            # fecha os tuneis
            parent = psutil.Process(tunnelTCP_UDP.pid)
            for child in parent.children(recursive=True):
                child.kill()
            parent.kill()

            parent = psutil.Process(tunnelUDP.pid)
            for child in parent.children(recursive=True):
                child.kill()
            parent.kill()
        elif clientOrServer==0:
            cmd = "socat -d -d udp-listen:2001,reuseaddr tcp:localhost:2000"
            #    socat -d -d udp-listen:2001,reuseaddr tcp:localhost:2000
            print(cmd)

            tunnelUDP_TCP = Popen(cmd.split())

            cmdServer = "iperf3 -1 -s -p 2000"
            iperf = Popen(cmdServer.split())

            try:
                iperf.wait(30)
            except TimeoutExpired:
                print("timeout do server")

            parent = psutil.Process(tunnelUDP_TCP.pid)
            for child in parent.children(recursive=True):
                child.kill()
            parent.kill()

    def listen(self):
        if self.porta_udp>0:
            try:
                self.s2.bind(('0.0.0.0',self.porta_udp))
            except:
                print("erro ao fazer bind do socket na porta 37710")
                #esse exit so sai da thread
                #pensar como fechar o programa se esse bind nao funcionar
                exit(1)

        while True:

            dataa,sender = self.s2.recvfrom(1024)
            decodedData=dataa.decode('utf-8')
            splitData=decodedData.split(',')
            if splitData[0]=="add" and (splitData[1]+","+splitData[2]+","+splitData[3]+","+splitData[4]) not in self.listaPares:
                self.listaPares.append((splitData[1]+","+splitData[2]+","+splitData[3]+","+splitData[4]))
            elif splitData[0]=="remove" and (splitData[1]+","+splitData[2]+","+splitData[3]+","+splitData[4]) in self.listaPares:
                self.listaPares.remove((splitData[1]+","+splitData[2]+","+splitData[3]+","+splitData[4]))
            elif splitData[0]=="holeport":
                if sender[1] == 37711:
                    self.hole_port1 = int(splitData[1])
                if self.hole_address=="":
                    self.hole_address=splitData[2]
                #talvez dexar sempre sobescrever as portas publicas
                if self.public_port1==0:
                    self.public_port1=int(splitData[3])
                if self.public_address=="":
                    self.public_address=splitData[4]
            '''
            elif splitData[0]=="serverReady":
                self.serverReady=True
                self.server_udp_hole=int(splitData[1])
                self.server_tcp_hole=int(splitData[2])
            elif splitData[0]=="gonnaTest":
                self.gonnaTest=True
                self.client_udp_hole=int(splitData[1])
                self.client_tcp_hole=int(splitData[2])
            '''
            print('\rpeer: {}\n '.format(decodedData), end='')

    def callTest(self):
        testSucessfull=False
        while True:

            if self.listaPares!=[] and self.hole_port1>0 and not self.testDone:
                self.makeTest("normal")
            sleep(5)

def peerNetwork1():
    #process = Popen(["node", "PeerNetwork.js"], stdout=PIPE)
    #https://stackoverflow.com/questions/18421757/live-output-from-subprocess-command


    filename = 'test.log'
    with io.open(filename, 'wb') as writer, io.open(filename, 'rb', 0) as reader:
        process=Popen("DEBUG=NetworkDHT node ../PeerNetwork.js",stdout=writer,shell=True)
        while process.poll() is None:
            sys.stdout.write(reader.read().decode("utf-8"))
            sleep(0.5)
        # Read the remaining
        sys.stdout.write(reader.read().decode("utf-8"))


def main():
    proof_of_concept = PoC()

    socket_listener = threading.Thread(target=proof_of_concept.listen, daemon=True)
    socket_listener.start()

    call_test = threading.Thread(target=proof_of_concept.callTest, daemon=True)
    call_test.start()
    # listener2 = threading.Thread(target=notPing, daemon=True)
    # listener2.start()

    pnthread1 = threading.Thread(target=peerNetwork1, daemon=True)
    pnthread1.start()

    input("sair?")
    # continueProgram=True
    # while continueProgram:
    #    sleep(2)


if __name__ == '__main__':
    main()
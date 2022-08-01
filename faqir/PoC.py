


import os.path

import socket
import threading
from time import sleep
from subprocess import Popen, PIPE, TimeoutExpired
import iperf3
import psutil
from stun import open_hole, KeepHoleAlive

import io
import sys


class PoC:
    def __init__(self):
        self.listaPares = []
        self.s2=socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.porta_udp = 37710
        self.porta_peernetwork=0
        self.notPinged=False
        self.readyToTest=False
        self.hole_socket=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        self.hole_port1=0
        self.hole_port2=0
        self.hole_address=""
        self.public_port1=0
        self.public_address=""
        self.testDone=False
        self.test2Done=False
        self.serverReady=False
        self.gonnaTest=False
        self.serverRunning=False
        self.server_udp_hole=0
        self.server_tcp_hole=0
        self.client_udp_hole=0
        self.client_tcp_hole=0
        self.iperf_port=5000
        self.udp_local_port=2000
        self.tcp_local_port=2001

    def restartPeerNetwork(self):

        restartString = "endTest," + str(self.hole_port1)
        restartString2 = "endTest," + str(self.hole_port2)
        self.s2.sendto(restartString.encode('utf-8'), ("0.0.0.0", 37711))
        self.s2.sendto(restartString2.encode('utf-8'), ("0.0.0.0", 37712))


    def makeTest(self,direcao):
        testSucessfull=False

        tempLP=self.listaPares

        ipPeer,idPeer="",""
        portaPeer,portaCanal=0,0

        for i in range(0,len(self.listaPares)):
            par=self.listaPares[i].split(',')
            if par[0] != self.public_address and int(par[3]) == self.hole_port1:
                ipPeer, portaPeer, idPeer, portaCanal = self.listaPares[i].split(',')

        portaPeer = int(portaPeer)
        portaCanal= int(portaCanal)

        if portaPeer == 0:
            return

        # proceeds to do testing
        myMappedAddr = list(map(int, self.public_address.split('.')))
        peerMappedAddr = list(map(int, ipPeer.split('.')))

        myPort = self.public_port1
        pPort = portaPeer
        # 0 to server, 1 to client
        clientOrServer = -1
        if direcao=="normal":
            if self.public_port1 > portaPeer:
                clientOrServer = 1
            elif self.public_port1 < portaPeer:
                clientOrServer = 0
            elif myMappedAddr > peerMappedAddr:
                clientOrServer = 1
            elif myMappedAddr < peerMappedAddr:
                clientOrServer = 0
        elif direcao=="reverso":
            if self.public_port1 > portaPeer:
                clientOrServer = 0
            elif self.public_port1 < portaPeer:
                clientOrServer = 1
            elif myMappedAddr > peerMappedAddr:
                clientOrServer = 0
            elif myMappedAddr < peerMappedAddr:
                clientOrServer = 1


        if clientOrServer == 1:

            udp_hole = open_hole(self.udp_local_port)
            tcp_hole = open_hole(self.tcp_local_port)

            if tcp_hole != 0 and udp_hole != 0:
                socket_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                socket_tcp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

                try:
                    socket_udp.bind(("0.0.0.0", self.udp_local_port))
                    socket_tcp.bind(("0.0.0.0", self.tcp_local_port))
                except:
                    print("erro ao dar bind nos sockets do cliente")
                    return

                keep_udp = KeepHoleAlive(socket_udp, 4)
                keep_tcp = KeepHoleAlive(socket_tcp, 4)

                keep_udp.start()
                keep_tcp.start()
            else:
                print("erro ao abrir buracos do cliente")
                return

            c = iperf3.Client()
            c.server_hostname = "localhost"
            c.port = self.iperf_port
            # hole punch eh udp
            c.protocol = 'udp'
            # deixar iperf determinar o tamanho do bloco
            c.blksize = 0
            #trocar esse valor depois pelo que der no tcp
            c.bandwidth=1000000

            # esperar por tantos segundos o servidor falar que ja ta pronto
            # comunicacao vai ser feita pelos sockets da biblioteca antes de fecha-los
            for i in range(0, 3):
                sleep(1)
                if self.serverReady:
                    break

            keep_tcp.stop()
            keep_udp.stop()
            keep_tcp.join()
            keep_udp.join()




            # socket_tcp.sendto("o".encode('utf-8'),(ipPeer,self.server_udp_hole))




            socket_tcp.close()
            socket_udp.close()

            if self.serverReady:

                if self.server_udp_hole == 0 or self.server_udp_hole == 0:
                    print("nao foram recebidos buracos do servidor")
                    return

                # manda msg de confirmacao
                gonnaString = "gonnaTest," + idPeer + "," +str(udp_hole)+ "," +str(tcp_hole)
                self.s2.sendto(gonnaString.encode('utf-8'), ("0.0.0.0", 37711))

                sleep(6)
                #cmd = "socat tcp-listen:"+str(hole_port1)+",reuseaddr,fork udp:" + ipPeer2 + ":" + str(portaPeer2)
                #cmd2 = "socat udp-listen:"+str(hole_port1)+",reuseaddr,fork udp:" + ipPeer + ":" + str(portaPeer)
                cmd = "socat -d -d tcp-listen:"+str(self.iperf_port)+",reuseaddr udp:" + ipPeer + ":" + str(self.server_tcp_hole)+",sp="+str(self.tcp_local_port)
                cmd2 = "socat -d -d udp-listen:"+str(self.iperf_port)+",reuseaddr udp:" + ipPeer + ":" + str(self.server_udp_hole)+",sp="+str(self.udp_local_port)

                print(cmd)
                print(cmd2)

                tunnelTCP_UDP = Popen(cmd.split())
                tunnelUDP = Popen(cmd2.split())

                result = ""
                try:
                    print("cliente iniciando teste")
                    result = c.run()
                except:
                    print('exception no teste (cliente)')
                if result != "":
                    if result.error:
                        print("result error: " + result.error)
                    else:
                        print(result)
                        print("teste concluido com sucesso")
                        self.testDone = True
                        testSucessfull = True

                #fecha os tuneis
                parent = psutil.Process(tunnelTCP_UDP.pid)
                for child in parent.children(recursive=True):
                    child.kill()
                parent.kill()

                parent = psutil.Process(tunnelUDP.pid)
                for child in parent.children(recursive=True):
                    child.kill()
                parent.kill()

                self.server_udp_hole = 0
                self.server_udp_hole = 0

                self.serverReady = False

        elif clientOrServer == 0:

            udp_hole = open_hole(self.udp_local_port)
            tcp_hole = open_hole(self.tcp_local_port)


            if tcp_hole != 0 and udp_hole != 0:
                socket_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                socket_tcp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

                try:
                    socket_udp.bind(("0.0.0.0", self.udp_local_port))
                    socket_tcp.bind(("0.0.0.0", self.tcp_local_port))
                except:
                    print("erro ao dar bind nos sockets do servidor")
                    return

                keep_udp = KeepHoleAlive(socket_udp,4)
                keep_tcp = KeepHoleAlive(socket_tcp,4)

                keep_udp.start()
                keep_tcp.start()
            else:
                print("erro ao abrir buracos do servidor")
                return


            serverString = "serverReady," + idPeer +","+str(udp_hole)+","+str(tcp_hole)
            self.s2.sendto(serverString.encode('utf-8'), ("0.0.0.0", 37711))
            print(serverString)

            for i in range(0, 40):
                sleep(0.5)
                if self.gonnaTest:
                    break

            # para o keep alive dos buracos
            keep_tcp.stop()
            keep_udp.stop()
            keep_tcp.join()
            keep_udp.join()

            if self.client_udp_hole != 0 and self.client_tcp_hole != 0:
                print("furando buracos para peer ip: "+ipPeer)
                #socket_udp.sendto("o".encode('utf-8'), (ipPeer, self.client_udp_hole))
                #socket_tcp.sendto("o".encode('utf-8'), (ipPeer, self.client_tcp_hole))

                #socket_tcp.sendto("o".encode('utf-8'), (ipPeer, self.client_udp_hole))



            socket_tcp.close()
            socket_udp.close()

            if self.gonnaTest:
                #cmd = "socat udp-listen:21202,reuseaddr,fork tcp:localhost:21201"
                cmd = "socat -d -d udp-listen:"+str(self.tcp_local_port)+",reuseaddr tcp:localhost:"+str(self.udp_local_port)
                print(cmd)
                # nao precisa de tunnel udp aqui pq ja vai receber no porto certo
                tunnelTCP_UDP = Popen(cmd.split())

                serverRunning=True
                # fechar o socket do peernetwork (ja foi feito pela biblioteca)
                print("Servidor iniciando")
                cmdserver="iperf3 -s -p "+str(self.udp_local_port)
                s=Popen(cmdserver.split())
                try:
                    s.wait(25)
                except TimeoutExpired:
                    print("matando servs")
                    parent=psutil.Process(s.pid)
                    for child in parent.children(recursive=True):
                        child.kill()
                    parent.kill()
                self.testDone = True
                testSucessfull = True
                # fecha o tunel
                self.serverRunning=False
                parent = psutil.Process(tunnelTCP_UDP.pid)
                for child in parent.children(recursive=True):
                    child.kill()
                parent.kill()
                print("teste concluido com sucesso")
            else:
                print("gonnaTest nao chegou a tempo")

            self.client_udp_hole = 0
            self.client_tcp_hole = 0

            #nao esqueci de resetar o gonnatest, so escolhi nao resetar


    def callTest(self):
        testSucessfull=False
        while True:

            if self.listaPares!=[] and self.hole_port1>0 and not self.testDone:
                self.makeTest("reverso")
            elif self.listaPares!=[] and self.hole_port1>0 and self.testDone and not self.test2Done:
                self.makeTest("normal")
            sleep(5)


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
                elif sender[1] == 37712:
                    self.hole_port2 = int(splitData[1])
                if self.hole_address=="":
                    self.hole_address=splitData[2]
                #talvez dexar sempre sobescrever as portas publicas
                if self.public_port1==0:
                    self.public_port1=int(splitData[3])
                if self.public_address=="":
                    self.public_address=splitData[4]
            elif splitData[0]=="confirmNotPing":
                self.notPinged=True
            elif splitData[0]=="removeNotPing":
                self.notPinged=False
            elif splitData[0]=="serverReady":
                self.serverReady=True
                self.server_udp_hole=int(splitData[1])
                self.server_tcp_hole=int(splitData[2])
            elif splitData[0]=="gonnaTest":
                self.gonnaTest=True
                self.client_udp_hole=int(splitData[1])
                self.client_tcp_hole=int(splitData[2])

            print('\rpeer: {}\n '.format(decodedData), end='')

            #if len(listaPares)>0:

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
    proof_of_concept=PoC()

    socket_listener = threading.Thread(target=proof_of_concept.listen, daemon=True)
    socket_listener.start()

    call_test=threading.Thread(target=proof_of_concept.callTest, daemon=True)
    call_test.start()
    #listener2 = threading.Thread(target=notPing, daemon=True)
    #listener2.start()

    pnthread1 = threading.Thread(target=peerNetwork1, daemon=True)
    pnthread1.start()
    
    input("sair?")
    #continueProgram=True
    #while continueProgram:
    #    sleep(2)
if __name__ == '__main__':
    main()
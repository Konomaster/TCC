


import os.path

import socket
import threading
from time import sleep
from subprocess import Popen, PIPE, TimeoutExpired
import iperf3
import psutil

import io
import sys

listaPares=[]

s2=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
porta_udp=37710
porta_peernetwork=0

notPinged=False
readyToTest=False
hole_socket=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
hole_port1=0
hole_port2=0
hole_address=""
public_port1=0
public_address=""
testDone=False
test2Done=False
serverReady=False
gonnaTest=False
serverRunning=False

def restartPeerNetwork():
    global hole_port1
    global hole_port2
    global hole_address
    global s2

    restartString = "endTest," + str(hole_port1)
    restartString2 = "endTest," + str(hole_port2)
    s2.sendto(restartString.encode('utf-8'), ("0.0.0.0", 37711))
    s2.sendto(restartString2.encode('utf-8'), ("0.0.0.0", 37712))

#colocar uma flag aqui pra definir quem vai ser servidor ou cliente
def makeTest(direcao):

    global notPinged
    global listaPares
    global s2
    global hole_port1
    global hole_port2
    global hole_address
    global public_port1
    global public_address
    global testDone
    global serverReady
    global gonnaTest
    global readyToTest
    global test2Done
    global serverRunning
    testSucessfull=False

    tempLP=listaPares
    indexPeer = 0
    for par in listaPares:
        if par.split(',')[0] == public_address:
            indexPeer += 1
        else:
            break
    # protecao contra null pointer
    if indexPeer > len(listaPares) - 1:
        return


    ipPeer, portaPeer, idPeer = listaPares[indexPeer].split(',')
    portaPeer = int(portaPeer)

    ipPeer2,idPeer2="",""
    portaPeer2=0

    for i in range(indexPeer, len(listaPares)):
        ipC, portaC, idC = listaPares[i].split(',')
        if ipC == ipPeer and portaC != portaPeer:
            ipPeer2=ipC
            portaPeer2=portaC
            idPeer2=idC

    if portaPeer2 == portaPeer or portaPeer2 == 0:
        return

    # tenho que saber meus candidatos ip e porta
    # ou n

    notPingus1 = "notPing," + idPeer
    notPingus2 = "notPing," + idPeer2

    s2.sendto(notPingus1.encode('utf-8'), ("0.0.0.0", 37711))
    s2.sendto(notPingus2.encode('utf-8'), ("0.0.0.0", 37711))
    s2.sendto(notPingus1.encode('utf-8'), ("0.0.0.0", 37712))
    s2.sendto(notPingus2.encode('utf-8'), ("0.0.0.0", 37712))

    print("Python enviou notPing " + idPeer + " e "+idPeer2)

    sleep(2)

    # proceeds to do testing
    if notPinged:
        myMappedAddr = list(map(int, public_address.split('.')))
        peerMappedAddr = list(map(int, ipPeer.split('.')))

        myPort = public_port1
        pPort = portaPeer
        # 0 to server, 1 to client
        clientOrServer = -1
        if direcao=="normal":
            if public_port1 > portaPeer:
                clientOrServer = 1
            elif public_port1 < portaPeer:
                clientOrServer = 0
            elif myMappedAddr > peerMappedAddr:
                clientOrServer = 1
            elif myMappedAddr < peerMappedAddr:
                clientOrServer = 0
        elif direcao=="reverso":
            if public_port1 > portaPeer:
                clientOrServer = 0
            elif public_port1 < portaPeer:
                clientOrServer = 1
            elif myMappedAddr > peerMappedAddr:
                clientOrServer = 0
            elif myMappedAddr < peerMappedAddr:
                clientOrServer = 1
        # se porta e ip for igual da zebra kkkk
        # to mandando continuar pingando
        else:
            doPing = "doPing," + idPeer
            doPing2 = "doPing," + idPeer2

            s2.sendto(doPing.encode('utf-8'), ("0.0.0.0", 37711))
            s2.sendto(doPing2.encode('utf-8'), ("0.0.0.0", 37711))
            s2.sendto(doPing.encode('utf-8'), ("0.0.0.0", 37712))
            s2.sendto(doPing2.encode('utf-8'), ("0.0.0.0", 37712))

            print("Python enviou doPing")

        if clientOrServer == 1:
            c = iperf3.Client()
            c.server_hostname = "localhost"
            c.port = 21201
            # hole punch eh udp
            c.protocol = 'udp'
            # deixar iperf determinar o tamanho do bloco
            c.blksize = 0

            # esperar por tantos segundos o servidor falar que ja ta pronto
            # comunicacao vai ser feita pelos sockets da biblioteca antes de fecha-los
            for i in range(0, 3):
                sleep(1)
                if serverReady:
                    break

            if serverReady:

                # manda msg de confirmacao
                gonnaString = "gonnaTest," + idPeer
                gonnaString2 = "gonnaTest," + idPeer2
                s2.sendto(gonnaString.encode('utf-8'), ("0.0.0.0", 37711))
                s2.sendto(gonnaString2.encode('utf-8'), ("0.0.0.0", 37712))

                sleep(1)
                cmd = "socat tcp-listen:"+hole_port1+",reuseaddr,fork udp:" + ipPeer2 + ":" + str(portaPeer2)
                cmd2 = "socat udp-listen:"+hole_port1+",reuseaddr,fork udp:" + ipPeer + ":" + str(portaPeer)
                tunnelTCP_UDP = Popen(cmd.split())
                tunnelUDP = Popen(cmd2.split())
                sleep(2)
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
                        #fecha os tuneis
                        parent = psutil.Process(tunnelTCP_UDP.pid)
                        for child in parent.children(recursive=True):
                            child.kill()
                        parent.kill()

                        parent = psutil.Process(tunnelUDP.pid)
                        for child in parent.children(recursive=True):
                            child.kill()
                        parent.kill()
                        print(result)
                        print("teste concluido com sucesso")
                        testDone = True
                        testSucessfull = True
                restartPeerNetwork()

        elif clientOrServer == 0:

            serverString = "serverReady," + idPeer
            serverString2 = "serverReady," + idPeer2
            s2.sendto(serverString.encode('utf-8'), ("0.0.0.0", 37711))
            s2.sendto(serverString2.encode('utf-8'), ("0.0.0.0", 37712))
            #
            for i in range(0, 10):
                sleep(0.5)
                if gonnaTest:
                    break
            cmd = "socat udp-listen:21202,reuseaddr,fork tcp:localhost:21201"
            #nao precisa de tunnel udp aqui pq ja vai receber no porto certo
            #cmd2 = "socat udp-listen:21201,reuseaddr,fork tcp:localhost:21201"
            tunnelTCP_UDP = Popen(cmd.split())

            if gonnaTest:
                serverRunning=True
                # fechar o socket do peernetwork (ja foi feito pela biblioteca)
                print("Servidor iniciando")
                cmdserver="iperf3 -s -p 21201"
                try:
                    s=Popen(cmdserver.split()).wait(20)
                except TimeoutExpired:
                    parent=psutil.Process(s.pid)
                    for child in parent.children(recursive=True):
                        child.kill()
                    parent.kill()
                testDone = True
                testSucessfull = True
                # fecha o tunel
                serverRunning=False
                parent = psutil.Process(tunnelTCP_UDP.pid)
                for child in parent.children(recursive=True):
                    child.kill()
                parent.kill()
                print("teste concluido com sucesso")
                restartPeerNetwork()

    # talvez so fazer isso depois que peernetwork tiver reiniciado
    # to mandando continuar pingando
    doPing = "doPing," + idPeer
    doPing2 = "doPing," + idPeer2

    s2.sendto(doPing.encode('utf-8'), ("0.0.0.0", 37711))
    s2.sendto(doPing2.encode('utf-8'), ("0.0.0.0", 37711))
    s2.sendto(doPing.encode('utf-8'), ("0.0.0.0", 37712))
    s2.sendto(doPing2.encode('utf-8'), ("0.0.0.0", 37712))

    print("Python enviou doPing")


def notPing():
    global notPinged
    global listaPares
    global s2
    global hole_port1
    global hole_port2
    global hole_address
    global public_port1
    global public_address
    global testDone
    global serverReady
    global gonnaTest
    global readyToTest
    global test2Done
    testSucessfull=False
    while True:
        lp=listaPares
        hp1=hole_port1
        hp2=hole_port2
        td=testDone
        if listaPares!=[] and hole_port1>0 and hole_port2>0 and not testDone:
            makeTest("normal")
        elif listaPares!=[] and hole_port1>0 and hole_port2>0 and testDone and not test2Done:
            makeTest("reverso")
        sleep(5)
        #    if notPinged:
        #       doPing="doPing,"+listaPares[0].split(',')[2]
        #        s2.sendto(doPing.encode('utf-8'),("0.0.0.0",37711))
        #        print("Python enviou doPing")
        #        notPinged=False
        #    else:
        #        notPingus="notPing,"+listaPares[0].split(',')[2]
        #        s2.sendto(notPingus.encode('utf-8'),("0.0.0.0",37711))
        #        print("Python enviou notPing "+listaPares[0].split(',')[2])
        #        notPinged=True
        #sleep(600)



def listen():
    global porta_udp
    global s2
    global hole_port1
    global hole_port2
    global hole_address
    global public_port1
    global public_address
    global notPinged
    global serverReady
    global gonnaTest
    if porta_udp>0:
        try:
            s2.bind(('0.0.0.0',porta_udp))
        except:
            print("erro ao fazer bind do socket na porta 37710")
            #esse exit so sai da thread
            #pensar como fechar o programa se esse bind nao funcionar
            exit(1)

    while True:

        dataa,sender = s2.recvfrom(1024)
        decodedData=dataa.decode('utf-8')
        splitData=decodedData.split(',')
        if splitData[0]=="add" and (splitData[1]+","+splitData[2]+","+splitData[3]) not in listaPares:
            listaPares.append((splitData[1]+","+splitData[2]+","+splitData[3]))
        elif splitData[0]=="remove" and (splitData[1]+","+splitData[2]+","+splitData[3]) in listaPares:
            listaPares.remove((splitData[1]+","+splitData[2]+","+splitData[3]))
        elif splitData[0]=="holeport":
            if sender[1] == 37711:
                hole_port1 = int(splitData[1])
            elif sender[1] == 37712:
                hole_port2 = int(splitData[1])
            if hole_address=="":
                hole_address=splitData[2]
            #talvez dexar sempre sobescrever as portas publicas
            if public_port1==0:
                public_port1=int(splitData[3])
            if public_address=="":
                public_address=splitData[4]
        elif splitData[0]=="confirmNotPing":
            notPinged=True
        elif splitData[0]=="removeNotPing":
            notPinged=False
        elif splitData[0]=="serverReady":
            serverReady=True
        elif splitData[0]=="gonnaTest":
            gonnaTest=True

        print('\rpeer: {}\n '.format(decodedData), end='')

        #if len(listaPares)>0:

        pass

def peerNetwork1():
    #process = Popen(["node", "PeerNetwork.js"], stdout=PIPE)
    #https://stackoverflow.com/questions/18421757/live-output-from-subprocess-command


    filename = 'test.log'
    with io.open(filename, 'wb') as writer, io.open(filename, 'rb', 0) as reader:
        process=Popen("DEBUG=NetworkDHT node PeerNetwork.js",stdout=writer,shell=True)
        while process.poll() is None:
            sys.stdout.write(reader.read().decode("utf-8"))
            sleep(0.5)
        # Read the remaining
        sys.stdout.write(reader.read().decode("utf-8"))

def peerNetwork2():
    #process = Popen(["node", "PeerNetwork.js"], stdout=PIPE)
    #https://stackoverflow.com/questions/18421757/live-output-from-subprocess-command


    filename = 'test2.log'
    with io.open(filename, 'wb') as writer, io.open(filename, 'rb', 0) as reader:
        process=Popen("DEBUG=NetworkDHT node PeerNetwork2.js",stdout=writer,shell=True)
        while process.poll() is None:
            sys.stdout.write(reader.read().decode("utf-8"))
            sleep(0.5)
        # Read the remaining
        sys.stdout.write(reader.read().decode("utf-8"))

def main():
    listener = threading.Thread(target=listen, daemon=True)
    listener.start()

    listener2= threading.Thread(target=notPing, daemon=True)
    listener2.start()

    pnthread1 = threading.Thread(target=peerNetwork1, daemon=True)
    pnthread1.start()

    pnthread2 = threading.Thread(target=peerNetwork2, daemon=True)
    pnthread2.start()
    
    input("sair?")
    #continueProgram=True
    #while continueProgram:
    #    sleep(2)
if __name__ == '__main__':
    main()



import os.path

import socket
import threading
from time import sleep
from subprocess import Popen, PIPE
import iperf3

import io
import sys

listaPares=[]

s2=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
porta_udp=37710
porta_peernetwork=0

notPinged=False
readyToTest=False
hole_socket=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
hole_port=0
hole_address=""
public_port=0
public_address=""
testDone=False
test2Done=False
serverReady=False
gonnaTest=False

def restartPeerNetwork():
    global hole_port
    global hole_address
    global s2

    restartString = "endTest," + str(hole_port)
    s2.sendto(restartString.encode('utf-8'), ("0.0.0.0", 37711))

def notPing():
    global notPinged
    global listaPares
    global s2
    global hole_port
    global hole_address
    global public_port
    global public_address
    global testDone
    global serverReady
    global gonnaTest
    global readyToTest
    global test2Done
    testSucessfull=False
    while True:
        if listaPares==[]:
            sleep(5)
            continue
        elif hole_port>0 and not testDone:
            indexPeer=0
            for par in listaPares:
                if par.split(',')[0]==public_address:
                    indexPeer+=1
                else:
                    break
            #protecao contra null pointer
            if indexPeer>len(listaPares)-1:
                sleep(5)
                continue
            ipPeer,portaPeer,idPeer=listaPares[indexPeer].split(',')
            portaPeer=int(portaPeer)
            #tenho que saber meus candidatos ip e porta
            #ou n

            notPingus="notPing,"+idPeer
            s2.sendto(notPingus.encode('utf-8'),("0.0.0.0",37711))
            print("Python enviou notPing "+idPeer)

            sleep(2)

            #proceeds to do testing
            if notPinged:
                myMappedAddr=list(map(int,public_address.split('.')))
                peerMappedAddr=list(map(int,ipPeer.split('.')))

                myPort=public_port
                pPort=portaPeer
                #0 to server, 1 to client
                clientOrServer=-1
                if public_port>portaPeer:
                    clientOrServer=1
                elif public_port<portaPeer:
                    clientOrServer=0
                elif myMappedAddr>peerMappedAddr:
                    clientOrServer=1
                elif myMappedAddr<peerMappedAddr:
                    clientOrServer=0
                #se porta e ip for igual da zebra kkkk
                #to mandando continuar pingando
                else:
                    doPing="doPing,"+listaPares[indexPeer].split(',')[2]
                    s2.sendto(doPing.encode('utf-8'),("0.0.0.0",37711))
                    print("Python enviou doPing")


                if clientOrServer==1:
                    c=iperf3.Client()
                    c.server_hostname=ipPeer
                    c.port=portaPeer
                    #hole punch eh udp
                    c.protocol='udp'
                    #deixar iperf determinar o tamanho do bloco
                    c.blksize=0

                    #esperar por tantos segundos o servidor falar que ja ta pronto
                    #comunicacao vai ser feita pelos sockets da biblioteca antes de fecha-los
                    for i in range(0,3):
                        sleep(1)
                        if serverReady:
                            break

                    if serverReady:

                        # manda msg de confirmacao
                        gonnaString = "gonnaTest," + listaPares[indexPeer].split(',')[2]
                        s2.sendto(gonnaString.encode('utf-8'), ("0.0.0.0", 37711))

                        sleep(2)

                        result=""
                        try:
                            result=c.run()
                        except:
                            print('exception no teste (cliente)')
                        if result!="":
                            if result.error:
                                print("result error: "+result.error)
                            else:
                                testDone=True
                                testSucessfull=True
                        restartPeerNetwork()

                elif clientOrServer==0:
                    s=iperf3.Server()
                    s.port=hole_port
                    #se der certo testar com = hole_address e ver se por acaso
                    #hole_address nao eh 0.0.0.0
                    s.bind_address='0.0.0.0'
                    s.verbose=False

                    serverString="serverReady,"+listaPares[indexPeer].split(',')[2]
                    s2.sendto(serverString.encode('utf-8'), ("0.0.0.0", 37711))
                    #
                    for i in range(0, 4):
                        sleep(0.5)
                        if gonnaTest:
                            break

                    if gonnaTest:
                        #fechar o socket do peernetwork (ja foi feito pela biblioteca)
                        resultServer=s.run()
                        testDone=True
                        testSucessfull=True
                        restartPeerNetwork()


            #talvez so fazer isso depois que peernetwork tiver reiniciado
            # to mandando continuar pingando
            doPing = "doPing," + listaPares[indexPeer].split(',')[2]
            s2.sendto(doPing.encode('utf-8'), ("0.0.0.0", 37711))
            print("Python enviou doPing")

        elif hole_port>0 and testDone and not test2Done:
            indexPeer=0
            for par in listaPares:
                if par.split(',')[0]==public_address:
                    indexPeer+=1
            if indexPeer>len(listaPares)-1:
                sleep(5)
                continue
            ipPeer,portaPeer,idPeer=listaPares[indexPeer].split(',')
            portaPeer=int(portaPeer)
            #tenho que saber meus candidatos ip e porta
            #ou n

            notPingus="notPing,"+idPeer
            s2.sendto(notPingus.encode('utf-8'),("0.0.0.0",37711))
            print("Python enviou notPing "+idPeer)

            sleep(2)

            #proceeds to do testing
            if notPinged:
                myMappedAddr=list(map(int,public_address.split('.')))
                peerMappedAddr=list(map(int,ipPeer.split('.')))

                myPort=public_port
                pPort=portaPeer
                #0 to server, 1 to client
                clientOrServer=-1
                if public_port>portaPeer:
                    clientOrServer=0
                elif public_port<portaPeer:
                    clientOrServer=1
                elif myMappedAddr>peerMappedAddr:
                    clientOrServer=0
                elif myMappedAddr<peerMappedAddr:
                    clientOrServer=1
                #se porta e ip for igual da zebra kkkk
                #to mandando continuar pingando
                else:
                    doPing="doPing,"+listaPares[indexPeer].split(',')[2]
                    s2.sendto(doPing.encode('utf-8'),("0.0.0.0",37711))
                    print("Python enviou doPing")


                if clientOrServer==1:
                    c=iperf3.Client()
                    c.server_hostname=ipPeer
                    c.port=portaPeer
                    #hole punch eh udp
                    c.protocol='udp'
                    #deixar iperf determinar o tamanho do bloco
                    c.blksize=0

                    #esperar por tantos segundos o servidor falar que ja ta pronto
                    #comunicacao vai ser feita pelos sockets da biblioteca antes de fecha-los
                    for i in range(0,3):
                        sleep(1)
                        if serverReady:
                            break

                    if serverReady:

                        # manda msg de confirmacao
                        gonnaString = "gonnaTest," + listaPares[indexPeer].split(',')[2]
                        s2.sendto(gonnaString.encode('utf-8'), ("0.0.0.0", 37711))

                        sleep(2)

                        result=""
                        try:
                            result=c.run()
                        except:
                            print('exception no teste (cliente)')
                        if result!="":
                            if result.error:
                                print("result error: "+result.error)
                            else:
                                test2Done=True
                                testSucessfull=True
                        restartPeerNetwork()

                elif clientOrServer==0:
                    s=iperf3.Server()
                    s.port=hole_port
                    #se der certo testar com = hole_address e ver se por acaso
                    #hole_address nao eh 0.0.0.0
                    s.bind_address='0.0.0.0'
                    s.verbose=False

                    serverString="serverReady,"+listaPares[indexPeer].split(',')[2]
                    s2.sendto(serverString.encode('utf-8'), ("0.0.0.0", 37711))
                    #
                    for i in range(0, 4):
                        sleep(0.5)
                        if gonnaTest:
                            break

                    if gonnaTest:
                        #fechar o socket do peernetwork (ja foi feito pela biblioteca)
                        resultServer=s.run()
                        test2Done=True
                        testSucessfull=True
                        restartPeerNetwork()

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
    global hole_port
    global hole_address
    global public_port
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

        dataa = s2.recv(1024)
        decodedData=dataa.decode('utf-8')
        splitData=decodedData.split(',')
        if splitData[0]=="add" and (splitData[1]+","+splitData[2]+","+splitData[3]) not in listaPares:
            listaPares.append((splitData[1]+","+splitData[2]+","+splitData[3]))
        elif splitData[0]=="remove" and (splitData[1]+","+splitData[2]+","+splitData[3]) in listaPares:
            listaPares.remove((splitData[1]+","+splitData[2]+","+splitData[3]))
        elif splitData[0]=="holeport":
            hole_port=int(splitData[1])
            hole_address=splitData[2]
            public_port=int(splitData[3])
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


def main():
    listener = threading.Thread(target=listen, daemon=True)
    listener.start()

    listener2= threading.Thread(target=notPing, daemon=True)
    listener2.start()
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

    input("sair?")
    #continueProgram=True
    #while continueProgram:
    #    sleep(2)
if __name__ == '__main__':
    main()
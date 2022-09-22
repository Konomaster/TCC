import math
import os.path
from datetime import datetime
import socket
import subprocess
import threading
from time import sleep
from subprocess import Popen, PIPE, TimeoutExpired, DEVNULL
import iperf3
import psutil
from stun import open_hole, KeepHoleAlive
from peer_offer_thread import PeerOfferThread
import random

import io
import sys

DELAY_BUSCA = 5  # seconds
NUM_RETRANSMISSOES = 1
NUM_RETRANSMISSOES_TESTE = 3
NUM_PARES_BUSCA = 3
OFFER_TIMEOUT = 3  # seconds

CLIENT = 1
SERVER = 0

lock=threading.Lock()


class PoC:
    def __init__(self):
        self.listaPares = []
        self.s1=socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.s2=socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.porta_udp = 37710
        self.porta_peernetwork=0
        #self.notPinged=False
        self.readyToTest=False
        self.hole_socket=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        self.hole_port1=0
        #self.hole_port2=0
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
        self.bits_per_sec_sender=0
        self.bits_per_sec_self=0
        self.bits_per_sec_peer=0
        self.endTest=False


        self.offer_thread=PeerOfferThread(self.s2,NUM_RETRANSMISSOES,OFFER_TIMEOUT)

    def seleciona_par(self,direcao):

        ipPeer,idPeer="",""
        portaPeer,portaCanal=0,0

        for i in range(0,len(self.listaPares)):
            par=self.listaPares[i].split(',')
            if par[2] == self.offer_thread.get_found_peer():
                ipPeer, portaPeer, idPeer, portaCanal = self.listaPares[i].split(',')

        portaPeer = int(portaPeer)
        portaCanal = int(portaCanal)

        if portaPeer == 0:
            return "", "", -1

        myMappedAddr = list(map(int, self.public_address.split('.')))
        peerMappedAddr = list(map(int, ipPeer.split('.')))

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

        return ipPeer, idPeer, clientOrServer

    def extract_throughput(self, pvstderr_decoded):
        l = pvstderr_decoded
        i = -3
        measure = ""
        while not l[i].isdigit():
            measure += l[i]
            i -= 1
        measure = measure[::-1].strip()
        average = ""
        while i >= -len(l):
            average += l[i]
            i -= 1
        average = float(average[::-1].replace(",", "."))
        # google search (what does mib stands for)
        bits = 0
        if measure == "B":
            bits = average * 8.0
        elif measure == "KiB":
            bits = average * 8.0 * 1024.0
        elif measure == "MiB":
            bits = average * 8.0 * math.pow(1024.0, 2.0)
        elif measure == "GiB":
            bits = average * 8.0 * math.pow(1024.0, 3.0)
        elif measure == "TiB":
            bits = average * 8.0 * math.pow(1024.0, 4.0)
        elif measure == "PiB":
            bits = average * 8.0 * math.pow(1024.0, 5.0)
        elif measure == "EiB":
            bits = average * 8.0 * math.pow(1024.0, 6.0)
        elif measure == "ZiB":
            bits = average * 8.0 * math.pow(1024.0, 7.0)
        elif measure == "YiB":
            bits = average * 8.0 * math.pow(1024.0, 8.0)
        return int(bits)

    def save_results(self, throughput, result, latency):
        result_string = str(throughput)
        i = 0
        unit = -1
        point=0
        while i < len(result_string):
            if i % 3 == 0 and unit < 8:
                unit += 1
                point=i
            i += 1
        if point>2:
            result_string = result_string[:len(result_string)-point] + "." + result_string[len(result_string)-point:]
        if unit < 1:
            result_string = result_string + " bits/s"
        elif unit == 1:
            result_string = result_string + " Kbits/s"
        elif unit == 2:
            result_string = result_string + " Mbits/s"
        elif unit == 3:
            result_string = result_string + " Gbits/s"
        elif unit == 4:
            result_string = result_string + " Tbits/s"
        elif unit == 5:
            result_string = result_string + " Pbits/s"
        elif unit == 6:
            result_string = result_string + " Ebits/s"
        elif unit == 7:
            result_string = result_string + " Zbits/s"
        elif unit == 8:
            result_string = result_string + " Ybits/s"
        result_string = result_string + ", Jitter: {} ms, Lost: {} %, Latencia: {} ms\n".format(result.jitter_ms,
                                                                                                result.lost_percent,
                                                                                                latency)
        result_string = datetime.now().strftime("%Y-%m-%d %H:%M:%S") + ", Vazao: " + result_string
        file = open("results.txt", "a")

        file.write(result_string)
        file.close()

        return result_string

    def tcp_test(self, direcao):

        self.endTest = False
        retorno = False
        estado = 1
        max_retr = 3
        result_retr = 3
        result_retr_timeout = 6 # 3 segundos porcausa do sleep de 0.5

        ip_peer, id_peer, my_role = self.seleciona_par(direcao)

        if ip_peer == "":
            return retorno

        udp_hole, socket_udp, keep_udp = self.open_udp_hole()
        tcp_hole, socket_tcp, keep_tcp = self.open_tcp_hole()

        if udp_hole == -1 or tcp_hole == -1:
            # print("erro ao dar bind nos sockets do cliente")
            return retorno
        elif udp_hole == -2 or tcp_hole == -2:
            # print("erro ao abrir buracos do cliente")
            return retorno

        if my_role is CLIENT:

            C_INICIAR = 1
            C_TESTAR = 2
            C_RECEBER_RESULTADOS = 3
            C_FINALIZAR = 5

            while estado != C_FINALIZAR:

                if estado is C_INICIAR:

                    if max_retr == 0:
                        estado = C_FINALIZAR
                        continue
                    max_retr -= 1

                    gonnaString = "gonnaTest," + id_peer + "," + str(udp_hole) + "," + str(tcp_hole)
                    self.s2.sendto(gonnaString.encode('utf-8'), ("0.0.0.0", 37711))

                    # esperar por tantos segundos o servidor falar que ja ta pronto (28)
                    for i in range(0, 32):
                        sleep(0.5)
                        if self.serverReady:
                            self.serverReady = False
                            estado = C_TESTAR
                            break

                    keep_tcp.stop()
                    keep_udp.stop()
                    keep_tcp.join()
                    keep_udp.join()
                    socket_tcp.close()
                    socket_udp.close()

                if estado is C_TESTAR:

                    if self.server_udp_hole == 0 or self.server_udp_hole == 0:
                        # print("nao foram recebidos buracos do servidor")
                        estado = C_FINALIZAR
                        continue

                    sleep(1)

                    try:
                        # str1="pv -f -B 1450 -a /dev/random"
                        str1 = "pv -f -B 1450 -a stun.py"
                        str2 = "socat -b 1450 - udp:" + ip_peer + ":" + str(self.server_udp_hole) + ",sp=" + str(
                            self.udp_local_port)
                        t1 = Popen(str1.split(), stderr=PIPE, stdout=PIPE)
                        t2 = Popen(str2.split(), stdin=t1.stdout)
                        t1.stdout.close()
                        sleep(10)
                        self.close_processes([t1.pid, t2.pid])
                        for line in t1.stderr:
                            step = line.decode('utf-8').split("\r")[-2].lstrip("[").rstrip("]")
                            self.bits_per_sec_sender = self.extract_throughput(step)
                            break
                        estado = C_RECEBER_RESULTADOS
                    except:
                        print('exception no teste (cliente)')
                        estado = C_INICIAR

                if estado is C_RECEBER_RESULTADOS:
                    #ignorar serverReadies duplos que vierem por qualquer motivo
                    if self.serverReady:
                        self.serverReady = False
                    #Tempo suficiente pra par fazer as retransmissoes de
                    #resultado e chegar para o cliente
                    for i in range(0, result_retr_timeout*result_retr + 1):
                        sleep(0.5)
                        if self.endTest:
                            #recebeu resultado, envia ack
                            sendstr = "endTest_ack," + self.offer_thread.get_found_peer()
                            self.s2.sendto(sendstr.encode('utf-8'), ("0.0.0.0", 37711))
                            self.testDone = True
                            retorno = True
                            break

                    estado = C_FINALIZAR

        elif my_role is SERVER:

            S_OUVIR = 1
            S_TESTAR = 2
            S_ENVIAR_RESULTADOS = 3
            S_FINALIZAR = 5

            client_result = "0.00 B/s"

            while estado != S_FINALIZAR:

                if estado is S_OUVIR:

                    estado = S_FINALIZAR

                    for i in range(0,40):
                        sleep(0.5)
                        if self.gonnaTest:
                            self.gonnaTest = False
                            estado = S_TESTAR
                            break
                    time1=datetime.now()
                    keep_tcp.stop()
                    keep_udp.stop()
                    keep_tcp.join()
                    keep_udp.join()

                    if self.client_udp_hole != 0 and self.client_tcp_hole != 0:
                        # print("furando buracos para peer ip: "+ipPeer)
                        socket_tcp.sendto("abrindo buraco tcp".encode('utf-8'), (ip_peer, self.client_tcp_hole))
                        socket_udp.sendto("abrindo buraco udp".encode('utf-8'), (ip_peer, self.client_udp_hole))
                        # make sure client doesnt get above messages
                        sleep(3)

                    socket_tcp.close()
                    socket_udp.close()
                    elapsed_time = datetime.now() - time1
                    print("elapsed time:\n"+str(elapsed_time)+"\n")
                elif estado is S_TESTAR:

                    if max_retr == 0:
                        estado = S_FINALIZAR
                        continue
                    max_retr -= 1

                    # nao precisa de tunnel udp aqui pq ja vai receber no porto certo
                    serverRunning = True
                    str1 = "nc -u -l " + str(self.udp_local_port)
                    str2 = "pv -f -r"
                    # "nc -u -l "+str(self.udp_local_port)+" | pv > /dev/null"

                    serverString = "serverReady," + id_peer + "," + str(udp_hole) + "," + str(tcp_hole)
                    self.s2.sendto(serverString.encode('utf-8'), ("0.0.0.0", 37711))

                    t1 = Popen(str1.split(), stdout=PIPE)
                    t2 = Popen(str2.split(), stdin=t1.stdout, stderr=PIPE, stdout=DEVNULL)
                    t1.stdout.close()

                    retry = False
                    for i in range(0,15):
                        sleep(1)
                        if self.gonnaTest:
                            self.gonnaTest = False
                            retry = True
                            break

                    self.close_processes([t1.pid, t2.pid])

                    if retry:
                        continue

                    max_bits = 0
                    max = "0,00 B/s"
                    for line in t2.stderr:
                        l = line.decode('utf-8').rstrip("\n").rstrip("\r").split("\r")
                        for step in l:
                            clean_step = step.rstrip("]").lstrip("[")
                            bits = self.extract_throughput(clean_step)
                            if bits > max_bits:
                                max_bits = bits
                                max = clean_step
                        self.bits_per_sec_peer = max_bits
                        break
                    client_result = max.replace(",", ".")
                    estado = S_ENVIAR_RESULTADOS

                elif estado is S_ENVIAR_RESULTADOS:

                    #somente num_retr tentativas de mandar resultado
                    if result_retr == 0:
                        estado = S_FINALIZAR
                        continue
                    result_retr -= 1

                    # envia resultado ao par
                    vazao = "endTest," + id_peer + "," + client_result
                    self.s2.sendto(vazao.encode('utf-8'), ("0.0.0.0", 37711))

                    # timeout de 3 secs
                    for i in range(0,result_retr_timeout):
                        sleep(0.5)
                        #recebeu ack
                        if self.endTest:
                            estado = S_FINALIZAR
                            self.testDone = True
                            self.serverRunning = False
                            retorno = True
                            break

        return retorno

    def make_tcp_test(self,direcao):

        ipPeer, idPeer, clientOrServer = self.seleciona_par(direcao)

        if ipPeer == "":
            return

        if clientOrServer == 1:

            udp_hole, socket_udp, keep_udp = self.open_udp_hole()
            tcp_hole, socket_tcp, keep_tcp = self.open_tcp_hole()

            if udp_hole == -1 or tcp_hole == -1:
                #print("erro ao dar bind nos sockets do cliente")
                return
            elif udp_hole == -2 or tcp_hole == -2:
                #print("erro ao abrir buracos do cliente")
                return

            # manda msg de confirmacao
            gonnaString = "gonnaTest," + idPeer + "," + str(udp_hole) + "," + str(tcp_hole)
            self.s2.sendto(gonnaString.encode('utf-8'), ("0.0.0.0", 37711))


            # esperar por tantos segundos o servidor falar que ja ta pronto
            # comunicacao vai ser feita pelos sockets da biblioteca antes de fecha-los
            for i in range(0, 40):
                sleep(1)
                if self.serverReady:
                    break

            keep_tcp.stop()
            keep_udp.stop()
            keep_tcp.join()
            keep_udp.join()
            socket_tcp.close()
            socket_udp.close()

            if self.serverReady:
                self.serverReady=False
                if self.server_udp_hole == 0 or self.server_udp_hole == 0:
                    #print("nao foram recebidos buracos do servidor")
                    return

                sleep(1)

                result = ""
                try:
                    #print("cliente iniciando teste")
                    #str1="pv -f -B 1450 -a /dev/random"
                    str1 = "pv -f -B 1450 -a stun.py"
                    str2="socat -b 1450 - udp:"+ipPeer+":"+str(self.server_udp_hole)+",sp="+str(self.udp_local_port)
                    t1=Popen(str1.split(),stderr=PIPE,stdout=PIPE)
                    t2=Popen(str2.split(),stdin=t1.stdout)
                    t1.stdout.close()
                    sleep(10)
                    self.close_processes([t1.pid,t2.pid])
                    for line in t1.stderr:
                        step=line.decode('utf-8').split("\r")[-2].lstrip("[").rstrip("]")
                        self.bits_per_sec_sender=self.extract_throughput(step)
                        break
                    self.testDone=True
                except:
                    print('exception no teste (cliente)')
                if result != "":
                    if result.error:
                        print("result error: " + result.error)
                    else:
                        #print(result)
                        #print("teste concluido com sucesso")
                        self.testDone = True
                        testSucessfull = True


                self.server_udp_hole = 0
                self.server_udp_hole = 0

                self.serverReady = False

        elif clientOrServer == 0:

            udp_hole, socket_udp, keep_udp=self.open_udp_hole()
            tcp_hole, socket_tcp, keep_tcp=self.open_tcp_hole()

            if udp_hole == -1 or tcp_hole == -1:
                #print("erro ao dar bind nos sockets do servidor")
                return
            elif tcp_hole == -2 or tcp_hole == -2:
                #print("erro ao abrir buracos do servidor")
                return

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
                #print("furando buracos para peer ip: "+ipPeer)
                socket_tcp.sendto("abrindo buraco tcp".encode('utf-8'), (ipPeer, self.client_tcp_hole))
                socket_udp.sendto("abrindo buraco udp".encode('utf-8'), (ipPeer, self.client_udp_hole))
                #make sure client doesnt get above messages
                sleep(3)

            socket_tcp.close()
            socket_udp.close()

            if self.gonnaTest:
                self.gonnaTest=False
                serverString = "serverReady," + idPeer + "," + str(udp_hole) + "," + str(tcp_hole)
                self.s2.sendto(serverString.encode('utf-8'), ("0.0.0.0", 37711))
                #print(serverString)

                #nao precisa de tunnel udp aqui pq ja vai receber no porto certo
                serverRunning=True
                #print("Servidor iniciando")
                str1="nc -u -l "+str(self.udp_local_port)
                str2="pv -f -r"
                #cmdserver = "nc -u -l "+str(self.udp_local_port)+" | pv > /dev/null"
                t1 = Popen(str1.split(),stdout=PIPE)
                t2 = Popen(str2.split(),stdin=t1.stdout,stderr=PIPE,stdout=DEVNULL)
                t1.stdout.close()

                sleep(15)
                self.close_processes([t1.pid,t2.pid])
                max_bits=0
                max="0,00 B/s"
                for line in t2.stderr:
                    l = line.decode('utf-8').rstrip("\n").rstrip("\r").split("\r")
                    for step in l:
                        clean_step=step.rstrip("]").lstrip("[")
                        bits=self.extract_throughput(clean_step)
                        if bits>max_bits:
                            max_bits=bits
                            max=clean_step
                    self.bits_per_sec_peer=max_bits
                    break
                self.testDone = True
                testSucessfull = True
                self.serverRunning=False

                #envia resultado ao par
                #necessario trocar o , do max porque a virgula eh meu separador especial
                vazao="vazao,"+idPeer+","+max.replace(",",".")
                self.s2.sendto(vazao.encode('utf-8'),("0.0.0.0",37711))

                #print("teste concluido com sucesso")
            else:
                print("gonnaTest nao chegou a tempo")

            self.client_udp_hole = 0
            self.client_tcp_hole = 0

            #nao esqueci de resetar o gonnatest, so escolhi nao resetar

    def make_udp_test(self,direcao):
        testSucessfull=False

        ipPeer, idPeer, clientOrServer = self.seleciona_par(direcao)

        if ipPeer == "":
            return

        if clientOrServer == 1:

            udp_hole, socket_udp, keep_udp=self.open_udp_hole()
            tcp_hole, socket_tcp, keep_tcp=self.open_tcp_hole()

            if udp_hole == -1 or tcp_hole == -1:
                #print("erro ao dar bind nos sockets do cliente")
                return
            elif udp_hole == -2 or tcp_hole == -2:
                #print("erro ao abrir buracos do cliente")
                return

            # manda msg de confirmacao
            gonnaString = "gonnaTest," + idPeer + "," + str(udp_hole) + "," + str(tcp_hole)
            self.s2.sendto(gonnaString.encode('utf-8'), ("0.0.0.0", 37711))

            c = iperf3.Client()
            c.server_hostname = "localhost"
            c.port = self.iperf_port
            # hole punch eh udp
            c.protocol = 'udp'
            # deixar iperf determinar o tamanho do bloco
            c.blksize = 1450
            #trocar esse valor depois pelo que der no tcp
            if self.bits_per_sec_peer>self.bits_per_sec_self:
                c.bandwidth=self.bits_per_sec_self
            else:
                c.bandwidth = self.bits_per_sec_peer
            if c.bandwidth==0:
                c.bandwidth=1000000

            # esperar por tantos segundos o servidor falar que ja ta pronto
            # comunicacao vai ser feita pelos sockets da biblioteca antes de fecha-los
            for i in range(0, 40):
                sleep(1)
                if self.serverReady:
                    break

            keep_tcp.stop()
            keep_udp.stop()
            keep_tcp.join()
            keep_udp.join()
            socket_tcp.close()
            socket_udp.close()

            if self.serverReady:
                self.serverReady=False
                if self.server_udp_hole == 0 or self.server_udp_hole == 0:
                    #print("nao foram recebidos buracos do servidor")
                    return

                sleep(1)
                cmd = "socat -d -d tcp-listen:"+str(self.iperf_port)+",reuseaddr udp:" + ipPeer + ":" + str(self.server_tcp_hole)+",sp="+str(self.tcp_local_port)
                cmd2 = "socat -d -d udp-listen:"+str(self.iperf_port)+",reuseaddr udp:" + ipPeer + ":" + str(self.server_udp_hole)+",sp="+str(self.udp_local_port)

                #print(cmd)
                #print(cmd2)

                tunnelTCP_UDP = Popen(cmd.split())
                tunnelUDP = Popen(cmd2.split())
                result = ""
                try:

                    #print("cliente iniciando teste")
                    result = c.run()

                except:
                    print('exception no teste (cliente)')
                if result != "":
                    if result.error:
                        print("result error: " + result.error)
                    else:
                        self.save_results(c.bandwidth,result,0)
                        #print("teste concluido com sucesso")
                        self.testDone = True
                        testSucessfull = True

                #fecha os tuneis
                self.close_processes([tunnelTCP_UDP.pid,tunnelUDP.pid])

                self.server_udp_hole = 0
                self.server_udp_hole = 0

                self.serverReady = False

        elif clientOrServer == 0:

            udp_hole, socket_udp, keep_udp=self.open_udp_hole()
            tcp_hole, socket_tcp, keep_tcp=self.open_tcp_hole()

            if udp_hole == -1 or tcp_hole == -1:
                #print("erro ao dar bind nos sockets do servidor")
                return
            elif udp_hole == -2 or tcp_hole == -2:
                #print("erro ao abrir buracos do servidor")
                return

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
                
                #print("furando buracos para peer ip: "+ipPeer)
                socket_tcp.sendto("abrindo buraco tcp".encode('utf-8'), (ipPeer, self.client_tcp_hole))
                socket_udp.sendto("abrindo buraco udp".encode('utf-8'), (ipPeer, self.client_udp_hole))
                #delay to make sure what i just sent dont get received by the client
                sleep(3)

            socket_tcp.close()
            socket_udp.close()

            if self.gonnaTest:
                self.gonnaTest=False
                serverString = "serverReady," + idPeer + "," + str(udp_hole) + "," + str(tcp_hole)
                self.s2.sendto(serverString.encode('utf-8'), ("0.0.0.0", 37711))
                #print(serverString)

                cmd = "socat -d -d udp-listen:"+str(self.tcp_local_port)+",reuseaddr tcp:localhost:"+str(self.udp_local_port)
                #print(cmd)
                #nao precisa de tunnel udp aqui pq ja vai receber no porto certo
                tunnelTCP_UDP = Popen(cmd.split())

                serverRunning=True
                #print("Servidor iniciando")
                cmdserver="iperf3 -1 -s -p "+str(self.udp_local_port)
                s=Popen(cmdserver.split())

                try:
                    s.wait(25)
                except TimeoutExpired:
                    #print("matando servs")
                    self.close_processes([s.pid])
                self.testDone = True
                testSucessfull = True
                # fecha o tunel
                self.serverRunning=False
                self.close_processes([tunnelTCP_UDP.pid])

                #print("teste concluido com sucesso")
            else:
                print("gonnaTest nao chegou a tempo")

            self.client_udp_hole = 0
            self.client_tcp_hole = 0

            #nao esqueci de resetar o gonnatest, so escolhi nao resetar

    def select_peer(self):
        if not self.offer_thread.is_kicked_off() and self.listaPares and self.public_address != "":

            real_peers = []
            for peer in self.listaPares:
                ipPeer, portaPeer, idPeer, portaCanal = peer.split(',')
                if ipPeer != self.public_address:
                    real_peers.append(idPeer)

            if not real_peers:
                return

            chosen_peers = []
            num_offers = NUM_PARES_BUSCA

            if len(real_peers) < NUM_PARES_BUSCA:
                num_offers = len(real_peers)

            while len(chosen_peers) < num_offers:
                index = random.randint(0,len(real_peers)-1)

                idPeer = real_peers[index]

                if idPeer not in chosen_peers:
                    chosen_peers.append(idPeer)

            self.offer_thread.set_peers(chosen_peers)

            print("select_peer() chosen_peers:\n")
            print(real_peers)
            self.offer_thread.kick_off()

    def callTest(self):
        testSucessfull=False
        while True:
            # kick off test offers if it still isnt
            self.select_peer()
         #   print("chamou select peer")
            if self.offer_thread.get_found_peer() and self.hole_port1 > 0:
                print("achouPeer\n")
                self.tcp_test("reverso")
                #print("indo pro teste tcp reverso")
                self.tcp_test("normal")
                #print("indo pro teste udp normal")
                #self.make_udp_test("reverso")
                #print("indo pro teste udp reverso")
                #self.make_udp_test("normal")
                #print("acabou todos os testes")
                sleep(DELAY_BUSCA)
                self.offer_thread.set_peers([])
                self.offer_thread.set_found_peer((False,"undefined"))
                print("found peer = False\n")
            #elif self.listaPares!=[] and self.hole_port1>0 and self.testDone and not self.test2Done:
            else:
                print("ainda nao achou peer\n")
            sleep(5)

    def listen(self):
        if self.porta_udp>0:
            try:
                self.s2.bind(('0.0.0.0', self.porta_udp))
                self.s1.bind(('0.0.0.0', self.porta_udp-1))
                self.offer_thread.start()
            except:
                #print("erro ao fazer bind do socket na porta 37710")
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
                #elif sender[1] == 37712:
                #    self.hole_port2 = int(splitData[1])
                if self.hole_address=="":
                    self.hole_address=splitData[2]
                #talvez dexar sempre sobescrever as portas publicas
                if self.public_port1==0:
                    self.public_port1=int(splitData[3])
                if self.public_address=="":
                    self.public_address=splitData[4]
            #elif splitData[0]=="confirmNotPing":
            #    self.notPinged=True
            #elif splitData[0]=="removeNotPing":
            #    self.notPinged=False
            elif splitData[0]=="serverReady" and self.offer_thread.get_found_peer() == splitData[3]:
                self.serverReady=True
                self.server_udp_hole=int(splitData[1])
                self.server_tcp_hole=int(splitData[2])
            elif splitData[0]=="gonnaTest" and self.offer_thread.get_found_peer() == splitData[3]:
                self.gonnaTest=True
                self.client_udp_hole=int(splitData[1])
                self.client_tcp_hole=int(splitData[2])
            elif splitData[0]=="vazao":
                self.bits_per_sec_self=self.extract_throughput(splitData[1])
            elif splitData[0] == "endTest" and self.offer_thread.get_found_peer() == splitData[len(splitData)-1]:
                self.endTest=True
                if len(splitData) == 3:
                    self.bits_per_sec_self = self.extract_throughput(splitData[1])
            elif splitData[0] == "endTest_ack" and self.offer_thread.get_found_peer() == splitData[len(splitData)-1]:
                self.endTest=True
            elif splitData[0] == "offer" and not self.offer_thread.get_found_peer():
                self.offer_thread.set_found_peer((splitData[1],"server"))
                sendstr="offer_res," + splitData[1]
                self.s1.sendto(sendstr.encode('utf-8'), ("0.0.0.0", 37711))
            elif splitData[0] == "offer" and self.offer_thread.get_found_peer():

                sendstr="offer_rjct,"+splitData[1]
                self.s1.sendto(sendstr.encode('utf-8'), ("0.0.0.0", 37711))
            elif splitData[0] == "offer_rjct":

                self.offer_thread.ack(splitData[1])
            elif splitData[0] == "offer_res" and self.offer_thread.get_found_peer() == False:

                self.offer_thread.ack(splitData[1])
                self.offer_thread.set_found_peer((splitData[1],"client"))
            elif splitData[0] == "offer_abort" and self.offer_thread.get_found_peer() and splitData[1] == self.offer_thread.get_found_peer():

                self.offer_thread.set_found_peer((False,"undefined"))
                sendstr="offer_abort_ack," + splitData[1]
                self.s1.sendto(sendstr.encode('utf-8'), ("0.0.0.0", 37711))
            elif splitData[0] == "offer_abort_ack":
                self.offer_thread.ack(splitData[1])


           # print('\rpeer: {}\n '.format(decodedData), end='')

    def open_udp_hole(self):
        udp_hole = open_hole(self.udp_local_port)

        if udp_hole != 0:
            socket_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

            try:
                socket_udp.bind(("0.0.0.0", self.udp_local_port))

            except:
                #print("erro ao dar bind no socket udp do cliente")
                return -1, -1, -1

            keep_udp = KeepHoleAlive(socket_udp, 2)

            keep_udp.start()

            return udp_hole, socket_udp, keep_udp

        return -2, -2, -2

    def open_tcp_hole(self):
        tcp_hole = open_hole(self.tcp_local_port)

        if tcp_hole != 0:
            socket_tcp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

            try:
                socket_tcp.bind(("0.0.0.0", self.tcp_local_port))
            except:
                #print("erro ao dar bind no socket tcp do cliente")
                return -1, -1, -1

            keep_tcp = KeepHoleAlive(socket_tcp, 2)

            keep_tcp.start()

            return tcp_hole, socket_tcp, keep_tcp

        return -2, -2, -2

    def close_processes(self,pid_list):
        for pid in pid_list:
            if not psutil.pid_exists(pid):
                continue
            parent=psutil.Process(pid)
            for child in parent.children(recursive=True):
                try:
                    child.kill()
                except:
                    pass
            try:
                parent.kill()
            except:
                pass


def peerNetwork():
    process = Popen("node ../PeerNetwork.js".split())


def main():
    proof_of_concept=PoC()

    socket_listener = threading.Thread(target=proof_of_concept.listen, daemon=True)
    socket_listener.start()

    call_test=threading.Thread(target=proof_of_concept.callTest, daemon=True)
    call_test.start()
    #listener2 = threading.Thread(target=notPing, daemon=True)
    #listener2.start()

    pnthread1 = threading.Thread(target=peerNetwork, daemon=True)
    pnthread1.start()
    
    input("sair?")
    #continueProgram=True
    #while continueProgram


if __name__ == '__main__':
    main()

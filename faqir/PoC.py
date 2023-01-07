import math
import signal
from datetime import datetime
import socket
import subprocess
import threading
from time import sleep
from subprocess import Popen, PIPE, DEVNULL
import iperf3
from stun import open_hole, KeepHoleAlive
from peer_offer_thread import PeerOfferThread
import random
import sys
from utils import close_processes, bps_scale

DELAY_BUSCA = 5  # seconds
NUM_RETRANSMISSOES = 1
NUM_RETRANSMISSOES_TESTE = 3
NUM_PARES_BUSCA = 3
OFFER_TIMEOUT = 3  # seconds

CLIENT = 1
SERVER = 0

lock = threading.Lock()


class PoC:
    def __init__(self):
        self.listaPares = []
        self.s1 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.s2 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.porta_udp = 37710
        self.porta_peernetwork = 0
        # self.notPinged=False
        self.readyToTest = False
        self.hole_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.hole_port1 = 0
        # self.hole_port2=0
        self.hole_address = ""
        self.public_port1 = 0
        self.public_address = ""
        self.latency = 0
        self.test2Done = False
        self.serverReady = False
        self.gonnaTest = False
        self.serverRunning = False
        self.server_udp_hole = 0
        self.server_tcp_hole = 0
        self.client_udp_hole = 0
        self.client_tcp_hole = 0
        self.iperf_port = 5000
        self.udp_local_port = 3000
        self.tcp_local_port = 3001
        self.bits_per_sec_sender = 0
        self.bits_per_sec_self = 0
        self.bits_per_sec_peer = 0
        self.endTest = False

        self.offer_thread = PeerOfferThread(self.s2, NUM_RETRANSMISSOES, OFFER_TIMEOUT)
        self.offer_thread.setDaemon(True)

    def seleciona_par(self, direcao):

        ipPeer, idPeer = "", ""
        portaPeer, portaCanal = 0, 0

        for i in range(0, len(self.listaPares)):
            par = self.listaPares[i].split(',')
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

    def calculate_latency(self):
        file = open('udp_packetn_latency_pairs')
        index = 0
        sum = 0
        for line in file.readlines():
            if index>0:
                sum+=int(line.split(' ')[1].replace('.',''))
            index+=1
        file.close()
        #converte de us (microssegundos) em ms (milissegundos)
        #1e5 = 1e3 + 1e2 pra compensar as casas decimais que eu desconsiderei acima
        latency = (sum/index) / 1e5
        return latency


    def save_results(self, throughput, jitter_ms, lost_percent):

        bps_scale(throughput)

        latency = self.calculate_latency()
        result_string = bps_scale(throughput) + ", Jitter: {} ms, Lost: {} %, Latencia: {} ms\n".format(jitter_ms,
                                                                                                lost_percent,
                                                                                                latency)
        result_string = datetime.now().strftime("%Y-%m-%d %H:%M:%S") + ", Vazao: " + result_string
        file = open("results.txt", "a")

        file.write(result_string)
        file.close()

        return result_string

    def throughput_test(self, direcao):

        self.endTest = False
        retorno = False
        estado = 1
        max_retr = 3
        result_retr = 3
        result_retr_timeout = 6  # 3 segundos porcausa do sleep de 0.5

        ip_peer, id_peer, my_role = self.seleciona_par(direcao)

        if ip_peer == "":
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

                    udp_hole, socket_udp, keep_udp = self.open_udp_hole()
                    tcp_hole, socket_tcp, keep_tcp = self.open_tcp_hole()

                    if udp_hole == -1 or tcp_hole == -1:
                        # print("erro ao dar bind nos sockets do cliente")
                        estado = C_FINALIZAR
                        continue
                    elif udp_hole == -2 or tcp_hole == -2:
                        # print("erro ao abrir buracos do cliente")
                        estado = C_FINALIZAR
                        continue

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

                    if self.server_udp_hole == 0 or self.server_tcp_hole == 0:
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
                        close_processes([t1.pid, t2.pid])
                        for line in t1.stderr:
                            step = line.decode('utf-8').split("\r")[-2].lstrip("[").rstrip("]")
                            self.bits_per_sec_sender = self.extract_throughput(step)
                            break
                        estado = C_RECEBER_RESULTADOS
                    except:
                        print('exception no teste (cliente)')
                        estado = C_INICIAR

                if estado is C_RECEBER_RESULTADOS:
                    # ignorar serverReadies duplos que vierem por qualquer motivo
                    if self.serverReady:
                        self.serverReady = False
                    # Tempo suficiente pra par fazer as retransmissoes de
                    # resultado e chegar para o cliente
                    for i in range(0, result_retr_timeout * result_retr + 1):
                        sleep(0.5)
                        if self.endTest:
                            # recebeu resultado, envia ack
                            sendstr = "endTest_ack," + self.offer_thread.get_found_peer()
                            self.s2.sendto(sendstr.encode('utf-8'), ("0.0.0.0", 37711))

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

                    for i in range(0, 40):
                        sleep(0.5)
                        if self.gonnaTest:
                            self.gonnaTest = False
                            estado = S_TESTAR
                            break

                elif estado is S_TESTAR:

                    if max_retr == 0:
                        estado = S_FINALIZAR
                        continue
                    max_retr -= 1

                    #abre buracos por onde o cliente ira realizar o teste
                    udp_hole, socket_udp, keep_udp = self.open_udp_hole()
                    tcp_hole, socket_tcp, keep_tcp = self.open_tcp_hole()

                    if udp_hole == -1 or tcp_hole == -1:
                        # print("erro ao dar bind nos sockets do cliente")
                        estado = S_FINALIZAR
                        continue
                    elif udp_hole == -2 or tcp_hole == -2:
                        # print("erro ao abrir buracos do cliente")
                        estado = S_FINALIZAR
                        continue

                    time1 = datetime.now()
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
                    for i in range(0, 15):
                        sleep(1)
                        if self.gonnaTest:
                            self.gonnaTest = False
                            retry = True
                            break

                    close_processes([t1.pid, t2.pid])

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

                    # somente num_retr tentativas de mandar resultado
                    if result_retr == 0:
                        estado = S_FINALIZAR
                        continue
                    result_retr -= 1

                    # envia resultado ao par
                    vazao = "endTest," + id_peer + "," + client_result
                    self.s2.sendto(vazao.encode('utf-8'), ("0.0.0.0", 37711))

                    # timeout de 3 secs
                    for i in range(0, result_retr_timeout):
                        sleep(0.5)
                        # recebeu ack
                        if self.endTest:
                            estado = S_FINALIZAR

                            self.serverRunning = False
                            retorno = True
                            break

        return retorno

    def jitter_loss_test(self, direcao):

        self.endTest = False
        retorno = False
        estado = 1
        max_retr = 3
        result_retr = 3
        result_retr_timeout = 6  # 3 segundos porcausa do sleep de 0.5

        ip_peer, id_peer, my_role = self.seleciona_par(direcao)

        if ip_peer == "":
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

                    udp_hole, socket_udp, keep_udp = self.open_udp_hole()
                    tcp_hole, socket_tcp, keep_tcp = self.open_tcp_hole()

                    if udp_hole == -1 or tcp_hole == -1:
                        # print("erro ao dar bind nos sockets do cliente")
                        estado = C_FINALIZAR
                        continue
                    elif udp_hole == -2 or tcp_hole == -2:
                        # print("erro ao abrir buracos do cliente")
                        estado = C_FINALIZAR
                        continue

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

                    if self.server_udp_hole == 0 or self.server_tcp_hole == 0:
                        # print("nao foram recebidos buracos do servidor")
                        estado = C_FINALIZAR
                        continue

                    sleep(1)

                    cmd = "socat -d -d tcp-listen:" + str(self.iperf_port) + ",reuseaddr udp:" + ip_peer + ":" + str(
                        self.server_tcp_hole) + ",sp=" + str(self.tcp_local_port)
                    cmd2 = "socat -d -d udp-listen:" + str(self.iperf_port) + ",reuseaddr udp:" + ip_peer + ":" + str(
                        self.server_udp_hole) + ",sp=" + str(self.udp_local_port)

                    if self.bits_per_sec_peer > self.bits_per_sec_self:
                        bandwidth = self.bits_per_sec_self
                    else:
                        bandwidth = self.bits_per_sec_peer
                    if bandwidth == 0:
                        bandwidth = 1000000

                    cmdWrapper = "python3 wrapper_iperf3.py "+str(self.iperf_port)+" "+str(bandwidth)

                    tunnelTCP_UDP = Popen(cmd.split())
                    tunnelUDP = Popen(cmd2.split())
                    wrapperCall = Popen(cmdWrapper.split(),stdout=PIPE)
                    try:

                        # print("cliente iniciando teste")
                            sleep(16)
                            wrapperCall.wait(6)

                    except:
                        print('exception no teste (cliente entrou em deadlock):')
                        estado = C_INICIAR

                    # fecha os tuneis
                    close_processes([wrapperCall.pid,tunnelTCP_UDP.pid, tunnelUDP.pid])
                    self.server_udp_hole = 0
                    self.server_tcp_hole = 0

                    if estado == C_INICIAR:
                        continue

                    jitter_ms=0
                    lost_percent=0

                    result_index=0
                    for line in wrapperCall.stdout:
                        line = line.decode('utf-8').rstrip('\n')
                        if result_index == 0:
                            jitter_ms = line
                            result_index+=1
                        else:
                            lost_percent = line

                    self.save_results(bandwidth, jitter_ms, lost_percent)
                    estado = C_RECEBER_RESULTADOS


                if estado is C_RECEBER_RESULTADOS:
                    # ignorar serverReadies duplos que vierem por qualquer motivo
                    if self.serverReady:
                        self.serverReady = False
                    # Tempo suficiente pra par fazer as retransmissoes de
                    # resultado e chegar para o cliente
                    for i in range(0, result_retr_timeout * result_retr + 1):
                        sleep(0.5)
                        if self.endTest:
                            # recebeu resultado, envia ack
                            sendstr = "endTest_ack," + self.offer_thread.get_found_peer()
                            self.s2.sendto(sendstr.encode('utf-8'), ("0.0.0.0", 37711))

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

                    for i in range(0, 40):
                        sleep(0.5)
                        if self.gonnaTest:
                            self.gonnaTest = False
                            estado = S_TESTAR
                            break

                elif estado is S_TESTAR:

                    if max_retr == 0:
                        estado = S_FINALIZAR
                        continue
                    max_retr -= 1

                    #abre buracos por onde o cliente ira realizar o teste
                    udp_hole, socket_udp, keep_udp = self.open_udp_hole()
                    tcp_hole, socket_tcp, keep_tcp = self.open_tcp_hole()

                    if udp_hole == -1 or tcp_hole == -1:
                        # print("erro ao dar bind nos sockets do cliente")
                        estado = S_FINALIZAR
                        continue
                    elif udp_hole == -2 or tcp_hole == -2:
                        # print("erro ao abrir buracos do cliente")
                        estado = S_FINALIZAR
                        continue

                    time1 = datetime.now()
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

                    cmd = "socat -d -d udp-listen:" + str(self.tcp_local_port) + ",reuseaddr tcp:localhost:" + str(
                        self.udp_local_port)
                    cmdserver = "iperf3 -1 -s -p " + str(self.udp_local_port)

                    serverString = "serverReady," + id_peer + "," + str(udp_hole) + "," + str(tcp_hole)
                    self.s2.sendto(serverString.encode('utf-8'), ("0.0.0.0", 37711))

                    # nao precisa de tunnel udp aqui pq ja vai receber no porto certo
                    tunnelTCP_UDP = Popen(cmd.split())

                    serverRunning = True
                    # print("Servidor iniciando")
                    s = Popen(cmdserver.split())

                    retry = False
                    for i in range(0, 15):
                        sleep(1)
                        if self.gonnaTest:
                            self.gonnaTest = False
                            retry = True
                            break

                    close_processes([tunnelTCP_UDP.pid, s.pid])

                    if retry:
                        continue

                    # fecha o tunel
                    self.serverRunning = False

                    self.client_udp_hole = 0
                    self.client_tcp_hole = 0

                    estado = S_ENVIAR_RESULTADOS

                elif estado is S_ENVIAR_RESULTADOS:

                    # somente num_retr tentativas de mandar resultado
                    if result_retr == 0:
                        estado = S_FINALIZAR
                        continue
                    result_retr -= 1

                    # envia resultado ao par
                    vazao = "endTest," + id_peer
                    self.s2.sendto(vazao.encode('utf-8'), ("0.0.0.0", 37711))

                    # timeout de 3 secs
                    for i in range(0, result_retr_timeout):
                        sleep(0.5)
                        # recebeu ack
                        if self.endTest:
                            estado = S_FINALIZAR

                            self.serverRunning = False
                            retorno = True
                            break

        return retorno

    def latency_test(self, direcao):

        self.endTest = False
        retorno = False
        estado = 1
        max_retr = 3
        result_retr = 3
        result_retr_timeout = 6  # 3 segundos porcausa do sleep de 0.5

        ip_peer, id_peer, my_role = self.seleciona_par(direcao)

        if ip_peer == "":
            return retorno

        if my_role is CLIENT:

            c = iperf3.Client()

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

                    udp_hole, socket_udp, keep_udp = self.open_udp_hole()
                    tcp_hole, socket_tcp, keep_tcp = self.open_tcp_hole()

                    if udp_hole == -1 or tcp_hole == -1:
                        # print("erro ao dar bind nos sockets do cliente")
                        estado = C_FINALIZAR
                        continue
                    elif udp_hole == -2 or tcp_hole == -2:
                        # print("erro ao abrir buracos do cliente")
                        estado = C_FINALIZAR
                        continue

                    gonnaString = "gonnaTest," + id_peer + "," + str(udp_hole) + "," + str(tcp_hole)
                    self.s2.sendto(gonnaString.encode('utf-8'), ("0.0.0.0", 37711))

                    flagServerAnswered=False
                    # esperar por tantos segundos o servidor falar que ja ta pronto (28)
                    for i in range(0, 32):
                        sleep(0.5)
                        if self.serverReady:
                            self.serverReady = False
                            flagServerAnswered = True
                            estado = C_TESTAR
                            break

                    keep_tcp.stop()
                    keep_udp.stop()
                    keep_tcp.join()
                    keep_udp.join()
                    if flagServerAnswered:
                        socket_tcp.sendto("abrindo buraco tcp".encode('utf-8'), (ip_peer, self.server_tcp_hole))
                    socket_tcp.close()
                    socket_udp.close()

                if estado is C_TESTAR:

                    if self.server_udp_hole == 0 or self.server_tcp_hole == 0:
                        # print("nao foram recebidos buracos do servidor")
                        estado = C_FINALIZAR
                        continue

                    sleep(1)
                    exception = False

                    cmd1 = "socat -d -d udp-listen:" + str(self.iperf_port) + ",reuseaddr udp:" + ip_peer + ":" + str(
                        self.server_udp_hole) + ",sp=" + str(self.udp_local_port)

                    cmd2 = "socat -d -d udp-listen:" + str(
                        self.tcp_local_port) + ",reuseaddr udp:localhost:" + str(self.iperf_port + 1)
                    cmdclient = "python3 ../ultra_ping/echo.py --client 127.0.0.1 --listen_port " + str(self.iperf_port)

                    tunnelIda = Popen(cmd1.split())
                    tunnelVolta = Popen(cmd2.split())
                    client_exec = Popen(cmdclient.split())
                    try:
                        sleep(10)
                        client_exec.wait(1)
                    except:
                        print('exception no teste (cliente)')
                        exception = True
                        estado = C_INICIAR

                    if not exception:
                        estado = C_RECEBER_RESULTADOS
                    # fecha os tuneis
                    close_processes([tunnelIda.pid, tunnelVolta.pid, client_exec.pid])
                    self.server_udp_hole = 0
                    self.server_udp_hole = 0

                if estado is C_RECEBER_RESULTADOS:
                    # ignorar serverReadies duplos que vierem por qualquer motivo
                    if self.serverReady:
                        self.serverReady = False
                    # Tempo suficiente pra par fazer as retransmissoes de
                    # resultado e chegar para o cliente
                    for i in range(0, result_retr_timeout * result_retr + 1):
                        sleep(0.5)
                        if self.endTest:
                            # recebeu resultado, envia ack
                            sendstr = "endTest_ack," + self.offer_thread.get_found_peer()
                            self.s2.sendto(sendstr.encode('utf-8'), ("0.0.0.0", 37711))

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

                    for i in range(0, 40):
                        sleep(0.5)
                        if self.gonnaTest:
                            self.gonnaTest = False
                            estado = S_TESTAR
                            break

                elif estado is S_TESTAR:

                    if max_retr == 0:
                        estado = S_FINALIZAR
                        continue
                    max_retr -= 1

                    # abre buracos por onde o cliente ira realizar o teste
                    udp_hole, socket_udp, keep_udp = self.open_udp_hole()
                    tcp_hole, socket_tcp, keep_tcp = self.open_tcp_hole()

                    if udp_hole == -1 or tcp_hole == -1:
                        # print("erro ao dar bind nos sockets do cliente")
                        estado = S_FINALIZAR
                        continue
                    elif udp_hole == -2 or tcp_hole == -2:
                        # print("erro ao abrir buracos do cliente")
                        estado = S_FINALIZAR
                        continue

                    time1 = datetime.now()
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

                    cmd = "socat -d -d udp-listen:" + str(self.udp_local_port) + ",reuseaddr udp:localhost:" + str(
                        self.iperf_port)
                    cmd2 = "socat -d -d udp-listen:" + str(
                        self.iperf_port + 1) + ",reuseaddr udp:" + ip_peer + ":" + str(
                        self.client_tcp_hole) + ",sp=" + str(self.tcp_local_port)

                    cmdserver = "python3 ../ultra_ping/echo.py --server --listen_port " + str(self.iperf_port)

                    serverString = "serverReady," + id_peer + "," + str(udp_hole) + "," + str(tcp_hole)
                    self.s2.sendto(serverString.encode('utf-8'), ("0.0.0.0", 37711))

                    serverRunning = True
                    # print("Servidor iniciando")
                    tunnelVinda = Popen(cmd.split())
                    tunnelIda = Popen(cmd2.split())
                    s = Popen(cmdserver.split())

                    retry = False
                    for i in range(0, 12):
                        sleep(1)
                        if self.gonnaTest:
                            self.gonnaTest = False
                            retry = True
                            break

                    close_processes([tunnelVinda.pid, tunnelIda.pid, s.pid])

                    if retry:
                        continue

                    # fecha o tunel
                    self.serverRunning = False

                    self.client_udp_hole = 0
                    self.client_tcp_hole = 0

                    estado = S_ENVIAR_RESULTADOS

                elif estado is S_ENVIAR_RESULTADOS:

                    # somente num_retr tentativas de mandar resultado
                    if result_retr == 0:
                        estado = S_FINALIZAR
                        continue
                    result_retr -= 1

                    # envia resultado ao par
                    vazao = "endTest," + id_peer
                    self.s2.sendto(vazao.encode('utf-8'), ("0.0.0.0", 37711))

                    # timeout de 3 secs
                    for i in range(0, result_retr_timeout):
                        sleep(0.5)
                        # recebeu ack
                        if self.endTest:
                            estado = S_FINALIZAR
                            self.serverRunning = False
                            retorno = True
                            break

        return retorno

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
                index = random.randint(0, len(real_peers) - 1)

                idPeer = real_peers[index]

                if idPeer not in chosen_peers:
                    chosen_peers.append(idPeer)

            self.offer_thread.set_peers(chosen_peers)

            self.offer_thread.kick_off()

    def callTest(self):
        while True:
            # kick off test offers if it still isnt
            self.select_peer()
            #   print("chamou select peer")
            if self.offer_thread.get_found_peer() and self.hole_port1 > 0:
                print("indo pro teste de vazao")
                self.throughput_test("normal")
                self.throughput_test("reverso")
                print("indo pro teste de latencia")
                self.latency_test("normal")
                self.latency_test("reverso")
                print("indo pro teste de jitter e perda")
                self.jitter_loss_test("normal")
                self.jitter_loss_test("reverso")
                print("rodando teste speedtest")
                cli_test = Popen("python3 speedtest.py".split())
                cli_test.wait()
                print("acabou todos os testes")
                sleep(DELAY_BUSCA)
                self.offer_thread.set_peers([])
                self.offer_thread.set_found_peer((False, "undefined"))
                print("found peer = False\n")
            sleep(5)

    def listen(self):
        if self.porta_udp > 0:
            try:
                self.s2.bind(('0.0.0.0', self.porta_udp))
                self.s1.bind(('0.0.0.0', self.porta_udp - 1))
                self.offer_thread.start()
            except:
                # print("erro ao fazer bind do socket na porta 37710")
                # esse exit so sai da thread
                # pensar como fechar o programa se esse bind nao funcionar
                exit(1)

        while True:
            dataa, sender = self.s2.recvfrom(1024)
            decodedData = dataa.decode('utf-8')
            splitData = decodedData.split(',')
            if splitData[0] == "add" and (
                    splitData[1] + "," + splitData[2] + "," + splitData[3] + "," + splitData[4]) not in self.listaPares:
                self.listaPares.append((splitData[1] + "," + splitData[2] + "," + splitData[3] + "," + splitData[4]))
            elif splitData[0] == "remove" and (
                    splitData[1] + "," + splitData[2] + "," + splitData[3] + "," + splitData[4]) in self.listaPares:
                self.listaPares.remove((splitData[1] + "," + splitData[2] + "," + splitData[3] + "," + splitData[4]))
            elif splitData[0] == "holeport":
                if sender[1] == 37711:
                    self.hole_port1 = int(splitData[1])
                if self.hole_address == "":
                    self.hole_address = splitData[2]
                # talvez dexar sempre sobescrever as portas publicas
                if self.public_port1 == 0:
                    self.public_port1 = int(splitData[3])
                if self.public_address == "":
                    self.public_address = splitData[4]
            elif splitData[0] == "serverReady" and self.offer_thread.get_found_peer() == splitData[3]:
                self.serverReady = True
                self.server_udp_hole = int(splitData[1])
                self.server_tcp_hole = int(splitData[2])
            elif splitData[0] == "gonnaTest" and self.offer_thread.get_found_peer() == splitData[3]:
                self.gonnaTest = True
                self.client_udp_hole = int(splitData[1])
                self.client_tcp_hole = int(splitData[2])
            elif splitData[0] == "vazao":
                self.bits_per_sec_self = self.extract_throughput(splitData[1])
            elif splitData[0] == "endTest" and self.offer_thread.get_found_peer() == splitData[len(splitData) - 1]:
                self.endTest = True
                if len(splitData) == 3:
                    self.bits_per_sec_self = self.extract_throughput(splitData[1])
            elif splitData[0] == "endTest_ack" and self.offer_thread.get_found_peer() == splitData[len(splitData) - 1]:
                self.endTest = True
            elif splitData[0] == "offer" and not self.offer_thread.get_found_peer():
                self.offer_thread.set_found_peer((splitData[1], "server"))
                sendstr = "offer_res," + splitData[1]
                self.s1.sendto(sendstr.encode('utf-8'), ("0.0.0.0", 37711))
            elif splitData[0] == "offer" and self.offer_thread.get_found_peer():

                sendstr = "offer_rjct," + splitData[1]
                self.s1.sendto(sendstr.encode('utf-8'), ("0.0.0.0", 37711))
            elif splitData[0] == "offer_rjct":

                self.offer_thread.ack(splitData[1])
            elif splitData[0] == "offer_res" and self.offer_thread.get_found_peer() == False:

                self.offer_thread.ack(splitData[1])
                self.offer_thread.set_found_peer((splitData[1], "client"))
            elif splitData[0] == "offer_abort" and self.offer_thread.get_found_peer() and splitData[
                1] == self.offer_thread.get_found_peer():

                self.offer_thread.set_found_peer((False, "undefined"))
                sendstr = "offer_abort_ack," + splitData[1]
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
                # print("erro ao dar bind no socket udp do cliente")
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
                # print("erro ao dar bind no socket tcp do cliente")
                return -1, -1, -1

            keep_tcp = KeepHoleAlive(socket_tcp, 2)

            keep_tcp.start()

            return tcp_hole, socket_tcp, keep_tcp

        return -2, -2, -2



def peerNetwork():
    process = Popen("node ../PeerNetwork.js".split())


def main():
    proof_of_concept = PoC()

    socket_listener = threading.Thread(target=proof_of_concept.listen, daemon=True)
    socket_listener.start()

    call_test = threading.Thread(target=proof_of_concept.callTest, daemon=True)
    call_test.start()
    # listener2 = threading.Thread(target=notPing, daemon=True)
    # listener2.start()

    pnthread1 = threading.Thread(target=peerNetwork, daemon=True)
    pnthread1.start()

    signal.signal(signal.SIGINT,signal_handler)
    # se tirar isso é como se executasse o programa no terminal com & depois e ele não pegaria o sigint
    proof_of_concept.offer_thread.join()
    # continueProgram=True
    # while continueProgram

def signal_handler(sig, frame):
    sys.exit(0)

if __name__ == '__main__':
    main()

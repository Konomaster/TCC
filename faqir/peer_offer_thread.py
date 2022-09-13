from threading import Thread
import threading
from time import sleep

lock = threading.Lock()

class PeerOfferThread(Thread):

    def __init__(self, socket, num_rtr, timeout):
        super(PeerOfferThread, self).__init__()
        self._stop_event = threading.Event()
        self.socket = socket
        self.found_peer = False # done
        self.my_role = "undefined" # done
        self.timeout = timeout
        self.peers = [] #
        self.peers_ack = [] #
        self.num_rtr = num_rtr
        self.offers_sent = False
        self.offers_ended = True

    # send offers and make sure to warn offered peers
    # when found a peer
    def keep_alive(self):
        while not self.stopped():
            # monitor
            print("pares a comunicar: ")
            print(self.peers)
            rtr = 1 + self.num_rtr
            with lock:
                if not self.offers_sent and not self.found_peer and self.peers != []:
                    self.offers_sent = True
                    for peer in self.peers:
                        # ver se da pra colocar meu id ao invés
                        offer_string = "offer," + peer
                        self.socket.sendto(offer_string.encode('utf-8'), ("0.0.0.0", 37711))

                elif self.offers_sent and self.found_peer and rtr > 0:
                    rtr -= 1

                    for i in range(0, len(self.peers)):
                        if self.peers[i] != self.found_peer and self.peers_ack[i] is False:
                            abort_string = "offer_abort," + self.peers[i]
                            self.socket.sendto(abort_string.encode('utf-8'), ("0.0.0.0", 37711))

                    if rtr == 0:
                        self.offers_ended = True

                sleep(self.timeout)

    def kick_off(self):
        if self.offers_ended is True:
            self.offers_ended = False
            self.offers_sent = False

    def is_kicked_off(self):
        return not self.offers_ended


    def peers(self,peers):
        with lock:
            if self.offers_ended:
                self.peers=peers
                self.peers_ack=[]
                for _ in self.peers:
                    self.peers_ack.append(False)

    @property
    def found_peer(self):
        with lock:
            return self.found_peer

    def found_peer(self,found_peer_myrole):
        with lock:
            peer, role = found_peer_myrole
            self.found_peer = peer
            self.my_role = role


    def role(self):
        with lock:
            return self.my_role


    def ack(self,peerId):
        with lock:
            for i in range(0,len(self.peers)):
                if self.peers[i] == peerId:
                    self.peers_ack[i] = True


    def run(self) -> None:
        self.keep_alive()

    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()

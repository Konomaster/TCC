#!/usr/bin/python

"""
Nat simulation using mininet

Topology:

   dht0  dht1  dht2  dht3  dht4  dht5
    |     |     |     |     |     |
    -------------------------------
                   |
                  inet0
                   |
            ----------------
            |              |
           nat1           nat2
            |              |
           s1              s2
            |              |
          alice           bob

"""

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.log import setLogLevel, info
from mininet.util import irange

class DhtTopo(Topo):
    "Topology creation."
    def __init__(self, **opts):
        Topo.__init__(self, **opts)

        # -- create central switch
        internet = self.addSwitch('inet0')

        # -- add dht node
        bottstrap = self.addHost('dht0', ip='200.0.0.1/24')
        self.addLink(bottstrap, internet)
        for i in irange(1, 5):
            node = self.addHost('dht%d' % i, ip='200.0.0.%d/24' % (i + 30))
            self.addLink(node, internet)

        self.addPeer('alice', 1, internet);
        self.addPeer('bob', 2, internet);

    def addPeer(self, name='alice', i=1, internet='inet'):
        # -- add Alice scructure
        # add NAT to topology
        nat = self.addNode('nat%d' % i, ip='200.0.0.%d/24' % (i + 1), defaultRoute='via 200.0.0.1')
        switch = self.addSwitch('s%d' % i)
        # connect NAT to inet and local switches
        self.addLink(nat, internet, intfName1='eth0')
        self.addLink(nat, switch, intfName1='eth1', params1={'ip':'192.168.%d.1/24' % i})
        # add host and connect to local switch
        alice = self.addHost(name, ip='192.168.%d.2/24' % i, defaultRoute='via 192.168.%d.1' % i);
        self.addLink(alice, switch)

def setupNat(nat):
    nat.cmd('iptables -F')
    nat.cmd('iptables -A FORWARD -i eth1 -j ACCEPT')
    nat.cmd('iptables -A FORWARD -o eth1 -j ACCEPT')
    nat.cmd('iptables -A INPUT -i eth0 -m state --state ESTABLISHED,RELATED -j ACCEPT')
    nat.cmd('iptables -A INPUT -p icmp -m state --state NEW -j ACCEPT')
    nat.cmd('iptables -A INPUT -i eth0 -m state --state NEW -j DROP')
    nat.cmd('iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE')
    nat.cmd('sysctl -w net.ipv4.ip_forward=1')

def run():
    topo = DhtTopo()
    net = Mininet(topo=topo)
    net.start()

    info('*** Config NAT\n')
    nat1 = net.get('nat1')
    setupNat(nat=nat1)
    nat2 = net.get('nat2')
    setupNat(nat=nat2)

    info('*** Ping all\n')
    net.pingAll();

    info('******* PoC using Mininet\n')
    info('*** Start DhtNode\n')
    for i in irange(0, 5):
        dht = net.get('dht%d' % i)
        dht.cmd('sudo node dht-node.js 200.0.0.1:6881 &');

    info('*** Bob and Alice start comunicate with DhtNode \n')
    alice = net.get('alice')
    alice.cmd('sudo node peer.js 200.0.0.1:6881 &');
    bob = net.get('bob')
    bob.sendCmd('sudo node peer.js 200.0.0.1:6881');
    bob.waitOutput(True);

    info('******* End of PoC\n')
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    run()

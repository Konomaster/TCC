const test = require('tape');
const createEnv = require('./net/dht-bootstrap');
const PeerNetwork = require('../');

let peerNames = {
    '2c02f64d94eda01c': 'Alice',
    '9155d5e058719a6e': 'Bob',
};
let idToName = (peerId) => {
    if (peerNames[peerId]) { return peerNames[peerId]; }
    return peerId;
};

let dhtEnv;
test('> Create env', function(t) {
    dhtEnv = createEnv(() => t.end(), 20);
});

test('Public API', function(t) {
    t.plan(10);

    let message = Buffer.from('HELLO!');
    let createPeer = (port, totalPeers) => {
        let complete = (totalPeers - 1) * 2;
        let destroy = () => {
            complete--;
            if (complete === 0) {
                t.pass(idToName(peer.id) + ' close socket');
                peer.close();
            }
        };
        let peer = new PeerNetwork({
            group: 'TEST',
            password: 'test',
            bootstrap: dhtEnv.bootstrap
        });
        peer.on('ready', () => {
            t.assert(peer.isReady(),
                idToName(peer.id) + ' is alive on port ' + port
            );
        });

        peer.on('message', (msg, peerId) => {
            t.assert(Buffer.compare(message, msg) === 0,
                idToName(peer.id) + ' receive hello from ' + idToName(peerId)
            );
            destroy();
        });
        peer.on('peer', (peerId) => {
            t.assert(peer.getPeers().length > 0,
                idToName(peer.id) + ' now can talk with ' + idToName(peerId)
            );
            peer.send(message, peerId, () => {
                t.pass(idToName(peer.id) + ' send hello message to ' + idToName(peerId));
                destroy();
            });
        });

        peer.start(port);

        return peer;
    };

    createPeer(21201, 2);
    createPeer(21202, 2);
});

test('> Destroy env', function(t) {
    dhtEnv.destroy(() => t.end());
});

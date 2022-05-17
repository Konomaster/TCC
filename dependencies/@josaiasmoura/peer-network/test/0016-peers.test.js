const test = require('tape');

test('Network - Peers', function(t) {
    t.plan(14);

    const Peers = require('../lib/network/peers');

    let peers = new Peers(function(ipport) {
        return ipport;
    });

    // --
    let peer = '100.100.0.1:8008';
    peers.add(peer);
    t.assert(!!peers.get(peer), 'Peer added');

    // --
    let candidate = {
        address: '10.0.0.1', port: 8008
    };
    peers.addCandidate(peer, candidate);
    t.assert(!!peers.get(candidate), 'Peer candidate added');

    // --
    let candidateLoopback = {
        address: '127.0.0.1', port: 8008
    };
    peers.addCandidate(peer, candidateLoopback);
    t.assert(!!peers.get(candidateLoopback), 'Peer candidate local');

    // --
    peers.online(peer);
    t.assert(peers.get(peer).isOnline, 'Peer online');
    peers.online(candidate);
    t.assert(peers.get(candidate).isOnline, 'Peer candidate online');

    // --
    t.assert(peers.onlines().length > 0, 'Peers onlines');

    // --
    peers.offline(peer);
    t.assert(!peers.get(peer).isOnline, 'Peer offline');
    peers.offline(candidate);
    t.assert(!peers.get(candidate).isOnline, 'Peer candidate offline');

    // --
    t.assert(peers.has(peer), 'Peer found');
    t.assert(peers.has(candidate), 'Peer candidate found');

    // --
    t.assert(peers.length > 0, 'Peers length ' + peers.length);

    // --
    let count = peers.length;
    peers.forEach((peer) => {
        count--;
    });
    t.assert(count === 0, 'Peers forEach');

    // --
    t.assert(peers.getById(peer), 'Peer found by id');

    // --
    peers.clear();
    t.assert(peers.length === 0, 'Peers clear');
});

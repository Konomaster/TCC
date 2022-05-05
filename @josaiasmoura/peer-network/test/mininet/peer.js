// const mn = require('mininet/host');
const PeerNetwork = require('../../');

let port = 21201;
let message = Buffer.from('HELLO!');
let args = process.argv.slice(2);

let complete = 2;
let destroy = () => {
    complete--;
    if (complete === 0) {
        console.log(idToName(peer.id) + ' close socket');
        peer.close();
    }
};
let peerNames = {
    'e7528b70bf74e0c5': 'Alice',
    'ed438a9cb3e604a1': 'Bob',
};
let idToName = (peerId) => {
    if (peerNames[peerId]) { return peerNames[peerId]; }
    return peerId;
};

let peer = new PeerNetwork({
    group: 'TEST',
    password: 'test',
    bootstrap: [ args[0] || '127.0.0.1:6881' ]
});
peer.on('ready', () => {
    console.log(idToName(peer.id) + ' is alive on port ' + port);
});

peer.on('message', (msg, peerId) => {
    console.log(idToName(peer.id) + ' receive hello from ' + idToName(peerId));
    destroy();
});
peer.on('peer', (peerId) => {
    console.log(idToName(peer.id) + ' now can talk with ' + idToName(peerId));
    peer.send(message, peerId, () => {
        console.log(idToName(peer.id) + ' send hello message to ' + idToName(peerId));
        destroy();
    });
});

peer.start(port);

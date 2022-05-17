const debug = require('debug')('Environment');
const BitTorrentDHT = require('bittorrent-dht');
const ed = require('ed25519-supercop');

require('./k-rpc-socket-ip');

function destroyAllNodes(nodes, callback) {
    let count = nodes.length;
    nodes.forEach(function(node) {
        node.destroy(function() {
            count--;
            if (count === 0 && typeof callback === 'function') {
                callback();
            }
        });
    });
}

function log(dht) {
    let ping = new Map();
    let startTime = Date.now();
    let bytesLoaded = 0;
    dht.krpcSocket.on('response', (resp, peer) => {
        bytesLoaded += peer.size;
        let kb = (bytesLoaded / 1024).toFixed(2) + ' kb';
        let time = ((Date.now() - startTime) / 1000 / 60).toFixed(2) + ' min';
        let log = '[==RES==][' + kb + ' in ' + time + ']';
        let host = peer.address + ':' + peer.port;
        if (!ping.has(host)) {
            ping.set(host, 0);
        }
        ping.set(host, ping.get(host) + 1);
        debug(log, ' acc ', host, ping.get(host), resp);
    });
}

module.exports = function(callback, qtd = 5, serverPort = 6881) {
    let nodes = [];
    let bootstrap = ['127.0.0.1:' + serverPort];
    let listen = 0;

    let server = new BitTorrentDHT({ bootstrap: false });
    server._onannouncepeer = server._onget = server._onput = function() {};
    nodes.push(server);

    server.listen(serverPort, () => {
        listen++;
        debug('bootstrap node is listen on port ' + serverPort);
        if (qtd === 0) {
            if (typeof callback === 'function') {
                callback();
            }
            return;
        }
        for (var port = serverPort + 1; port <= serverPort + qtd; port++) {
            let node = new BitTorrentDHT({
                bootstrap: bootstrap,
                verify: ed.verify
            });
            server.addNode({
                host: '127.0.0.1',
                port: port
            });
            let nodePort = port;
            node.listen(nodePort, () => {
                debug('new node is listen on port ' + nodePort);
                listen++;
                if (listen === qtd + 1 && typeof callback === 'function') {
                    callback();
                }
            });
            nodes.push(node);
        }
    });

    return {
        nodes,
        log,
        bootstrap,
        destroy(callback) {
            destroyAllNodes(nodes, callback);
        }
    };
};

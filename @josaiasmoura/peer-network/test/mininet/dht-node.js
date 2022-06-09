const BitTorrentDHT = require('bittorrent-dht');
const ed = require('ed25519-supercop');

require('../net/k-rpc-socket-ip');

let args = process.argv.slice(2);

let server = new BitTorrentDHT({
    bootstrap: args[0] || false,
    verify: ed.verify
});

server.listen(6881, function() {
    console.log('new node is listen on port 6881');
});

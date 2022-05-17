const KRPCSocket = require('k-rpc-socket');

// -- Modify socket to echo IP on responses
KRPCSocket.prototype.response = function(peer, req, res, cb) {
    let host = Buffer.from((peer.address || peer.host)
        .split('.')
        .map(str => parseInt(str))
    );
    let port = Buffer.alloc(2);
    port.writeUInt16BE(peer.port);
    let ip = Buffer.concat([host, port]);
    this.send(peer, {ip: ip, t: req.t, y: 'r', r: res}, cb);
};

module.exports = KRPCSocket;

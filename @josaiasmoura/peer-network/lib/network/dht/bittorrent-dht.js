/**
 * Changes to expand the bittorrent-dht module
 * (from https://github.com/webtorrent/bittorrent-dht/blob/1bfffdc1cae06ae27d9583ca96caf37555300360/client.js )
 *
 * @license https://github.com/webtorrent/bittorrent-dht/blob/1bfffdc1cae06ae27d9583ca96caf37555300360/LICENSE
 */

var DHT = require('bittorrent-dht');
var bencode = require('bencode');
var equals = require('buffer-equals');

DHT.prototype.announce = function(infoHash, port, cb) {
    if (typeof port === 'function') return this.announce(infoHash, 0, port);
    infoHash = toBuffer(infoHash);
    if (!cb) cb = noop;

    var table = this._tables.get(infoHash.toString('hex'));
    if (!table) return this._preannounce(infoHash, port, cb);

    if (this._host) {
        var dhtPort = this.listening ? this.address().port : 0;
        this._addPeer(
            {host: this._host, port: port || dhtPort},
            infoHash,
            {host: this._host, port: dhtPort}
        );
    }

    var message = {
        q: 'announce_peer',
        a: {
            id: this._rpc.id,
            token: null, // queryAll sets this
            info_hash: infoHash,
            port: port,
            implied_port: port ? 0 : 1
        }
    };

    var self = this;
    var visit = function(resp, peer) {
        self.emit('announced', peer);
    };

    this._debug('announce %s %d', infoHash, port);
    this._rpc.queryAll(table.closest(infoHash), message, visit, cb);
};

DHT.prototype.putOnce = function(node, opts, cb) {
    if (!cb) cb = noop;

    var isMutable = !!opts.k;
    var v = typeof opts.v === 'string' ? Buffer.from(opts.v) : opts.v;
    var key = isMutable
        ? this._hash(opts.salt ? Buffer.concat([opts.k, opts.salt]) : opts.k)
        : this._hash(bencode.encode(v));

    node.host = node.host || node.address;
    if (!node.id) {
        node = this.nodes.toArray().find(function(n) {
            return n.host === node.host && n.port === node.port;
        });
    }
    if (!node) return cb(new Error('node not found'));

    if (!node.token) {
        var self = this;
        return this.getOnce(node, key, function() {
            if (!node.token) return cb(new Error('token not found'));
            self.putOnce(node, opts, cb);
        });
    }

    var message = {
        q: 'put',
        a: {
            id: this._rpc.id,
            token: null, // queryAll sets this
            v: v
        }
    };

    if (isMutable) {
        if (typeof opts.cas === 'number') message.a.cas = opts.cas;
        if (opts.salt) message.a.salt = opts.salt;
        message.a.k = opts.k;
        message.a.seq = opts.seq;
        if (typeof opts.sign === 'function') message.a.sig = opts.sign(encodeSigData(message.a));
        else if (Buffer.isBuffer(opts.sig)) message.a.sig = opts.sig;
    } else {
        this._values.set(key.toString('hex'), message.a);
    }

    this._rpc.query(node, message, function(err, res, peer) {
        if (res && res.r && res.r.token) {
            node.token = res.r.token;
        }
        if (err) {
            return cb(err, key, 0);
        }
        cb(null, key, 1);
    });

    return key;
};

DHT.prototype.getOnce = function(node, key, opts, cb) {
    key = toBuffer(key);
    if (typeof opts === 'function') {
        cb = opts;
        opts = null;
    }

    node.host = node.host || node.address;
    if (!node.id) {
        node = this.nodes.toArray().find(function(n) {
            return n.host === node.host && n.port === node.port;
        });
    }
    if (!node) return cb(new Error('node not found'));

    if (!opts) opts = {};
    var verify = opts.verify || this._verify;
    var hash = this._hash;
    var value = null;

    var query = {
        q: 'get',
        a: {
            id: this._rpc.id,
            target: key
        }
    };

    this._rpc.query(node, query, function(err, res, peer) {
        if (res && res.r && res.r.token) {
            node.token = res.r.token;
        }

        if (err) {
            return cb(err);
        }

        onreply(res);
        cb(null, value);
    });

    function onreply(message) {
        var r = message.r;
        if (!r || !r.v) return true;

        var isMutable = r.k || r.sig;

        if (opts.salt) r.salt = Buffer.from(opts.salt);

        if (isMutable) {
            if (!verify || !r.sig || !r.k) return true;
            if (!verify(r.sig, encodeSigData(r), r.k)) return true;
            if (equals(hash(r.salt ? Buffer.concat([r.k, r.salt]) : r.k), key)) {
                if (!value || r.seq > value.seq) value = r;
            }
        } else {
            if (equals(hash(bencode.encode(r.v)), key)) {
                value = r;
                return false;
            }
        }

        return true;
    }
};

function noop() {}

function encodeSigData(msg) {
    var ref = { seq: msg.seq || 0, v: msg.v };
    if (msg.salt) ref.salt = msg.salt;
    return bencode.encode(ref).slice(1, -1);
}

function toBuffer(str) {
    if (Buffer.isBuffer(str)) return str;
    if (ArrayBuffer.isView(str)) return Buffer.from(str.buffer, str.byteOffset, str.byteLength);
    if (typeof str === 'string') return Buffer.from(str, 'hex');
    throw new Error('Pass a buffer or a string');
}

module.exports = DHT;

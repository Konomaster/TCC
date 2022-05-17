/**
 * @author Josaias Moura
 */

'use strict';

const debug = require('debug')('Dht');
const dgram = require('dgram');
const address = require('network-address');
const EventEmitter = require('events');
const KRPCSocket = require('k-rpc-socket');
const KRPC = require('k-rpc');
const utils = require('../../utils');
const errors = require('../../errors');
const DHT = require('./bittorrent-dht');
const ed = require('ed25519-supercop');
const crypto = require('crypto');

class DhtProtocol extends EventEmitter {
    /**
     * Discover and manage nodes interested in exchanging UDP messages
     *
     * @constructor
     * @fires Dht#close
     * @fires Dht#warning
     * @fires Dht#peer
     * @fires Dht#query
     * @fires Dht#listening
     * @fires Dht#announce
     * @param {object} opts
     * @param {string} opts.group Name of P2P group
     * @param {string} opts.password Strong password to encrypt all P2P data
     * @param {Buffer} [opts.id] An unique indentification of peer (default value is random generated)
     * @param {integer} [opts.concurrency] (default value is 16)
     * @param {dgram.Socket} [opts.udpSocket]
     * @param {Array.<string>} [opts.bootstrap] Bootstrap Bitorrent DHT server (default value: router.bittorrent.com:6881, router.utorrent.com:6881, dht.transmissionbt.com:6881)
     */
    constructor(opts = {}) {
        super();

        if (typeof opts.group !== 'string' || typeof opts.password !== 'string') {
            let err = errors.ERR_INVALID_ARG(
                'opts.group or opts.password can\'t be empty'
            );
            process.nextTick(() => {
                this.emit('error', err);
            });
            throw err;
        }

        this.id = opts.id || crypto.randomBytes(20);
        this.concurrency = opts.concurrency || 16;

        // Generate SHA-1 with group name and password
        let tempHash = utils.sha1(opts.group);
        this.secret = utils.sha1(opts.password + tempHash.toString('hex'));
        let infoHash = utils.sha1(opts.group + this.secret);

        // Genetate network group public/private keys
        this.groupKeyPair = utils.generateSign(this.secret, infoHash);
        this.groupHash = utils.sha1(this.groupKeyPair.publicKey);
        this.infoHash = this.groupHash;

        this.localAddress = {
            // address: null,
            port: 0
        };
        Object.defineProperty(this.localAddress, 'address', {
            enumerable: true,
            get: function() { return address(); }
        });

        this.remoteAddress = {
            address: null,
            port: 0,
        };

        this._symmetricNAT = false;
        this._seq = new Map();

        this.udpSocket = opts.udpSocket || dgram.createSocket('udp4');
        this.krpcSocket = new KRPCSocket({
            timeout: opts.timeout || 5000,
            socket: this.udpSocket
        });
        let krpc = opts.krpc = new KRPC({
            id: this.id,
            nodes: opts.bootstrap,
            krpcSocket: this.krpcSocket,
            concurrency: opts.concurrency
        });

        opts.verify = ed.verify;

        this.dht = new DHT(opts);

        this.dht.on('peer', (peer, infoHash, from) => {
            if (peer && peer.port > 1) {
                this.emit('peer', {
                    address: peer.host || peer.address,
                    port: peer.port
                }, from);
            }
        });

        krpc.removeAllListeners('query');
        krpc.on('query', (query, peer) => {
            var q = query.q.toString();
            if (!query.a) return;
            if (q === 'ping' ||
                q === 'get_peers' ||
                q === 'find_node') {
                return krpc.response(peer, query, {id: krpc.id});
            }

            // this.emit('query', query, peer);
        });

        this.dht.on('close', () => {
            this.emit('close');
        });

        this.dht.on('announced', (peer) => {
            this.emit('announce', peer);
        });
    }

    get listening() {
        return this.dht.listening;
    }

    /**
     * Peer starts listen on UDP port
     *
     * @param {integer} [port=21201]
     * @param {Function} [callback]
     * @return {void}
     */
    listen(port, callback) {
        callback = callback || function() {};
        if (this.dht.listening || this.dht.destroyed) {
            callback(new Error('Is now listening'));
            return;
        }

        // --
        if (typeof port === 'function') {
            callback = port;
            port = null;
        }
        if (port <= 1 || port > 65535) {
            port = null;
        }
        port = port || 21201;

        // --
        let bind = (err) => {
            this.localAddress.port = this.dht.address().port;
            callback(err);
            process.nextTick(() => {
                this.emit('listening');
            });

            // Try open a port using UPnP
            utils.openUPnPPort(this.localAddress.port, (err, externalIp) => {
                if (!err) {
                    this._upnp = true;
                    this._upnpExternalIp = externalIp;
                }
            });
        };

        this.dht.listen(port, bind);
    }

    /**
     * Return primitive value of object
     *
     * @param {Function} [callback]
     * @param {boolean} [announce=false]
     * @return {string}
     */
    lookup(callback, announce) {
        callback = callback || function() {};

        let remoteIps = {};
        let count = 0;

        let onResponse = (message, node) => {
            if (count >= 16) return;

            // -- check if the response has the public IP:Port
            let remote = utils.findRemoteIp(message);

            if (remote) {
                count++;
                let ipIndex = remote.address + ':' + remote.port;
                if (!remoteIps[ipIndex]) {
                    remote.count = 0;
                    remoteIps[ipIndex] = remote;
                }
                remoteIps[ipIndex].count++;
            }
        };

        this.krpcSocket.on('response', onResponse);

        this.dht.lookup(this.groupHash, (err) => {
            this.krpcSocket.removeListener('response', onResponse);

            _updateRemoteIp(this, remoteIps);

            if (announce) {
                this.dht.announce(
                    this.groupHash,
                    this.remoteAddress.port,
                    (err, n) => {
                        this.emit('announce-done', err, n);
                    }
                );
            }

            callback(err);
        });
    }

    /**
     * Destroy
     *
     * @param {Function} [callback]
     * @return {void}
     */
    destroy(callback) {
        process.nextTick((arg) => {
            this.removeAllListeners();
        });
        this.dht.destroy.apply(this.dht, arguments);
    }

    /**
     * Get UDP socket
     *
     * @return {Socket}
     */
    getUDPSocket() {
        return this.udpSocket;
    }

    /**
     * Get closest nodes list
     *
     * @return {Array}
     */
    getClosestNodes() {
        return this.dht.nodes.closest(this.groupHash, 32);
    }

    /**
     * Store value on DHT network
     *
     * @param {(string|Buffer)} key
     * @param {Buffer} bufferValue
     * @param {Object} [node]
     * @param {Function} [callback]
     * @return {void}
     */
    putSharedData(key, bufferValue, node, callback) {
        if (typeof node === 'function') {
            callback = node;
            node = null;
        }
        callback = callback || function() {};

        let opts = {
            k: this.groupKeyPair.publicKey,
            seq: 1,
            cas: undefined,
            v: bufferValue,
            salt: typeof key === 'string'
                ? Buffer.from(key, 'ascii')
                : key,
            sign: this.groupKeyPair.sign
        };

        let keyStr = opts.salt.toString('hex');
        if (node) {
            keyStr += '-' + (node.address || node.host) + ':' + node.port;
        }
        if (!this._seq.has(keyStr)) {
            this.getSharedData(key, node, (err) => {
                if (!err) {
                    this.putSharedData(key, bufferValue, node, callback);
                } else {
                    callback(err, null);
                }
            });
            return;
        }

        let seq = this._seq.get(keyStr);
        opts.seq = seq + 1;
        opts.cas = seq;

        let done = function(err, hash) {
            callback(err);
        };

        if (node) {
            this.dht.putOnce(node, opts, done);
        } else {
            this.dht.put(opts, done);
        }
    }

    /**
     * Get value on DHT network
     *
     * @param {(string|Buffer)} key
     * @param {Object} [node]
     * @param {Function} [callback]
     * @return {void}
     */
    getSharedData(key, node, callback) {
        if (typeof node === 'function') {
            callback = node;
            node = null;
        }
        callback = callback || function() {};

        let opts = {
            seq: 0,
            salt: typeof key === 'string'
                ? Buffer.from(key, 'ascii')
                : key
        };

        let keyStr = opts.salt.toString('hex');
        if (node) {
            keyStr += '-' + (node.address || node.host) + ':' + node.port;
        }
        if (this._seq.has(keyStr)) {
            opts.seq = this._seq.get(keyStr);
        }

        let hash = utils.sha1(Buffer.concat([
            this.groupKeyPair.publicKey,
            opts.salt
        ]));

        let done = (err, resp) => {
            if (resp) {
                this._seq.set(keyStr, resp.seq || 0);
            }
            if (!this._seq.has(keyStr)) {
                this._seq.set(keyStr, 0);
            }
            if (!err && resp && resp.v) {
                callback(err, resp.v);
            } else {
                callback(err, null);
            }
        };

        if (node) {
            this.dht.getOnce(node, hash, opts, done);
        } else {
            this.dht.get(hash, opts, done);
        }
    }
}

/**
 *  Private (Not public API)
 *  ------
 */

/**
 * Update public internet IP:Port
 *
 * @private
 * @param {DhtProtocol} self
 * @param {Object} remoteIps
 * @return {void}
 */
function _updateRemoteIp(self, remoteIps) {
    if (remoteIps) {
        let ips = [];
        let qtdResponses = 0;
        Object.keys(remoteIps).forEach((index) => {
            qtdResponses += remoteIps[index].count;
            ips.push(remoteIps[index]);
            delete remoteIps[index];
        });

        ips.sort((a, b) => {
            return a.count - b.count;
        });

        if (ips.length === 0) {
            return;
        }

        let remoteIpCandidate = ips[0];

        if (remoteIpCandidate.count === 1 && qtdResponses > 1) {
            self._symmetricNAT = true;
            self.emit('warning', new Error('Symmetric NAT?!'));
            debug('Warning! Symmetric NAT?!');
        }

        self.remoteAddress.address = remoteIpCandidate.address;
        self.remoteAddress.port = remoteIpCandidate.port;
    }
}

exports = module.exports = DhtProtocol;

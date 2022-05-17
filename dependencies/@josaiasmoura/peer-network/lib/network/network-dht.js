/**
 * @author Josaias Moura
 */

'use strict';

const debug = require('debug')('NetworkDHT');
const NetworkBase = require('./network-base');
const CallbackQueue = require('../callback-queue');
const errors = require('../errors');
const utils = require('../utils');
const Peers = require('./peers');
const packet = require('./packet');
const AES = require('./security/aes');

const KEEP_ALIVE_TIME = 10000;
const LOOKUP_TIME = 20000;
const PEER_OFFLINE_TIME = 20000 * 6; // 2min
const ANNOUNCE_TIME = 20000 * 12; // 4min

class NetworkDht extends NetworkBase {
    /**
     * @fires NetworkBase#alive
     * @fires NetworkBase#destroy
     * @fires NetworkBase#message
     * @fires NetworkBase#online
     * @fires NetworkBase#offline
     * @param {Object} dht
     * @constructor
     */
    constructor(dht) {
        super();

        if (!dht) {
            throw errors.ERR_FATAL('DhtProtocol is needed');
        }

        this.__idFunc = function(info) {
            if (typeof info === 'object') {
                info = info.address + ':' + info.port;
            }
            return utils.sha1(info).slice(0, 8).toString('hex');
        };
        this.__peers = new Peers(this.__idFunc);
        this.__dht = dht;
        this.__socket = dht.udpSocket;
        this.__announceTime = 0;
        this.__queue = new CallbackQueue(1e5);
        this.__security = new AES(dht.secret);

        this.stats = {
            startTime: 0,
            bytesReceived: 0,
            bytesSended: 0
        };

        this.__socket.on('message', (msg, from) => {
            this.stats.bytesReceived += (from.size + 8 + 20);
            _onUdpMessage(this, msg, from);
        });

        let addPeer = (peer) => {
            let peerObj = this.__peers.add(peer);
            if (peerObj) {
                peerObj.responseTime = 0;
                peerObj.sendTime = 0;
                peerObj.isMe = utils.equalsAddress(peer, dht.remoteAddress);
            }
            return peerObj;
        };

        this.__dht.on('announce', (target) => {
            debug('[announce]', target);
            this.__announceTime = Date.now();
            _onAnnounceStoreLocalCandidates(this, target);
        });

        this.__dht.on('peer', (peer, from) => {
            if (!this.__peers.has(peer)) {
                debug('[found potential peer]', peer);
                let peerObj = addPeer(peer);

                // dont ping itself
                if (!peerObj.isMe) {
                    _ping(this, peerObj);
                    _ping(this, peerObj);
                }

                // find local addresses candidates
                _onFindLocalCandiates(this, peer, from);
            }
        });

        let onListen = () => {
            _keepAlive(this);
            _lookup(this, () => {
                if (dht.remoteAddress.address) {
                    let myself = addPeer(dht.remoteAddress);
                    myself.isMe = true;

                    let selfCandidate = {
                        address: dht.localAddress.address,
                        port: dht.localAddress.port,
                    };

                    this.__peers.addCandidate(dht.remoteAddress, selfCandidate);
                    this.__peers.online(selfCandidate);
                }

                if (!this.stats.startTime) {
                    this.stats.startTime = Date.now();
                }

                this.setReady(true);

                this.__queue.flush().forEach((err) => {
                    debug('[error]', err);
                });

                _lookup(this); // lookup again, after announce
            });
        };

        if (this.__dht.listening) {
            onListen();
        } else {
            this.__dht.once('listening', onListen);
        }

        this.once('destroy', () => {
            _lookup.stop(this);
            _keepAlive.stop(this);
            this.__peers.clear();
            this.__queue.clear();
            this.__dht.destroy();
        });
    }

    /**
     * Get peer address
     *
     * @return {string}
     */
    myID() {
        if (this.__dht.remoteAddress && this.__dht.remoteAddress.address) {
            return this.__idFunc(
                this.__dht.remoteAddress.address + ':' +
                this.__dht.remoteAddress.port
            );
        }
        return '';
    }

    /**
     * @return {Array.<string>}
     */
    peersIDs() {
        return this.__peers.onlines().map((obj) => {
            return obj.id;
        });
    }

    /**
     * @param {Buffer} buf
     * @param {string} peerId
     * @param {Function} [callback]
     * @return {void}
     */
    send(buf, peerId, callback) {
        if (!this.isAlive()) {
            return callback(errors.ERR_FATAL('Network is not alive'));
        }

        callback = callback || function() {};

        let peer = this.__peers.getById(peerId);

        if (peer && peer.isOnline) {
            peer.sendTime = Date.now();

            buf = this.__security.encrypt(buf);
            let encoded = packet.encode(buf);

            this.__socket.send(encoded, peer.port, peer.address, callback);
        } else {
            callback(errors.ERR_FATAL('Peer is offline or not found'));
        }
    }
}

/**
 * Receive a UDP packet (any)
 *
 * @private
 * @param {NetworkDht} self
 * @param {Buffer} msg
 * @param {Object} from
 * @return {void}
 */
function _onUdpMessage(self, msg, from) {
    if (!Buffer.isBuffer(msg) || msg.length < 2) return;

    // verify if 'from' is a trustly address
    let peer = self.__peers.get(from);
    if (!peer) {
        return; // discard packet
    }

    // verify if msg is a valid packet
    let msgContent;
    try {
        let decoded = packet.decode(msg);
        if (decoded.length > 0) {
            decoded = self.__security.decrypt(decoded);
        }
        msgContent = decoded;
    } catch (e) {
        return; // discard packet
    }

    // log response time
    peer.responseTime = Date.now();
    if (!peer.isOnline) {
        self.__peers.online(from);
        _ping(self, peer, true); // pong

        if (self.isReady()) {
            self.emit('online', peer.id);
        } else {
            self.__queue.push(() => {
                self.emit('online', peer.id);
            });
        }
    }

    // packet is empty?
    if (msgContent.length === 0) {
        _ping(self, peer); // pong
        return;
    }

    // everithing is ok! reflect event
    if (msgContent.length > 0) {
        if (self.isReady()) {
            self.emit('message', msgContent, peer.id);
        } else {
            self.__queue.push(() => {
                self.emit('message', msgContent, peer.id);
            });
        }
    }
}

/**
 * Send ping
 *
 * @private
 * @param {NetworDht} self
 * @param {Object} peer
 * @param {boolean} [pingNow=false]
 * @return {void}
 */
function _ping(self, peer, pingNow = false) {
    if (self.isDestroyed()) {
        return;
    }

    // is offline ?
    let diff = Date.now() - peer.responseTime;
    if (peer.isOnline && diff > PEER_OFFLINE_TIME) {
        peer.isOnline = false;
        if (self.isReady()) {
            self.emit('offline', peer.id);
        } else {
            self.__queue.push(() => {
                self.emit('offline', peer.id);
            });
        }
    }

    // need ping?
    diff = Date.now() - peer.sendTime;
    if (!pingNow && diff < KEEP_ALIVE_TIME) {
        return; // not
    }
    peer.sendTime = Date.now();

    // ping address list
    let candidates = [];
    if (peer) {
        if (peer.port) {
            candidates.push(peer);
        } else {
            candidates = peer.candidates;
        }
    }

    // start ping
    candidates.forEach((peerAddress) => {
        debug('[PING]', peerAddress.address + ':' + peerAddress.port);
        self.__socket.send(
            packet.encode(Buffer.alloc(0)),
            peerAddress.port,
            peerAddress.address || peerAddress.host
        );
    });
}

/**
 * Find local address candidate for peer
 *
 * @private
 * @param {NetworDht} self
 * @param {Object} peer
 * @param {Object} target
 * @return {void}
 */
function _onFindLocalCandiates(self, peer, target) {
    if (self.isDestroyed() ||
        peer._foundCandidates ||
        utils.equalsAddress(self.__dht.remoteAddress, peer)) {
        return;
    }

    let key = utils.ipCompact(peer);
    if (!key) return;

    self.__dht.getSharedData(key, target, function(err, resp) {
        if (err) {
            // try again after keep alive time
            setTimeout(
                _onFindLocalCandiates.bind(null, self, peer, target),
                KEEP_ALIVE_TIME
            );
            return;
        }

        if (!Buffer.isBuffer(resp) || resp.length < 6) {
            return;
        }

        let candidate = utils.ipExtract(resp.slice(0, 6));
        if (candidate.address === '127.0.0.1') {
            return;
        }

        self.__peers.addCandidate(peer, candidate);

        debug('[FOUNDCANDIDATE]',
            candidate.address + ':' + candidate.port,
            ' of ',
            peer.address + ':' + peer.port
        );

        peer._foundCandidates = true;
    });
}

/**
 * When peer is announced, store local ip's candidate
 *
 * @private
 * @param {NetworDht} self
 * @param {Object} target
 * @return {void}
 */
function _onAnnounceStoreLocalCandidates(self, target) {
    if (self.isDestroyed() ||
        !self.__dht.remoteAddress ||
        !self.__dht.remoteAddress.address) {
        return;
    }

    let key = utils.ipCompact(self.__dht.remoteAddress);
    let localAddress = utils.ipCompact(self.__dht.localAddress);

    self.__dht.putSharedData(key, localAddress, target, (err) => {
        debug('[STORE]', err ? err.message : null);
    });
}

/**
 * KeepAlive
 *
 * @private
 * @param {NetworkDht} self
 * @return {void}
 */
function _keepAlive(self) {
    if (self.isDestroyed()) {
        return;
    }

    // Louch this function again after 20 seconds
    clearTimeout(self.__keepAliveTm);
    self.__keepAliveTm = setTimeout(() => {
        _keepAlive(self);
    }, KEEP_ALIVE_TIME);

    if (self.__peers.length === 0) return;

    self.__peers.forEach((peer) => {
        if (peer.isMe) return;
        _ping(self, peer);
    });
}
_keepAlive.stop = function(self) {
    clearTimeout(self.__keepAliveTm);
};

/**
 * Update list of nodes and announce peer
 *
 * @private
 * @param {NetworkDht} self
 * @param {Function} callback
 * @return {void}
 */
function _lookup(self, callback) {
    if (self.isDestroyed()) {
        return;
    }

    // Louch this function again after 20 seconds
    clearTimeout(self.__lookupTm);
    self.__lookupTm = setTimeout(() => {
        _lookup(self);
    }, LOOKUP_TIME);

    let annouce = Date.now() - self.__announceTime > ANNOUNCE_TIME;
    self.__dht.lookup((err) => {
        debug('[lookup]', annouce);
        if (callback) callback(err);
    }, annouce);
}
_lookup.stop = function(self) {
    clearTimeout(self.__lookupTm);
};

// -- exports
module.exports = NetworkDht;

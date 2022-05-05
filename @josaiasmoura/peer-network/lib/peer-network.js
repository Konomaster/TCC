/**
 * @author Josaias Moura
 */

'use strict';

const EventEmitter = require('events');
const DhtProtocol = require('./network/dht');
const NetworkDht = require('./network/network-dht');
const CallbackQueue = require('./callback-queue');

class PeerNetwork extends EventEmitter {
    /**
     * Peer-to-peer Network
     *
     * @constructor
     * @fires PeerNetwork#close
     * @fires PeerNetwork#warning
     * @fires PeerNetwork#peer
     * @fires PeerNetwork#ready
     * @fires PeerNetwork#message
     * @param {object} opts
     * @param {string} opts.group Name of P2P group
     * @param {string} opts.password Strong password to encrypt all P2P data
     * @param {Buffer} [opts.id] An unique indentification of peer (default value is random generated)
     * @param {integer} [opts.concurrency] (default value is 16)
     * @param {dgram.Socket} [opts.udpSocket]
     * @param {Array.<string>} [opts.bootstrap] Bootstrap Bitorrent DHT server (default value: router.bittorrent.com:6881, router.utorrent.com:6881, dht.transmissionbt.com:6881)
     * @param {Function} [callback] When network is alive
     */
    constructor(opts) {
        super();

        this.__dht = new DhtProtocol(opts);
        this.__network = new NetworkDht(this.__dht);
        this.__queue = new CallbackQueue(1000);

        this.__network.on('message', (msg, from) => {
            if (!this.__network.isReady()) {
                return this.__queue.push(() => {
                    this.emit('message', msg, from);
                });
            }
            this.emit('message', msg, from);
        });

        this.__network.on('destroy', () => {
            this.emit('close');
        });

        this.__network.on('online', (peer) => {
            this.emit('online', peer);
            this.emit('peer', peer);
        });

        this.__network.on('offline', (peer) => {
            this.emit('offline', peer);
        });

        Object.defineProperty(this, 'id', {
            enumerable: true,
            get: () => { return this.__network.myID(); }
        });
    }

    /**
     * Get list of peers online
     *
     * @param {integer} [port=21201] Port used on UDP Socket
     * @param {Function} [callback]
     * @return {Array}
     */
    start(port, callback) {
        if (this.__network.isReady()) {
            this.emit('warning', 'Network started');
            return this;
        }
        this.__network.once('alive', () => {
            if (typeof callback === 'function') {
                this.once('ready', callback);
            }
            this.emit('ready');
            this.__queue.flush().forEach((err) => {
                this.emit('warning', err.message);
            });
        });
        this.__dht.listen(port);
        return this;
    }

    /**
     * Get list of peers online
     *
     * @return {Array}
     */
    getPeers() {
        return this.__network.peersIDs();
    }

    /**
     * @return {boolean}
     */
    isReady() {
        return this.__network.isReady();
    }

    /**
     * Close p2p network
     *
     * @param {Function} [callback]
     * @return {void}
     */
    close(callback) {
        this.__network.destroy(callback);
        this.__queue.clear();
    }

    /**
     * Send a message to peer
     *
     * @param {Buffer} buf Message content
     * @param {string} peerId Address of peer
     * @param {Function} [callback]
     * @return {void}
     */
    send(buf, peerId, callback) {
        if (!this.__network.isReady()) {
            return this.__queue.push(() => {
                this.send(buf, peerId, callback);
            });
        }
        callback = callback || function() {};
        this.__network.send(buf, peerId, callback);
    }
}

// -- exports
module.exports = PeerNetwork;

/**
 * @author Josaias Moura
 */

'use strict';

const utils = require('../utils');

class Peers {
    /**
     * @param {Function} [idFunction] Function to generate id ID
     * @constructor
     */
    constructor(idFunction) {
        this.__peers = new Map();
        this.__local = new Map();
        this.__ids = new Map();
        this.__idFunc = idFunction || function(ip) { return ip; };

        Object.defineProperty(this, 'length', {
            enumerable: true,
            get: () => { return this.__peers.size; }
        });
    }

    /**
     * Foreach
     *
     * @param {Function} callback
     * @return {Array}
     */
    forEach(callback) {
        return this.__peers.forEach(callback);
    }

    /**
     * Get list of peers online
     *
     * @return {Array}
     */
    onlines() {
        return Array.from(this.__peers.values()).filter((obj) => {
            return obj.isOnline;
        });
    }

    /**
     * Get list of peers online
     *
     * @return {void}
     */
    clear() {
        this.__peers.clear();
        this.__local.clear();
        this.__ids.clear();
    }

    /**
     * Add a peer to list
     *
     * @param {(Object|string)} peer
     * @param {Object} peerObj
     * @return {void}
     */
    add(peer) {
        peer = __peerToString(peer);
        if (!peer) {
            return;
        }
        if (this.has(peer)) {
            return this.get(peer);
        }

        let peerObj = Object.create(null, {
            address: {
                enumerable: true, get: __address
            },
            port: {
                enumerable: true, get: __port
            }
        });

        peerObj.isOnline = false;
        peerObj.id = this.__idFunc(peer);
        peerObj.candidates = [ utils.ipExtract(peer) ];
        peerObj._activeCandidate = null;
        // peerObj.addr = peer;

        this.__peers.set(peer, peerObj);
        this.__ids.set(peerObj.id, peer);

        return peerObj;
    }

    /**
     * Get peer by IP
     *
     * @param {(Object|string)} peer
     * @param {Object} candidate
     * @return {boolean}
     */
    addCandidate(peer, candidate) {
        peer = __peerToString(peer);

        let found = this.__peers.get(peer);
        if (!found) return false;

        if (this.__peers.get(candidate)) return false;

        if (typeof candidate !== 'object') {
            candidate = utils.ipExtract(candidate);
        }

        if (!utils.isPrivateIP(candidate.address) &&
            candidate.address !== '127.0.0.1') {
            return false;
        }

        found.candidates.push(candidate);

        this.__local.set(
            candidate.address + ':' + candidate.port,
            peer
        );

        return true;
    }

    /**
     * Active peer candidate
     *
     * @param {(Object|string)} peer
     * @param {Object} peerObj
     * @return {Object}
     */
    online(peer) {
        let found = this.get(peer);
        if (found) {
            found.isOnline = true;
            found._activeCandidate = utils.ipExtract(peer);
        }
    }

    /**
     * Active peer candidate
     *
     * @param {(Object|string)} peer
     * @param {Object} peerObj
     * @return {Object}
     */
    offline(peer) {
        let found = this.get(peer);
        if (found) {
            found.isOnline = false;
            found._activeCandidate = null;
        }
    }

    /**
     * Get peer by IP
     *
     * @param {(Object|string)} peer
     * @param {Object} peerObj
     * @return {Object}
     */
    get(peer) {
        peer = __peerToString(peer);

        let found = this.__peers.get(peer);
        if (found) return found;

        // verify if peer has a local address
        found = this.__peers.get(this.__local.get(peer));
        return found;
    }

    /**
     * Get list of peers online
     *
     * @param {(Object|string)} peer
     * @return {boolean}
     */
    has(peer) {
        peer = __peerToString(peer);

        if (this.__peers.has(peer)) return true;

        // verify if peer has a local address
        if (this.__peers.get(this.__local.get(peer))) return true;

        return false;
    }

    /**
     * Get peer from list
     *
     * @param {Object} peerAddr
     * @return {Object}
     */
    getById(peerAddr) {
        let id = this.__ids.get(peerAddr);
        return this.__peers.get(id);
    }
}

/**
 * Getter .address
 *
 * @private
 * @return {string}
 */
function __address() {
    if (this._activeCandidate) {
        return this._activeCandidate.address || this._activeCandidate.host;
    }
    return null;
}

/**
 * Getter .port
 *
 * @private
 * @return {integer}
 */
function __port() {
    if (this._activeCandidate) {
        return this._activeCandidate.port;
    }
    return 0;
}

/**
 * Object address to string
 *
 * @private
 * @param {Object} peer
 * @return {integer}
 */
function __peerToString(peer) {
    if (peer && typeof peer === 'object') {
        peer = peer.address + ':' + peer.port;
    }
    if (typeof peer !== 'string') {
        peer = '';
    }

    return peer;
}

// -- exports
module.exports = Peers;

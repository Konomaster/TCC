/**
 * @author Josaias Moura
 */

'use strict';

const EventEmitter = require('events');
const errors = require('../errors');

class NetworkBase extends EventEmitter {
    /**
     * @fires NetworkBase#alive
     * @fires NetworkBase#destroy
     * @fires NetworkBase#message
     * @fires NetworkBase#online
     * @fires NetworkBase#offline
     * @constructor
     */
    constructor() {
        super();
        this.__destroyed = false;
        this.__ready = false;
    }

    /**
     * Verify if network is ready
     *
     * @return {boolean}
     */
    isReady() {
        return this.__ready;
    }

    /**
     * Verify if network is destroyed
     *
     * @return {boolean}
     */
    isDestroyed() {
        return this.__destroyed;
    }

    /**
     * Set when network is ready
     *
     * @param {boolean} value
     * @return {void}
     */
    setReady(value) {
        this.__ready = !!value;
        if (this.isAlive()) {
            this.emit('alive');
        }
    }

    /**
     * Verify if network is alive
     *
     * @return {boolean}
     */
    isAlive() {
        return !this.__destroyed && this.__ready;
    }

    /**
     * @return {string}
     */
    myID() {
        throw errors.ERR_NOT_IMPLEMENTED_YET('myID');
    }

    /**
     * @return {Array.<string>}
     */
    peersIDs() {
        throw errors.ERR_NOT_IMPLEMENTED_YET('peersIDs');
    }

    /**
     * @param {Buffer} buf
     * @param {string} peerId
     * @param {Function} callback
     * @return {void}
     */
    send(buf, peerId, callback) {
        throw errors.ERR_NOT_IMPLEMENTED_YET('send');
    }

    /**
     * Destroy network
     *
     * @param {Function} [callback]
     * @return {void}
     */
    destroy(callback) {
        this.__ready = true;
        this.__destroyed = true;
        if (typeof callback === 'function') {
            this.once('destroy', callback);
        }
        this.emit('destroy');
    }
}

// -- exports
module.exports = NetworkBase;

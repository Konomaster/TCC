/**
 * @author Josaias Moura
 */

'use strict';

class CallbackQueue {
    /**
     * @param {integer} [max]
     * @constructor
     */
    constructor(max) {
        this._max = max || 1e6;
        this._queue = [];

        Object.defineProperty(this, 'length', {
            enumerable: true,
            get: () => { return this._queue.length; }
        });
    }

    /**
     * Foreach
     *
     * @param {Function} callback
     * @return {Array}
     */
    push(callback) {
        if (typeof callback === 'function') {
            this._queue.push(callback);
        }
        return this;
    }

    /**
     * Get list of peers online
     *
     * @return {Array}
     */
    flush() {
        let max = this._max;
        let errors = [];
        while (this._queue.length > 0 && max-- > 0) {
            try {
                (this._queue.shift())();
            } catch (e) {
                errors.push(e);
            }
        }
        this._queue = [];
        return errors;
    }

    /**
     * Get list of peers online
     *
     * @return {void}
     */
    clear() {
        while (this._queue.length > 0) {
            this._queue.shift();
        }
        this._queue = [];
    }
}

// -- exports
module.exports = CallbackQueue;

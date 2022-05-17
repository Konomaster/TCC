/**
 * @author Josaias Moura
 */

'use strict';

const Dht = require('./dht');
const NetworkDht = require('./network-dht');

module.exports = {
    /**
     * Create a NetworkDht object
     *
     * @param {object} opts
     * @param {string} opts.group Name of P2P group
     * @param {string} opts.password Strong password to encrypt all P2P data
     * @param {string} [opts.port=21201] Port used on UDP socket
     * @param {Function} [callback]
     * @return {NetworkDht}
     */
    createNetworkDht(opts, callback) {
        let dht = new Dht(opts);
        let network = new NetworkDht(dht);
        network.once('alive', callback);
        dht.listen(opts.port);
        return network;
    }
};

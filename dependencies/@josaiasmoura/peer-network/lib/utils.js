/**
 * @author Josaias Moura
 */

'use strict';

const crypto = require('crypto');
const ed = require('ed25519-supercop');
const natUpnp = require('nat-upnp');
const Netmask = require('netmask').Netmask;

const private10 = new Netmask('10.0.0.0/8');
const private172 = new Netmask('172.16.0.0/12');
const private192 = new Netmask('192.168.0.0/16');

const utils = exports = module.exports = {
    KRPC_ID_LENGTH: 20
};

/**
 * Verify if IP is inside private ip range
 *
 * @param {string} ipAddr
 * @return {boolean}
 */
utils.isPrivateIP = function(ipAddr) {
    if (private10.contains(ipAddr)) {
        return true;
    }
    if (private192.contains(ipAddr)) {
        return true;
    }
    if (private172.contains(ipAddr)) {
        return true;
    }
    return false;
};

/**
 * Verify if 2 addresses is equals;
 *
 * @param {(Object|string|Buffer)} addr1
 * @param {(Object|string|Buffer)} addr2
 * @return {boolean}
 */
utils.equalsAddress = function(addr1, addr2) {
    if (typeof addr1 !== 'object') {
        addr1 = utils.ipExtract(addr1);
    }
    if (typeof addr2 !== 'object') {
        addr2 = utils.ipExtract(addr2);
    }
    if (addr1 && addr2 && addr1.address === addr2.address &&
        addr1.port === addr2.port) {
        return true;
    }
    return false;
};

/**
 * Encrypt a buffer content with cipher
 *
 * @param {Buffer} key
 * @param {Buffer} data
 * @return {Buffer}
 */
utils.bufferEncrypt = function(key, data) {
    let cipher = crypto.createCipher('aes128', key);
    let encrypted = cipher.update(data);
    let final = cipher.final();
    return Buffer.concat([encrypted, final]);
};

/**
 * Decrypt a buffer content with decipher
 *
 * @param {Buffer} key
 * @param {Buffer} data
 * @return {(Buffer|null)}
 */
utils.bufferDecrypt = function(key, data) {
    let decipher = crypto.createDecipher('aes128', key);
    let decrypted, final;
    try {
        decrypted = decipher.update(data);
        final = decipher.final();
    } catch (e) {
        return null;
    }
    return Buffer.concat([decrypted, final]);
};

/**
 * Convert buffer or string IP:port
 *
 * @param {Buffer} nodes
 * @param {integer} [maxNodes=1e6]
 * @return {(Array.<Object>|null)}
 */
utils.extractNodes = function(nodes, maxNodes) {
    maxNodes = maxNodes || 1e6;
    if (!Buffer.isBuffer(nodes) || maxNodes < nodes.length) {
        return null;
    }

    let arrNodes = [];
    for (let i = 0; i < nodes.length; i += (utils.KRPC_ID_LENGTH + 6)) {
        let ipPort = nodes.slice(i + utils.KRPC_ID_LENGTH, i + utils.KRPC_ID_LENGTH + 6);
        let node = utils.ipExtract(ipPort);
        if (!node || !node.port) {
            continue;
        }

        arrNodes.push({
            id: nodes.slice(i, i + utils.KRPC_ID_LENGTH),
            address: node.address,
            port: node.port
        });
    }

    arrNodes.reverse();
    return arrNodes;
};

/**
 * Convert buffer or string IP:port
 *
 * @param {(string|Buffer)} ipPort
 * @return {(Object|null)}
 */
utils.ipExtract = function(ipPort) {
    let ip = {
        address: null,
        port: 0
    };
    if (ipPort && typeof ipPort === 'object' && ipPort.address && ipPort.port) {
        return ipPort;
    } else if (Buffer.isBuffer(ipPort)) {
        if (ipPort.length >= 6) {
            ip.port = ipPort.readUInt16BE(4);
        }
        if (ip.port > 0 && ip.port <= 65535) {
            ip.address = ipPort[0] + '.' + ipPort[1] + '.' + ipPort[2] + '.' + ipPort[3];
        }
    } else if (typeof ipPort === 'string') {
        ipPort = ipPort.split(':');
        ip.address = ipPort[0].trim();
        ip.port = parseInt(ipPort[1]);
    }
    if (ip.address) {
        return ip;
    }
    return null;
};

/**
 * Convert IP to Buffer
 *
 * @param {Object} peerAddress
 * @return {Buffer}
 */
utils.ipCompact = function(peerAddress) {
    let buf = Buffer.alloc(6);
    if (typeof peerAddress === 'string') {
        let cache = peerAddress.split(':');
        peerAddress = {
            address: cache[0], port: parseInt(cache[1])
        };
    }
    if (typeof peerAddress === 'object' && peerAddress !== null &&
        (peerAddress.address || peerAddress.host)) {
        let ipHex = peerAddress.address
            ? peerAddress.address.split('.')
            : peerAddress.host.split('.');

        buf.writeUInt8(parseInt(ipHex[0]), 0);
        buf.writeUInt8(parseInt(ipHex[1]), 1);
        buf.writeUInt8(parseInt(ipHex[2]), 2);
        buf.writeUInt8(parseInt(ipHex[3]), 3);
        buf.writeUInt16BE(peerAddress.port, 4);
    }
    return buf;
};

/**
 * Use a Bittorrent DHT node response to discover remote IP
 *
 * @param {Object} response
 * @return {(Object|null)}
 */
utils.findRemoteIp = function(response) {
    let remote;

    if (!response) return remote;

    if (response.ip) {
        remote = utils.ipExtract(response.ip);
    } else if (response.r && response.r.ip) {
        remote = utils.ipExtract(response.r.ip);
    }

    if (remote == null ||
        remote.address == null ||
        remote.port <= 0 || remote.port > 65535) {
        return null; // When node don't echo Ip:Port
    }

    return remote;
};

/**
 * Generate ed25519 key pair to sign/verify message
 *
 * @param {Buffer} masterKey1 SHA-1 hash
 * @param {Buffer} masterKey2 SHA-1 hash
 * @return {(Object|null)}
 */
utils.generateSign = function(masterKey1, masterKey2) {
    if (!Buffer.isBuffer(masterKey1) || !Buffer.isBuffer(masterKey2) ||
        masterKey1.length !== 20 || masterKey2.length !== 20) {
        return null;
    }
    let seed = Buffer.concat([masterKey1, masterKey2]).slice(0, 32);
    let keypair = ed.createKeyPair(seed);
    return {
        publicKey: keypair.publicKey,
        sign: (buf) => {
            return ed.sign(buf, keypair.publicKey, keypair.secretKey);
        },
        verify: (signature, message) => {
            return ed.verify(signature, message, keypair.publicKey);
        }
    };
};

/**
 * Generate sha1 hash
 *
 * @param {(string|Buffer)} content
 * @return {Buffer}
 */
utils.sha1 = function(content) {
    let hash = crypto.createHash('sha1');

    if (typeof content === 'string') {
        hash.update(content, 'ascii');
    }
    if (Buffer.isBuffer(content)) {
        hash.update(content);
    }

    return Buffer.from(hash.digest('hex'), 'hex');
};

/**
 * Open UPnP port (One solution for Symmetric NAT connection block)
 *
 * @param {integer} port
 * @param {Function} callback
 * @return {void}
 */
utils.openUPnPPort = function(port, callback) {
    let doneCount = 0;
    let externalIp;
    let upnpClient = natUpnp.createClient();
    let done = (err, ip) => {
        doneCount++;
        externalIp = ip || externalIp;
        if (typeof callback === 'function' && doneCount >= 2) {
            upnpClient.close();
            callback(err, externalIp);
        }
    };
    upnpClient.portMapping({
        public: port,
        private: port,
        ttl: 0,
        protocol: 'UDP',
        description: 'UPnP Peer'
    }, done);
    upnpClient.externalIp(done);
};

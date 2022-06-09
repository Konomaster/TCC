/**
 * @author Josaias Moura
 */

'use strict';

const errors = require('../errors');

/**
                    HEADER

     0      7 8     15 16    23 24    31
    +--------+--------+--------+--------+
    |   Magic Number  |    Checksum     |
    +--------+--------+--------+--------+

           (big-endian byte order)

*/

const PACKET_MAGIC_NUMBER = 0x504b;
const HEADER_LEN = 4;

function encodePacket(data) {
    if (!Buffer.isBuffer(data)) {
        throw errors.ERR_INVALID_ARG('data need be a Buffer');
    }

    let packet = Buffer.concat([
        Buffer.alloc(HEADER_LEN),
        data
    ]);

    packet.writeUInt16BE(PACKET_MAGIC_NUMBER, 0);

    let sum = checksum(packet);
    packet.writeUInt16BE(sum, 2);

    return packet;
}

function decodePacket(packet) {
    if (!Buffer.isBuffer(packet)) {
        throw errors.ERR_INVALID_ARG('packet need be a Buffer');
    }
    if (packet.length < HEADER_LEN) {
        throw errors.ERR_INVALID_ARG('packet wrong size');
    }

    let magicNumber = packet.readUInt16BE(0);
    if (magicNumber !== PACKET_MAGIC_NUMBER) {
        throw errors.ERR_FATAL('invalid packet');
    }

    let sum = checksum(packet);
    if (sum !== 0) {
        throw errors.ERR_FATAL('checksum failed');
    }

    let content = packet.slice(HEADER_LEN); // discard header

    return content;
}

function checksum(buf) {
    if (buf.length % 2 === 1) {
        buf = Buffer.concat([buf, Buffer.alloc(1)]);
    }

    let sum = 0xffff;
    let len = buf.length;

    for (var i = 0; i < len; i += 2) {
        sum += buf.readInt16BE(i);
    }

    return 0xffff & ~sum;
}

module.exports = {
    encode: encodePacket,
    decode: decodePacket
};

const test = require('tape');

/**
                    HEADER

     0      7 8     15 16    23 24    31
    +--------+--------+--------+--------+
    |   Magic Number  |    Checksum     |
    +--------+--------+--------+--------+

           (big-endian byte order)

*/
test('Network - Packet', function(t) {
    t.plan(7);

    const Packet = require('../lib/network/packet');
    const message = Buffer.from('HELLO');
    const helloPacket = Buffer.from(
        '504b' + 'cc24' +
        '48454c4c4f'
        , 'hex');

    t.throws(function() {
        Packet.encode(100);
    }, TypeError, 'Catch invalid data');

    t.throws(function() {
        Packet.decode(100);
    }, TypeError, 'Catch invalid packet');

    t.throws(function() {
        Packet.decode(Buffer.alloc(2));
    }, TypeError, 'Catch wrong size');

    t.throws(function() {
        Packet.decode(Buffer.alloc(5));
    }, Error, 'Catch invalid magic number');

    t.throws(function() {
        Packet.decode(Buffer.concat([
            Buffer.from('504b' + '0f0f', 'hex'), Buffer.alloc(16)
        ]));
    }, Error, 'Catch checksum failed');

    let bytes = Packet.encode(message);
    t.assert(Buffer.compare(bytes, helloPacket) === 0, 'Encode packet');

    let decoded = Packet.decode(helloPacket);
    t.assert(Buffer.compare(decoded, message) === 0, 'Decode packet');
});

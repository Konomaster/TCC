const test = require('tape');

/**
                              CONTENT

     0                               127                 length-1
    +-----------------------------------+------------------------+
    |     Initialization vector (IV)    |   crypted content ...  |
    +-----------------------------------+------------------------+

                     (big-endian byte order)

*/
test('AES - encrypt/decrypt', function(t) {
    const AES = require('../lib/network/security/aes');

    const message = Buffer.from('HELLO');
    const key = Buffer.alloc(16).fill('a');

    let aes = new AES(key);

    let crypted = aes.encrypt(message);
    t.assert(!!crypted, 'Encrypt');

    let decrypted = aes.decrypt(crypted);
    t.deepEqual(message, decrypted, 'Decrypt');

    t.end();
});

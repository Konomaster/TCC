/**
 * @author Josaias Moura
 */

'use strict';

const crypto = require('crypto');

/**
                              CONTENT

     0                               127                 length-1
    +-----------------------------------+------------------------+
    |     Initialization vector (IV)    |   crypted content ...  |
    +-----------------------------------+------------------------+

                     (big-endian byte order)

*/

class AES {
    /**
     * Encrypt and Decrypt buffers
     *
     * @constructor
     * @param {(Buffer|string)} key
     */
    constructor(key) {
        this._key = Buffer.from(key) || crypto.randomBytes(16);

        if (this._key.length > 16) {
            this._key = this._key.slice(0, 16);
        }

        this._algorithm = 'aes128';
    }

    /**
     * @param {Buffer} content
     * @return {object}
     */
    encrypt(content) {
        let iv = crypto.randomBytes(16);
        let cipher = crypto.createCipheriv(
            this._algorithm,
            this._key,
            iv
        );

        let encrypted = cipher.update(content);
        encrypted = Buffer.concat([iv, encrypted, cipher.final()]);

        return encrypted;
    }

    /**
     * @param {Buffer} content
     * @return {Buffer}
     */
    decrypt(content) {
        if (!Buffer.isBuffer(content) && content.length < 16) {
            return Buffer.alloc(0);
        }

        let iv = content.slice(0, 16);
        content = content.slice(16);
        let decipher = crypto.createDecipheriv(
            this._algorithm,
            this._key,
            iv
        );

        let decrypted = decipher.update(content);
        decrypted = Buffer.concat([decrypted, decipher.final()]);

        return decrypted;
    }
}

// -- exports
module.exports = AES;

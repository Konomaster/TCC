/**
 * @author Josaias Moura
 */

'use strict';

module.exports = {
    ERR_FATAL: _errCreate('ERR_FATAL', Error),
    ERR_NOT_IMPLEMENTED_YET: _errCreate('ERR_NOT_IMPLEMENTED_YET', Error),
    EINVAL: _errCreate('EINVAL', Error),
    EADDRINUSE: _errCreate('EADDRINUSE', Error),
    ERR_SOCKET_ALREADY_BOUND: _errCreate('ERR_SOCKET_ALREADY_BOUND', Error),
    ERR_SOCKET_DGRAM_NOT_RUNNING: _errCreate('ERR_SOCKET_DGRAM_NOT_RUNNING', Error),
    ENOTFOUND: _errCreate('ENOTFOUND', Error),
    ETIMEDOUT: _errCreate('ETIMEDOUT', Error),
    ECONNREFUSED: _errCreate('ETIMEDOUT', Error),
    ERR_INVALID_ARG: _errCreate('ERR_INVALID_ARG', TypeError),
    ERR_SOCKET_BAD_PORT: _errCreate('ERR_SOCKET_BAD_PORT', Error),
    ERR_SOCKET_BAD_TYPE: _errCreate('ERR_SOCKET_BAD_TYPE', Error)
};

function _errCreate(code, Error) {
    return function(message) {
        let err = new Error('[' + code + ']: ' + message);
        Object.defineProperty(err, 'code', {
            value: Object.freeze(code)
        });
        return err;
    };
}

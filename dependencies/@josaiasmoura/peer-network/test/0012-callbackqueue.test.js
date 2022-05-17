const test = require('tape');

test('CallbackQueue', function(t) {
    const CallbackQueue = require('../lib/callback-queue');

    t.plan(6);
    let queue = new CallbackQueue();

    queue.push(() => {
        t.pass('Run callback 1');
    }).push(() => {
        t.pass('Run callback 2');
    }).push(() => {
        throw new Error('error on callback');
    }).push(() => {
        t.pass('Run callback 3');
    });

    t.assert(queue.length > 0, 'push');

    let capturedErrors = queue.flush();

    t.assert(capturedErrors.length > 0, 'Capture errors');
    t.assert(queue.length === 0, 'flush');
});

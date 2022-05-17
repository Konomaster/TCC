const test = require('tape');
const createEnv = require('./net/dht-bootstrap');
const DhtProtocol = require('../lib/network/dht');

let dhtEnv;
test('> Create env', function(t) {
    dhtEnv = createEnv(() => t.end(), 1);
});

test('DhtProtocol', function(t) {
    t.plan(8);
    let dht = new DhtProtocol({
        group: 'TEST',
        password: 'test',
        bootstrap: dhtEnv.bootstrap
    });
    let valueToStore = Buffer.from('HELLO!');
    // log(dht);

    dht.once('peer', () => t.pass('peer found'));

    dht.once('announce', (node) => {
        t.pass('peer announced');
        dht.lookup(err => t.assert(!err, 'lookup after announce'), true);

        let afterGetStored = (err, value) => {
            t.assert(!err && Buffer.compare(value, valueToStore) === 0,
                'get value stored'
            );
            dht.destroy(err => t.assert(!err, 'destroyed'));
        };
        let afterStore = (err) => {
            t.assert(!err, 'put value on node');
            dht.getSharedData('hello', node, afterGetStored);
        };
        dht.putSharedData('hello', valueToStore, node, afterStore);
    });

    dht.listen(function(err) {
        t.assert(!err, 'listening');
        dht.lookup(err => t.assert(!err, 'lookup before announce'), true);
    });
});

test('> Destroy env', function(t) {
    dhtEnv.destroy(() => t.end());
});

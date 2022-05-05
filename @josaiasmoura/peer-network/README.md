# Peer Network
> DISCLAIMER: This work is for study purposes only. It should not be used in production.

A module for direct P2P (peer-to-peer) communication using Bittorrent DHT nodes like a rendezvous server.

### Installation

    npm install @josaiasmoura/peer-network

### Usage

```js
const PeerNetwork = require("@josaiasmoura/peer-network");

let peer = new PeerNetwork({ group:"networkname", password:"networkpassword" });

peer.on("ready", () => {
    console.log("I'm online!");
}).on("message", (msg, from) => {
    console.log("You received a message! ", from, msg.toString());
}).on("peer", (newPeer) => {
    console.log("New peer online! ", newPeer);
    peer.send(Buffer.from("Hello!"), newPeer);
}).on("offline", (offPeer) => {
    console.log("Peer is now offline! ", offPeer);
}).on("warning", (err) => {
    console.log("Alert! " + err.message);
});

peer.start();
```

### API

### Contributing

1. Fork this project
2. Create your feature branch (`git checkout -b feature/fooBar`)
3. Commit your changes (`git commit -am 'Add some fooBar'`)
4. Push to the branch (`git push origin feature/fooBar`)
5. Create a new Pull Request

# License

The MIT License (MIT)

Copyright (c) 2018 Josaias Moura

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

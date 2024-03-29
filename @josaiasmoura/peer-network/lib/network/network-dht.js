/**
 * @author Josaias Moura
 */

 'use strict';

 const debug = require('debug')('NetworkDHT');
 const NetworkBase = require('./network-base');
 const CallbackQueue = require('../callback-queue');
 const errors = require('../errors');
 const utils = require('../utils');
 const Peers = require('./peers');
 const packet = require('./packet');
 const AES = require('./security/aes');
 //custom requires
 const udp = require('dgram');
 
 //const KEEP_ALIVE_TIME = 10000;
 const KEEP_ALIVE_TIME = 4000; //4 seconds
 const LOOKUP_TIME = 20000; //20 seconds
 //const PEER_OFFLINE_TIME = 20000 * 6; // 2min
 const PEER_OFFLINE_TIME = 20000 * 3; // 1min
 const ANNOUNCE_TIME = 20000 * 3; // 1min 
 //const ANNOUNCE_TIME = 20000 * 12; // 4min
 
 class NetworkDht extends NetworkBase {
     /**
      * @fires NetworkBase#alive
      * @fires NetworkBase#destroy
      * @fires NetworkBase#message
      * @fires NetworkBase#online
      * @fires NetworkBase#offline
      * @param {Object} dht
      * @constructor
      */
     constructor(dht,controlPort) {
         super();
         
         //(Custom)
         //flag to identify if hole punch socket info was sent to the python program
         this.__boundSent=false
         this.__notPing=[]
         
         this.__controlSocket=udp.createSocket('udp4')
         this.__controlSocket.bind(controlPort)
         
         this.__controlSocket.on('message', (msg, from) => {
             _controlMessage(this,msg)
         })
 
         
         this.__notifyQueue=new CallbackQueue(1e6)
 
         //(End Custom)
 
         if (!dht) {
             throw errors.ERR_FATAL('DhtProtocol is needed');
         }
 
         this.__idFunc = function(info) {
             if (typeof info === 'object') {
                 info = info.address + ':' + info.port;
             }
             return utils.sha1(info).slice(0, 8).toString('hex');
         };
         this.__peers = new Peers(this.__idFunc);
         this.__dht = dht;
         this.__socket = dht.udpSocket;
         this.__announceTime = 0;
         this.__queue = new CallbackQueue(1e5);
         this.__security = new AES(dht.secret);
 
         this.stats = {
             startTime: 0,
             bytesReceived: 0,
             bytesSended: 0
         };
 
         this.__socket.on('message', (msg, from) => {
             this.stats.bytesReceived += (from.size + 8 + 20);
             if (from.address.toString()==="177.70.93.208"){
             console.log("chegando msg de: "+from.address.toString()+" porta: "+from.port.toString());
             }
             _onUdpMessage(this, msg, from);
         });
 
         let addPeer = (peer) => {
             let peerObj = this.__peers.add(peer);
             if (peerObj) {
                 peerObj.responseTime = 0;
                 peerObj.sendTime = 0;
                 peerObj.isMe = utils.equalsAddress(peer, dht.remoteAddress);
             }
             return peerObj;
         };
 
         this.__dht.on('announce', (target) => {
             debug('[announce]', target);
             this.__announceTime = Date.now();
             _onAnnounceStoreLocalCandidates(this, target);
         });
 
         this.__dht.on('peer', (peer, from) => {
             if (!this.__peers.has(peer)) {
                 debug('[found potential peer]', peer);
                 let peerObj = addPeer(peer);
 
                 // dont ping itself
                 if (!peerObj.isMe) {
                     _ping(this, peerObj);
                     _ping(this, peerObj);
                 }
 
                 // find local addresses candidates
                 //(Custom) 
                 //_onFindLocalCandiates(this, peer, from);
                 //(End Custom)
             }
         });
 
         let onListen = () => {
             _keepAlive(this);
             _lookup(this, () => {
                 if (dht.remoteAddress.address) {
                     let myself = addPeer(dht.remoteAddress);
                     myself.isMe = true;
 
                     let selfCandidate = {
                         address: dht.localAddress.address,
                         port: dht.localAddress.port,
                     };
 
                     this.__peers.addCandidate(dht.remoteAddress, selfCandidate);
                     this.__peers.online(selfCandidate);
                 }
 
                 if (!this.stats.startTime) {
                     this.stats.startTime = Date.now();
                 }
 
                 this.setReady(true);
 
                 this.__queue.flush().forEach((err) => {
                     debug('[error]', err);
                 });
                 
 
                 _lookup(this); // lookup again, after announce
             });
         };
 
         if (this.__dht.listening) {
             onListen();
         } else {
             this.__dht.once('listening', onListen);
         }
 
         this.once('destroy', () => {
             _lookup.stop(this);
             _keepAlive.stop(this);
             this.__peers.clear();
             this.__queue.clear();
             this.__dht.destroy();
         });
        
         
     }
 
     /**
      * Get peer address
      *
      * @return {string}
      */
     myID() {
         if (this.__dht.remoteAddress && this.__dht.remoteAddress.address) {
             return this.__idFunc(
                 this.__dht.remoteAddress.address + ':' +
                 this.__dht.remoteAddress.port
             );
         }
         return '';
     }
 
     /**
      * @return {Array.<string>}
      */
     peersIDs() {
         return this.__peers.onlines().map((obj) => {
             return obj.id;
         });
     }
 
     /**
      * @param {Buffer} buf
      * @param {string} peerId
      * @param {Function} [callback]
      * @return {void}
      */
     send(buf, peerId, callback) {
         if (!this.isAlive()) {
             return callback(errors.ERR_FATAL('Network is not alive'));
         }
 
         callback = callback || function() {};
 
         let peer = this.__peers.getById(peerId);
         
 
         if (peer && peer.isOnline) {
             peer.sendTime = Date.now();
 
             buf = this.__security.encrypt(buf);
             let encoded = packet.encode(buf);
             this.__socket.send(encoded, peer.port, peer.address, callback);
         } else {
             callback(errors.ERR_FATAL('Peer is offline or not found'));
         }
     }
 }
 
 /**
  * Receive a UDP packet (any)
  *
  * @private
  * @param {NetworkDht} self
  * @param {Buffer} msg
  * @param {Object} from
  * @return {void}
  */
 function _onUdpMessage(self, msg, from) {
     if (!Buffer.isBuffer(msg) || msg.length < 2) return;
 
     // verify if 'from' is a trustly address
     let peer = self.__peers.get(from);
     if (!peer) {
         return; // discard packet
     }
      
     // verify if msg is a valid packet
     let msgContent;
     try {
         let decoded = packet.decode(msg);
         if (decoded.length > 0) {
             decoded = self.__security.decrypt(decoded);
         }
         msgContent = decoded;
     } catch (e) {
         return; // discard packet
     }
 
     // log response time
     peer.responseTime = Date.now();
     if (!peer.isOnline) {
         self.__peers.online(from);
         //talvez colocar esse if aqui
         //if(!self.__notPing.includes(peer.id))
         _ping(self, peer, true); // pong
 
         if (self.isReady()) {
             self.emit('online', peer.id);
         } else {
             self.__queue.push(() => {
                 self.emit('online', peer.id);
             });
         }
 
         //(Custom)
         //maybe put inside the ifs
         if(self.__dht.remoteAddress.address){
             _notifyNewPeer(self,peer)
         }
         else{
         self.__queue.push(()=>{_notifyNewPeer(self,peer)})
         }
         //(End Custom)
     }
 
     // packet is empty?
     if (msgContent.length === 0) {
         _ping(self, peer); // pong
         return;
     }
 
     // everithing is ok! reflect event
     if (msgContent.length > 0) {
         if (self.isReady()) {
             self.emit('message', msgContent, peer.id);
         } else {
             self.__queue.push(() => {
                 self.emit('message', msgContent, peer.id);
             });
         }
         //(Custom)
         _preTestConfirmation(self,msgContent.toString(),peer.id)
         //(End Custom)
     }
 }
 
 /**
  * Send ping
  *
  * @private
  * @param {NetworDht} self
  * @param {Object} peer
  * @param {boolean} [pingNow=false]
  * @return {void}
  */
 function _ping(self, peer, pingNow = false) {
     if (self.isDestroyed()) {
         return;
     }
 
     // is offline ?
     let diff = Date.now() - peer.responseTime;
     if (peer.isOnline && diff > PEER_OFFLINE_TIME) {
         peer.isOnline = false;
         if (self.isReady()) {
             self.emit('offline', peer.id);
         } else {
             self.__queue.push(() => {
                 self.emit('offline', peer.id);
             });
         }
         _notifyPeerDown(self,peer);
     }
 
     // need ping?
     diff = Date.now() - peer.sendTime;
     if (!pingNow && diff < KEEP_ALIVE_TIME) {
         return; // not
     }
     peer.sendTime = Date.now();
 
     // ping address list
     let candidates = [];
     if (peer) {
         if (peer.port) {
             candidates.push(peer);
         } else {
             candidates = peer.candidates;
         }
     }
 
     // start ping
     candidates.forEach((peerAddress) => {
         debug('[PING]', peerAddress.address + ':' + peerAddress.port);
         self.__socket.send(
             packet.encode(Buffer.alloc(0)),
             peerAddress.port,
             peerAddress.address || peerAddress.host
         );
     });
 }
 
 /**
  * Find local address candidate for peer
  *
  * @private
  * @param {NetworDht} self
  * @param {Object} peer
  * @param {Object} target
  * @return {void}
  */
 function _onFindLocalCandiates(self, peer, target) {
     if (self.isDestroyed() ||
         peer._foundCandidates ||
         utils.equalsAddress(self.__dht.remoteAddress, peer)) {
         return;
     }
 
     let key = utils.ipCompact(peer);
     if (!key) return;
 
     self.__dht.getSharedData(key, target, function(err, resp) {
         if (err) {
             // try again after keep alive time
             setTimeout(
                 _onFindLocalCandiates.bind(null, self, peer, target),
                 KEEP_ALIVE_TIME
             );
             return;
         }
 
         if (!Buffer.isBuffer(resp) || resp.length < 6) {
             return;
         }
 
         let candidate = utils.ipExtract(resp.slice(0, 6));
         if (candidate.address === '127.0.0.1') {
             return;
         }
 
         self.__peers.addCandidate(peer, candidate);
 
         debug('[FOUNDCANDIDATE]',
             candidate.address + ':' + candidate.port,
             ' of ',
             peer.address + ':' + peer.port
         );
 
         peer._foundCandidates = true;
     });
 }
 
 /**
  * When peer is announced, store local ip's candidate
  *
  * @private
  * @param {NetworDht} self
  * @param {Object} target
  * @return {void}
  */
 function _onAnnounceStoreLocalCandidates(self, target) {
     if (self.isDestroyed() ||
         !self.__dht.remoteAddress ||
         !self.__dht.remoteAddress.address) {
         return;
     }
 
     let key = utils.ipCompact(self.__dht.remoteAddress);
     let localAddress = utils.ipCompact(self.__dht.localAddress);
 
     self.__dht.putSharedData(key, localAddress, target, (err) => {
         debug('[STORE]', err ? err.message : null);
     });
 }
 
 /**
  * KeepAlive
  *
  * @private
  * @param {NetworkDht} self
  * @return {void}
  */
 function _keepAlive(self) {
     if (self.isDestroyed()) {
         return;
     }
 
     // Louch this function again after 20 seconds
     clearTimeout(self.__keepAliveTm);
     self.__keepAliveTm = setTimeout(() => {
         _keepAlive(self);
     }, KEEP_ALIVE_TIME);
 
     if (self.__peers.length === 0) return;
 
     self.__peers.forEach((peer) => {
         if (peer.isMe) return;
         //flagged peers wont be pinged
 
         else if (peer.candidates[0].address === self.__dht.remoteAddress.address || self.__notPing.includes(peer.id)){
             //console.log("Peer que nao vai ser pingado "+peer.id+" "+peer.address+" "+peer.port)
             return;
         }
         
         //console.log("keepAlive "+peer.id)
         _ping(self, peer);
     });
 }
 _keepAlive.stop = function(self) {
     clearTimeout(self.__keepAliveTm);
 };
 
 /**
  * Update list of nodes and announce peer
  *
  * @private
  * @param {NetworkDht} self
  * @param {Function} callback
  * @return {void}
  */
 function _lookup(self, callback) {
     if (self.isDestroyed()) {
         return;
     }
 
     // Louch this function again after 20 seconds
     clearTimeout(self.__lookupTm);
     self.__lookupTm = setTimeout(() => {
         _lookup(self);
     }, LOOKUP_TIME);
 
     let annouce = Date.now() - self.__announceTime > ANNOUNCE_TIME;
     self.__dht.lookup((err) => {
         //(Custom)
         _sendHolePort(self)
         //(End Custom)
         debug('[lookup]', annouce);
         if (callback) callback(err);
     }, annouce);
 
 }
 _lookup.stop = function(self) {
     clearTimeout(self.__lookupTm);
 };
 
 /**
  * (Custom Method) Send peer info to python program when
  * new peer online
  * 
  * @private
  * @param {NetworDht} self
  * @param {Object} peer
  * @param {boolean} [pingNow=false]
  * @return {void}
  */
 
 function _notifyNewPeer(self,peer){
     if (peer.isMe || self.__dht.remoteAddress.address===null){
     //console.log("nao me envio para o python nem com hairpin");
     return;
     }
 
     let socket = udp.createSocket('udp4')
 
     let dadosPeer="add,"+peer.address+","+peer.port+","+peer.id+","+self.__socket.address().port
     let dadosBinario=Buffer.from(dadosPeer)
     //let reconvert=teste.toString('utf-8')
     socket.send(dadosBinario,37710,'0.0.0.0',function(error){
         if(error){
             socket.close()
         }
     })
     
     _sendHolePort(self)
 }
 
 /**
  * (Custom Method) Send peer info to python program
  * when peer becomes offline
  * 
  * @private
  * @param {NetworDht} self
  * @param {Object} peer
  * @param {boolean} [pingNow=false]
  * @return {void}
  */
 
 function _sendHolePort(self){
     if(self.__dht.remoteAddress.address!=null && self.__dht.remoteAddress.port != 0){
         let socketData=self.__socket.address()
         let holeport=socketData.port
         let holeaddress=socketData.address
         
         let holeString="holeport,"+holeport+","+holeaddress+","+Number(self.__dht.remoteAddress.port)+","+self.__dht.remoteAddress.address
         
         _responseMessage(self,holeString)
     }
 }
 
 
 /**
  * (Custom Method) Send peer info to python program
  * when peer becomes offline
  * 
  * @private
  * @param {NetworDht} self
  * @param {Object} peer
  * @param {boolean} [pingNow=false]
  * @return {void}
  */
 
 function _notifyPeerDown(self,peer){
     let socket = udp.createSocket('udp4')
 
     let dadosPeer="remove,"+peer.address+","+peer.port+","+peer.id+","+self.__socket.address().port
     let dadosBinario=Buffer.from(dadosPeer)
     //let reconvert=teste.toString('utf-8')
     socket.send(dadosBinario,37710,'0.0.0.0',function(error){
         if(error){
             socket.close()
         }
 
     })
 } 
 
 /**
  * (Custom Method) get message from python program to stop pinging a peer or to resume pinging it
  * when peer becomes offline
  * 
  * @private
  * @param {NetworDht} self
  * @param {Object} peer
  * @param {boolean} [pingNow=false]
  * @return {void}
  */
 
 
 function _controlMessage(self,message){
     let decodedMessage=message.toString('utf-8')
     let splitMessage=decodedMessage.split(',')
     if (splitMessage[0]==="notPing" && !self.__notPing.includes(splitMessage[1]))
     {
         self.__notPing.push(splitMessage[1])
         console.log("executou not ping")
         _responseMessage(self,"confirmNotPing")
         
     }
     else if(splitMessage[0]==="doPing" && self.__notPing.includes(splitMessage[1])){
         
         self.__notPing.splice(self.__notPing.indexOf(splitMessage[1]),1)
         console.log("tirou o not ping")
         _responseMessage(self,"removeNotPing")
     }
     
     else if(splitMessage[0]==="serverReady"){
         //console.log("enviandoServerReady")
         self.send(Buffer.from("serverReady,"+splitMessage[2]+","+splitMessage[3]),splitMessage[1])
     }
     else if(splitMessage[0]==="gonnaTest"){
         //console.log("enviandoGonnaTest")
         //passar calback pro send pra fechar socket
         self.send(Buffer.from("gonnaTest,"+splitMessage[2]+","+splitMessage[3]),splitMessage[1],()=>{
             //self.__socket.close()
             //self.destroy()
             self.emit('startTest')
         })
     }
     else if (splitMessage[0]==="destroy"){
         console.log("destruindo dht")
         self.destroy()
         self.emit('startTest')
     }
     else if(splitMessage[0]==="vazao"){
         _sendIfReady(self,"vazao,"+splitMessage[2],splitMessage[1])
     }
     else if(splitMessage[0]==="endTest"){
         if (splitMessage.length == 3){
             _sendIfReady(self,"endTest,"+splitMessage[2],splitMessage[1])
         }
         else{
            _sendIfReady(self,"endTest",splitMessage[1])
         }
     }
     else if(splitMessage[0]==="endTest_ack"){
        _sendIfReady(self,"endTest_ack",splitMessage[splitMessage.length-1])
     }
     else if (splitMessage[0]==="offer"){
         _sendIfReady(self,"offer",splitMessage[1])
     }
     else if (splitMessage[0]==="offer_rjct"){
        _sendIfReady(self,"offer_rjct",splitMessage[1])
     }
     else if (splitMessage[0]==="offer_res"){
        _sendIfReady(self,"offer_res",splitMessage[1])
     }
     else if (splitMessage[0]==="offer_abort"){
        _sendIfReady(self,"offer_abort",splitMessage[1])
     }
     else if (splitMessage[0]==="offer_abort_ack"){
        _sendIfReady(self,"offer_abort_ack",splitMessage[1])
     }
     //talvez implementar isso
     /*
     else if(splitMessage[0]==="boundReceived"){
         self.__boundSent=true
     }
     */
 }

 function _sendIfReady(self,message,destination){
    if (self.isAlive()){
        self.send(Buffer.from(message),destination)
    }
    else{
        self.__queue.push(()=>{self.send(Buffer.from(message),destination)})
    }
 }
 
 function _responseMessage(self,message){
     
     self.__controlSocket.send(Buffer.from(message),37710,'0.0.0.0',function(error){
         if(error){
         //talvez nao fechar aqui
         self.__controlSocket.close()
         }
     })
 
 }
 
 function _preTestConfirmation(self,msg,peerId){
     let splitMessage=msg.split(',')
     if (splitMessage[0]==="serverReady" && splitMessage.length == 3){
         _responseMessage(self,msg+","+peerId)
     }
     //recebe o gonnaTest, manda pro python e ja fecha o socket
     else if(splitMessage[0]==="gonnaTest" && splitMessage.length == 3){
         _responseMessage(self,msg+","+peerId)
         self.emit("startTest")
 
     }
     else if (splitMessage[0]==="vazao" && splitMessage.length==2){
         _responseMessage(self,msg)
     }
     else if(splitMessage[0]==="endTest"){
         _responseMessage(self,msg+","+peerId);   
        
     }
     else if(splitMessage[0]==="endTest_ack"){
        _responseMessage(self,msg+","+peerId)
     }
     else if (splitMessage[0]==="offer"){
         _responseMessage(self,"offer,"+peerId)
     }
     else if (splitMessage[0]==="offer_rjct"){
        _responseMessage(self,"offer_rjct,"+peerId)
     }
     else if (splitMessage[0]==="offer_res"){
        _responseMessage(self,"offer_res,"+peerId)
     }
     else if (splitMessage[0]==="offer_abort"){
        _responseMessage(self,"offer_abort,"+peerId)
     }
     else if (splitMessage[0]==="offer_abort_ack"){
        _responseMessage(self,"offer_abort_ack,"+peerId)
     }
 }
 
 // -- exports
 module.exports = NetworkDht;
 
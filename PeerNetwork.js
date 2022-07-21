const PeerNetwork = require("@josaiasmoura/peer-network")

let peer = new PeerNetwork({group:"thomas",password:"thomas"},37711)

peer.on("offline",(offPeer) => {
	console.log("Peer esta offline agora! ",offPeer)
}).on("message", (msg,from) => {
	console.log("Voce recebeu mensagem!",from,msg.toString())
}).on("online",(newPeer) => {
	console.log("Novo peer online! ",newPeer)
}).on("ready", () =>{
	console.log("estou online!")
	//jah=peer.__network.__peers
	//console.log("Printando ",jah)
}).on("warning",(err) => {
	console.log("Alerta! ",err.message)
}).on("startTest",()=>{
	console.log("startTestChegou!")
	peer.clearQueue()
})

peer.start()


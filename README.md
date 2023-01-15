# TCC

# Este tutorial supõe que você ja tenha o python3 e o pip3 instalado e que você esteja utilizando o ubuntu 20.04 LTS.

## Para rodar a prova de conceito:

	sudo apt update
	
	sudo apt install -y --no-install-recommends nodejs npm pv socat python3-pip git build-essential vim ncat

	pip3 install iperf3 

	pip3 install psutil  

### Instalando o iperf3

	git clone https://github.com/esnet/iperf.git iperf3

	cd iperf3

	./configure

	make

	sudo make install

	sudo ldconfig

	cd ..
	
### Instalando o SpeedTest-cli
	
	sudo apt install -y --no-install-recommends curl
	
	curl -s https://packagecloud.io/install/repositories/ookla/speedtest-cli/script.deb.sh | bash
	
	sudo apt install -y --no-install-recommends speedtest

	speedtest (aceite a licença)
	
### Instalando a Prova de Conceito:

	git clone https://github.com/Konomaster/TCC.git

	cd TCC 

	git clone https://github.com/jselbie/stunserver.git

	cd stunserver

	sudo apt install -y --no-install-recommends g++ make libboost-dev libssl-dev

	make

	cd ../

	npm install @josaiasmoura/peer-network --save

	rm -r node_modules/@josaiasmoura

	cp -r @josaiasmoura node_modules

	cd faqir/

### Rodando a prova de conceito

	python3 PoC.py

### Obs: talvez seja necessario colocar manualmente o caminho do libiperf.so.0

	sudo find /home -name 'libiperf*'
	
	no teste udp (aprox linha 270 do arquivo PoC.py) trocar o c = iperf3.Client() por c = iperf3.Client(lib_name="<caminho da biblioteca>")
	
### 

# TCC

# Este tutorial supõe que você ja tenha o python3 e o pip3 instalado e que você esteja utilizando o ubuntu 20.04 LTS.

## Para rodar a prova de conceito:

	sudo apt update
	
	sudo apt install -y --no-install-recommends nodejs npm pv socat python3-pip git build-essential vim ncat

	pip3 install iperf3 

	pip3 install psutil  
	
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
	

### Instalando o iperf3

	git clone https://github.com/esnet/iperf.git iperf3

	cd iperf3

	./configure

	make

	sudo make install

	sudo ldconfig

	cd ../faqir
	
### Instalando o SpeedTest-cli

Também serão realizadas aferições com o Speedtest, permitindo a comparação dos resultados 
da Peertest contra ele.

Caso queira desabilitar o Speedtest, comente as linhas 943 e 944 no arquivo PoC.py
	
	sudo apt install -y --no-install-recommends curl
	
	sudo curl -s https://packagecloud.io/install/repositories/ookla/speedtest-cli/script.deb.sh | sudo bash
	
	sudo apt install -y --no-install-recommends speedtest

	speedtest

### Rodando a prova de conceito

	python3 PoC.py

Os resultados das aferições estarão nos arquivos "results.txt" para a Peertest 
e "results_speedtest.txt" para o Speedtest.

### Obs: talvez seja necessario colocar manualmente o caminho do libiperf.so.0

	sudo find /home -name 'libiperf*'
	
	no teste udp (aprox linha 270 do arquivo PoC.py) trocar o c = iperf3.Client() por c = iperf3.Client(lib_name="<caminho da biblioteca>")
	
### 

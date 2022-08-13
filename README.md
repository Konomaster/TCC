#TCC

#Este tutorial supõe que você ja tenha o python3 e o pip3 instalado e que você este utilizando o ubuntu 20.04 LTS.

## Para rodar a prova de conceito:

	sudo apt update

	sudo apt install nodejs 

	sudo apt install pv 

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

### Instalando a Prova de Conceito:

	git clone https://github.com/Konomaster/TCC.git

	cd TCC 

	git clone https://github.com/jselbie/stunserver.git

	cd stunserver

	sudo apt-get install g++

	sudo apt-get install make

	sudo apt-get install libboost-dev

	sudo apt-get install libssl-dev

	make

	cd ../

	npm install @josaiasmoura/peer-network --save

	rm -r node_modules/@josaiasmoura

	cp -r @josaiasmoura node_modules

	cd faqir/

### Rodando a prova de conceito

	git checkout 1c41027aecd279549fe9bf480a44b6ae154ffb0e

	python3 PoC.py



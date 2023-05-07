#!/usr/bin/env Rscript
#
# Generate boxplots side by side grouped by hour
#
# Version 0.9
# (c) 2023 Everthon Valadao <everthonvaladao@gmail.com> under the GPL
#          http://www.gnu.org/copyleft/gpl.html
#

datasets = c("peertest-notebook.dat", "speedtest-notebook.dat")

for ( i in 1:length(datasets) ){

	data = read.table(file=datasets[i], header=TRUE, sep='\t')

	#colnames(data)
	metricas 		  = c( "Download..Mbps."	, "Upload..Mbps."	, "Jitter..ms."	, "Packet.Loss...."		, "Delay..ms." )
	metricas_title 	  = c( "Vazão do Download"	, "Vazão do Upload"	, "Jitter"		, "Perda de Pacotes"	, "Latência" )
	metricas_ylabel   = c( "Vazão (Mbit/s)"		, "Vazão (Mbit/s)"	, "Jitter (ms)"	, "Perda de Pacotes (%)", "Latência (ms)" )
	metricas_filename = c( "download"			, "upload"			, "jitter"		, "loss"				, "latency" )
	
	for ( j in 1:length(metricas) ){
		
		hours_xlabel = paste(0:23, "h", sep="")
		hours = list()		
		for (h in 1:24){
			hours[[h]] = data[,metricas[j]][ which( data$Hora.do.Dia..24h. == (h-1) ) ]
		}

		# hourGroup_xlabel = list()
		# hourGroup = list()
		# for (g in 0:7){	## de 3 em 3 horas (8 barras)
		# 	hourGroup[[g+1]] = c( hours[[3*g+1]] , hours[[3*g+2]] , hours[[3*g+3]] )
		# 	hourGroup_xlabel[[g+1]] = paste( hours_xlabel[3*g+1], "-", hours_xlabel[3*g+3], sep="" )
		# }

		hourGroup_xlabel = list()
		hourGroup = list()
		for (g in 0:5){		## de 4 em 4 horas (6 barras)
			hourGroup[[g+1]] = c( hours[[4*g+1]] , hours[[4*g+2]] , hours[[4*g+3]] , hours[[4*g+4]] )
			hourGroup_xlabel[[g+1]] = paste( hours_xlabel[4*g+1], "-", hours_xlabel[4*g+4], sep="" )
		}

		# hourGroup_xlabel = list()
		# hourGroup = list()
		# for (g in 0:3){		## de 6 em 6 horas (4 barras)
		# 	hourGroup[[g+1]] = c( hours[[6*g+1]] , hours[[6*g+2]] , hours[[6*g+3]] , hours[[6*g+4]] , hours[[6*g+5]] , hours[[6*g+6]] )
		# 	hourGroup_xlabel[[g+1]] = paste( hours_xlabel[6*g+1], "-", hours_xlabel[6*g+6], sep="" )
		# }

		if (metricas_filename[j] == "loss"){
			metrica_ylim = c(0.0, 0.25)	
		}
		else{
			# metrica_ylim = c(min(data[,metricas[j]]),quantile(data[,metricas[j]], c(.95)))
			metrica_ylim = c( max(0,quantile(data[,metricas[j]], c(.10))), quantile(data[,metricas[j]], c(.90)))
			# metrica_ylim = c( max(0,mean(data[,metricas[j]])-1.5*sd(data[,metricas[j]])) , mean(data[,metricas[j]])+1.5*sd(data[,metricas[j]]))
		}
		svg( paste("hoursOfTheDay-", metricas_filename[j], "_", datasets[i], ".svg", sep="") )

		par(mfrow=c(1,1))
		boxplot( 
			hourGroup #hours
			, main=paste("Variação de ", metricas_title[j], " conforme o Horário", sep="")
			, ylab = metricas_ylabel[j]
			, xlab = "Horário do Dia"
			, ylim = metrica_ylim
			, names = hourGroup_xlabel #hours_xlabel
			)

		dev.off() 

	} #for metricas

} #for datasets
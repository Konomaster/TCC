#!/usr/bin/env Rscript
#
# Generate boxplots side by side grouped by weekday
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
	weekdays_xlabel = c("Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom")

	for ( j in 1:length(metricas) ){

		seg1 = data[,metricas[j]][ which( data$Dia.da.Semana..1.7. == '1' ) ]
		ter2 = data[,metricas[j]][ which( data$Dia.da.Semana..1.7. == '2' ) ]
		qua3 = data[,metricas[j]][ which( data$Dia.da.Semana..1.7. == '3' ) ]
		qui4 = data[,metricas[j]][ which( data$Dia.da.Semana..1.7. == '4' ) ]
		sex5 = data[,metricas[j]][ which( data$Dia.da.Semana..1.7. == '5' ) ]
		sab6 = data[,metricas[j]][ which( data$Dia.da.Semana..1.7. == '6' ) ]
		dom7 = data[,metricas[j]][ which( data$Dia.da.Semana..1.7. == '7' ) ]

		if (metricas_filename[j] == "loss"){
			metrica_ylim = c(0.0, 0.25)	
		}
		else{
			# metrica_ylim = c(min(data[,metricas[j]]),quantile(data[,metricas[j]], c(.95)))
			metrica_ylim = c( max(0,quantile(data[,metricas[j]], c(.10))), quantile(data[,metricas[j]], c(.90)))
			# metrica_ylim = c( max(0,mean(data[,metricas[j]])-1.5*sd(data[,metricas[j]])) , mean(data[,metricas[j]])+1.5*sd(data[,metricas[j]]))
		}
		# metrica_ylim = c(
		# 					min ( 
		# 						c( 	  quantile(seg1, c(.20)) 
		# 							, quantile(ter2, c(.20)) 
		# 							, quantile(qua3, c(.20)) 
		# 							, quantile(qui4, c(.20)) 
		# 							, quantile(sex5, c(.20)) 
		# 							, quantile(sab6, c(.20)) 
		# 							, quantile(dom7, c(.20)) 
		# 						)
		# 					)			
		# 					, max ( 
		# 						c( 	  quantile(seg1, c(.80)) 
		# 							, quantile(ter2, c(.80)) 
		# 							, quantile(qua3, c(.80)) 
		# 							, quantile(qui4, c(.80)) 
		# 							, quantile(sex5, c(.80)) 
		# 							, quantile(sab6, c(.80)) 
		# 							, quantile(dom7, c(.80)) 
		# 						)
		# 					)				
		# 	) ## min max of quartiles
		

		svg( paste("weekdays-", metricas_filename[j], "_", datasets[i], ".svg", sep="") )

		par(mfrow=c(1,1))
		boxplot( 
			seg1,ter2,qua3,qui4,sex5,sab6,dom7 
			, main=paste("Variação de ", metricas_title[j], " conforme o Dia da Semana", sep="")
			, ylab = metricas_ylabel[j]
			, xlab = "Dias da Semana"
			, ylim = metrica_ylim
			, names = weekdays_xlabel
			)

		dev.off() 

	} #for metricas

} #for datasets
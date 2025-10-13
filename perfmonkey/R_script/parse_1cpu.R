library(tidyverse)

args <- commandArgs(trailingOnly = TRUE)

timedate_fmt<-"%Y/%m/%d %H:%M"

if (length(args)==0)
{
  stop("At least one argument must be supplied <input file> [<timedate fmt>])", call.=FALSE)
} else {
  input_file<-args[1]
  if (length(args)>1)
  {
    timedate_fmt<-args[2]
  }
}


label<-"CPUPERF"
serial<-"111111"
type<-"CPU"

output_file<-paste0(input_file,"_output")

data <- read.csv(input_file)
metrics <- unique(data$Metric)

dataf_list<-split(data, f=data$Metric)
dataf_list<-lapply(dataf_list,select,InstanceName,Time,Value)

output_df<-dataf_list[metrics[1]][[1]]
output_df$Label<-rep(label,nrow(output_df))
output_df$RowNumber<-seq(from = 1, to = nrow(output_df), by = 1)
output_df$Serial<-rep(serial,nrow(output_df))
output_df$Type<-rep(paste0("'",type,"'"),nrow(output_df))

output_df$BgnDateTime<-strftime(as.POSIXct(output_df$Time,format=timedate_fmt),format="%m/%d/%y %H:%M:%S")
output_df$EndDateTime<-output_df$BgnDateTime
output_df<-output_df[,c("Label","RowNumber","BgnDateTime","EndDateTime","Serial","InstanceName","Type","Value")]

for(i in 2:length(metrics))
{
  df<-dataf_list[metrics[i]][[1]]
  output_df<-cbind(output_df,df[,c("Value")])
}

names(output_df)<-c("CPUPERF","#","BgnDateTime","EndDateTime","Serial","Slot","Type",metrics)

write.csv(output_df, file = output_file, row.names = FALSE)

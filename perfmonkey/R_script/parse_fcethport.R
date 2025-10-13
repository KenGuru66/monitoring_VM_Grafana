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


label<-"PORTPERF"
serial<-"111111"
slot<-"1"
mode<-"Tgt"
alias<-"---"

output_file<-paste0(input_file,"_output")
data <- read.csv(input_file)

metrics <- unique(data$Metric)
instances<-unique(data$InstanceName)
timepoints<-unique(data$Time)


dataf_list<-split(data, f=data$Metric)
dataf_list<-lapply(dataf_list,select,Time,InstanceName,Value)

merged_df<-dataf_list[metrics[1]][[1]]
datapoints<-nrow(merged_df)/length(instances)

for( i in 2:length(metrics))
{
  merged_df<-merge(merged_df,dataf_list[metrics[i]][[1]],by=c("Time","InstanceName"))
}


output_df = data.frame(Label=rep(label,nrow(merged_df)))
output_df$RowNumber<-rep(1:length(timepoints), each = length(instances))
output_df$BgnDateTime<-strftime(as.POSIXct(merged_df$Time,format=timedate_fmt),format="%m/%d/%y %H:%M:%S")
output_df$EndDateTime<-output_df$BgnDateTime
output_df$Serial<-rep(serial,nrow(merged_df))
output_df$Slot<-rep(paste0("'",slot,"'"),nrow(output_df))
output_df<-cbind(output_df,merged_df[,2])
output_df$Mode<-rep(paste0("'",mode,"'"),nrow(output_df))
output_df$Alias<-rep(paste0("'",alias,"'"),nrow(output_df))

nc<-ncol(merged_df)
output_df<-cbind(output_df,merged_df[,3:nc])
names(output_df)<-c(label,"#","BgnDateTime","EndDateTime","Serial","Slot","Port","Mode","Alias",metrics)


write.csv(output_df, file = output_file, row.names = FALSE)


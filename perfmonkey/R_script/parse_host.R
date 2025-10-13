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

label<-"HAPERF"
serial<-"111111"
mpcnt<-"1"
dacnt<-"1"
pgcnt<-"1"
rgcnt<-"1"

output_file<-paste0(input_file,"_output")
data <- read.csv(input_file)

metrics <- unique(data$Metric)
instances<-unique(data$InstanceName)
timepoints<-unique(data$Time)


dataf_list<-split(data, f=data$Metric)
dataf_list<-lapply(dataf_list,select,Time,InstanceName,Value)

#find instanses with fewer datapoints
short_instances<-0

for(i in 1:length(instances))
{
  cur_inst<-subset(data,InstanceName==instances[i])
  n<-nrow(cur_inst)
  tp<-length(metrics)*length(timepoints)
  if(n<tp)
  {
    print(paste("Instance ",instances[i]," has fewer datapoints than should: ",n," instead of ",tp))
    short_instances<-short_instances+1
  }
}

if(short_instances>0)
{
  stop(paste("ERROR: ",short_instances," instances have fewer datapoints than should (see above). Execution halted."), call.=FALSE)

}

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
output_df$MpCnt<-rep(paste0("'",mpcnt,"'"),nrow(merged_df))
output_df$DaCnt<-rep(paste0("'",dacnt,"'"),nrow(merged_df))
output_df$PgCnt<-rep(paste0("'",pgcnt,"'"),nrow(merged_df))
output_df$RgCnt<-rep(paste0("'",rgcnt,"'"),nrow(merged_df))


nc<-ncol(merged_df)
output_df<-cbind(output_df,merged_df[,2:nc])
names(output_df)<-c(label,"#","BgnDateTime","EndDateTime","Serial","DefMp","DaCnt","RgCnt","PgCnt","Alias",metrics)


write.csv(output_df, file = output_file, row.names = FALSE)

#!/usr/bin/env Rscript
# Simple version without tidyverse dependency, using semicolon separator

args <- commandArgs(trailingOnly = TRUE)

timedate_fmt<-"%Y-%m-%dT%H:%M:%SZ"

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

cat("Reading CSV file...\n")
# Read CSV with semicolon separator
data <- read.csv(input_file, sep=";", stringsAsFactors = FALSE)

# Get unique metrics and instances
metrics <- unique(data$Metric)
instances <- unique(data$InstanceName)
timepoints <- unique(data$Time)

cat(sprintf("Found %d metrics, %d instances, %d timepoints\n", 
            length(metrics), length(instances), length(timepoints)))

# Check for instances with incomplete data
cat("Checking for instances with incomplete data...\n")
expected_points <- length(metrics) * length(timepoints)
for(inst in instances) {
  inst_data <- data[data$InstanceName == inst, ]
  actual_points <- nrow(inst_data)
  if (actual_points < expected_points) {
    cat(sprintf("WARNING: Instance '%s' has %d datapoints instead of %d\n", 
                inst, actual_points, expected_points))
  }
}

cat("Creating data structure...\n")
# Create list split by metric
dataf_list <- split(data, f=data$Metric)

# Select only needed columns for each metric
dataf_list <- lapply(dataf_list, function(df) {
  df[, c("InstanceName", "Time", "Value")]
})

# Start with first metric
output_df <- dataf_list[[metrics[1]]]
output_df$Label <- label
output_df$RowNumber <- seq(from = 1, to = nrow(output_df), by = 1)
output_df$Serial <- serial
output_df$Type <- paste0("'", type, "'")

# Convert time
cat("Converting time format...\n")
output_df$BgnDateTime <- strftime(as.POSIXct(output_df$Time, format=timedate_fmt), 
                                   format="%m/%d/%y %H:%M:%S")
output_df$EndDateTime <- output_df$BgnDateTime

# Reorder columns
output_df <- output_df[, c("Label", "RowNumber", "BgnDateTime", "EndDateTime", 
                           "Serial", "InstanceName", "Type", "Value")]

# Add other metrics as columns
cat("Merging metrics...\n")
for(i in 2:length(metrics))
{
  if (i %% 10 == 0) {
    cat(sprintf("  Processing metric %d of %d...\n", i, length(metrics)))
  }
  df <- dataf_list[[metrics[i]]]
  output_df <- cbind(output_df, df[, "Value", drop=FALSE])
}

# Set column names
colnames(output_df) <- c("CPUPERF", "#", "BgnDateTime", "EndDateTime", "Serial", 
                         "Slot", "Type", metrics)

# Write output
cat("Writing output...\n")
write.csv(output_df, file = output_file, row.names = FALSE)

cat(sprintf("SUCCESS! Output written to: %s\n", output_file))
cat(sprintf("Output has %d rows and %d columns\n", nrow(output_df), ncol(output_df)))


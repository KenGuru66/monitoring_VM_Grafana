#!/usr/bin/env Rscript
# parse_single_disk.R - Process ONE disk file (memory efficient)

args <- commandArgs(trailingOnly = TRUE)
if (length(args) == 0) {
  stop("Usage: Rscript parse_single_disk.R <input_file>", call.=FALSE)
}

input_file <- args[1]
timedate_fmt <- "%Y/%m/%d %H:%M"

label <- "RGPERF"
mpcnt <- "1"
pgcnt <- "1"
ldcnt <- "1"
alias <- "-"

# Extract Serial Number from filename
filename <- basename(input_file)
filename_clean <- gsub("\\.csv.*$", "", filename)
sn_match <- regmatches(filename_clean, regexpr("[0-9A-Z]{15,}", filename_clean))
serial <- if (length(sn_match) > 0) sn_match[1] else "111111"

# Read data
data <- read.csv(input_file, sep=";", stringsAsFactors = FALSE)

# Clean metric names
data$Metric <- gsub(",", "_", data$Metric)
data$Metric <- gsub("∞", "8", data$Metric)
data$Metric <- gsub('"', "", data$Metric)

# Sort by time
data <- data[order(data$Time), ]

metrics <- unique(data$Metric)
inst <- unique(data$InstanceName)[1]

# Split by metric
dataf_list <- split(data, f=data$Metric)
dataf_list <- lapply(dataf_list, function(df) df[, c("Time", "Value")])

# Start with first metric
merged_df <- dataf_list[[1]]
colnames(merged_df) <- c("Time", metrics[1])

# Merge other metrics
if (length(metrics) > 1) {
  for(i in 2:length(metrics)) {
    temp_df <- dataf_list[[i]]
    colnames(temp_df) <- c("Time", metrics[i])
    merged_df <- merge(merged_df, temp_df, by="Time", all=TRUE)
  }
}

# Create output
output_df <- data.frame(
  Label = rep(label, nrow(merged_df)),
  BgnDateTime = strftime(as.POSIXct(merged_df$Time, format=timedate_fmt), format="%m/%d/%y %H:%M:%S"),
  stringsAsFactors = FALSE
)
output_df$EndDateTime <- output_df$BgnDateTime
output_df$Serial <- rep(serial, nrow(merged_df))
output_df$MpCnt <- rep(mpcnt, nrow(merged_df))
output_df$Rg <- rep(inst, nrow(merged_df))
output_df$PgCnt <- rep(pgcnt, nrow(merged_df))
output_df$LdCnt <- rep(ldcnt, nrow(merged_df))
output_df$Alias <- rep(alias, nrow(merged_df))

# Add metrics
for(metric in metrics) {
  output_df[[metric]] <- merged_df[[metric]]
}

# Add row numbers
output_df <- cbind(
  output_df[, 1, drop=FALSE],
  "#" = seq(1, nrow(output_df)),
  output_df[, 2:ncol(output_df)]
)

colnames(output_df) <- c("RGPERF", "#", "BgnDateTime", "EndDateTime", "Serial",
                          "MpCnt", "Rg", "PgCnt", "LdCnt", "Alias", metrics)

# Output file
inst_clean <- gsub("\\.", "_", inst)
inst_clean <- gsub("/", "_", inst_clean)
output_file <- gsub("\\.csv$", "_output.csv", input_file)

write.table(output_df, file = output_file, sep = ",",
            row.names = FALSE, col.names = TRUE, quote = FALSE)

cat(sprintf("%s: %d rows\n", basename(output_file), nrow(output_df)))


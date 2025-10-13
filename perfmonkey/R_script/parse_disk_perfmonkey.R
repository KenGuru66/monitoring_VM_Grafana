#!/usr/bin/env Rscript
# parse_disk_perfmonkey.R
# Converts Huawei Disk performance data to PerfMonkey format
# WITHOUT tidyverse dependency, WITH automatic SN extraction,
# WITH time sorting, and creates SEPARATE files for each disk

args <- commandArgs(trailingOnly = TRUE)

timedate_fmt <- "%Y/%m/%d %H:%M"

if (length(args) == 0) {
  stop("At least one argument must be supplied <input file> [<timedate fmt>])", call.=FALSE)
} else {
  input_file <- args[1]
  if (length(args) > 1) {
    timedate_fmt <- args[2]
  }
}

cat("\n═══════════════════════════════════════════════════════════════\n")
cat("  DISK PERFORMANCE → PERFMONKEY FORMAT CONVERTER\n")
cat("═══════════════════════════════════════════════════════════════\n\n")

label <- "RGPERF"
mpcnt <- "1"
pgcnt <- "1"
ldcnt <- "1"
alias <- "-"

# Extract Serial Number from filename
cat("Extracting Serial Number from filename...\n")
filename <- basename(input_file)
filename_clean <- gsub("\\.csv.*$", "", filename)
sn_match <- regmatches(filename_clean, regexpr("[0-9A-Z]{15,}", filename_clean))
if (length(sn_match) > 0) {
  serial <- sn_match[1]
  cat(sprintf("  ✓ Extracted Serial Number: %s\n", serial))
} else {
  serial <- "111111"
  cat("  ⚠ WARNING: Could not extract SN from filename, using default: 111111\n")
}

cat("\nReading CSV file...\n")
# Read CSV with semicolon separator
data <- read.csv(input_file, sep=";", stringsAsFactors = FALSE)
cat(sprintf("  ✓ Read %d rows\n", nrow(data)))

# Clean metric names for PerfMonkey compatibility
cat("\nCleaning metric names...\n")
data$Metric <- gsub(",", "_", data$Metric)
data$Metric <- gsub("∞", "8", data$Metric)  # infinity symbol
data$Metric <- gsub('"', "", data$Metric)   # remove quotes if any
cat("  ✓ Cleaned metric names (replaced commas and special chars)\n")

# Sort data by InstanceName and Time for proper ordering
cat("\nSorting data by instance and time...\n")
data <- data[order(data$InstanceName, data$Time), ]
cat("  ✓ Data sorted\n")

metrics <- unique(data$Metric)
instances <- unique(data$InstanceName)

cat(sprintf("\nData summary:\n"))
cat(sprintf("  • Unique instances (disks): %d\n", length(instances)))
cat(sprintf("  • Unique metrics: %d\n", length(metrics)))
cat(sprintf("  • Disk IDs: %s\n", paste(head(instances, 10), collapse=", ")))
if (length(instances) > 10) {
  cat(sprintf("    ... and %d more\n", length(instances) - 10))
}

# Process each instance (disk) separately to handle different timepoints
cat("\nProcessing each disk separately...\n")
all_instance_data <- list()

for(inst in instances) {
  cat(sprintf("\n  Processing disk: %s\n", inst))
  
  # Filter data for this instance
  inst_data <- subset(data, InstanceName == inst)
  
  # Get unique timepoints for this instance
  inst_timepoints <- unique(inst_data$Time)
  cat(sprintf("    • Timepoints: %d\n", length(inst_timepoints)))
  cat(sprintf("    • Rows: %d\n", nrow(inst_data)))
  
  # Split data by metric
  dataf_list <- split(inst_data, f=inst_data$Metric)
  
  # Extract only Time and Value columns for each metric
  dataf_list <- lapply(dataf_list, function(df) {
    df[, c("Time", "Value")]
  })
  
  # Start with first metric
  merged_df <- dataf_list[[1]]
  colnames(merged_df) <- c("Time", metrics[1])
  
  # Merge all other metrics
  if (length(metrics) > 1) {
    for(i in 2:length(metrics)) {
      temp_df <- dataf_list[[i]]
      colnames(temp_df) <- c("Time", metrics[i])
      merged_df <- merge(merged_df, temp_df, by="Time", all=TRUE)
    }
  }
  
  # Create output dataframe for this instance
  inst_output <- data.frame(
    Label = rep(label, nrow(merged_df)),
    BgnDateTime = strftime(as.POSIXct(merged_df$Time, format=timedate_fmt), 
                           format="%m/%d/%y %H:%M:%S"),
    stringsAsFactors = FALSE
  )
  inst_output$EndDateTime <- inst_output$BgnDateTime
  inst_output$Serial <- rep(serial, nrow(merged_df))
  inst_output$MpCnt <- rep(mpcnt, nrow(merged_df))
  inst_output$Rg <- rep(inst, nrow(merged_df))  # Disk ID
  inst_output$PgCnt <- rep(pgcnt, nrow(merged_df))
  inst_output$LdCnt <- rep(ldcnt, nrow(merged_df))
  inst_output$Alias <- rep(alias, nrow(merged_df))
  
  # Add metric columns
  for(metric in metrics) {
    inst_output[[metric]] <- merged_df[[metric]]
  }
  
  all_instance_data[[inst]] <- inst_output
  cat(sprintf("    ✓ Processed %d rows\n", nrow(inst_output)))
}

cat("\n═══════════════════════════════════════════════════════════════\n")
cat("  Writing separate files for each disk...\n")
cat("═══════════════════════════════════════════════════════════════\n\n")

output_files <- c()
for(inst in names(all_instance_data)) {
  inst_df <- all_instance_data[[inst]]
  
  # Add row numbers as second column (after Label)
  inst_df <- cbind(
    inst_df[, 1, drop=FALSE],  # Label column
    "#" = seq(from = 1, to = nrow(inst_df), by = 1),
    inst_df[, 2:ncol(inst_df)]  # Rest of columns
  )
  
  # Set column names
  colnames(inst_df) <- c("RGPERF", "#", "BgnDateTime", "EndDateTime", "Serial",
                          "MpCnt", "Rg", "PgCnt", "LdCnt", "Alias", metrics)
  
  # Create output filename for this disk
  # Clean disk name for filename (replace dots and slashes)
  inst_clean <- gsub("\\.", "_", inst)
  inst_clean <- gsub("/", "_", inst_clean)
  
  inst_output_file <- gsub("\\.csv.*$", "", input_file)
  inst_output_file <- paste0(inst_output_file, "_", inst_clean, "_output.csv")
  
  # Write to file WITHOUT QUOTES
  write.table(inst_df, file = inst_output_file, sep = ",",
              row.names = FALSE, col.names = TRUE,
              quote = FALSE)  # NO QUOTES!
  
  output_files <- c(output_files, inst_output_file)
  cat(sprintf("  ✓ Disk %s: %s (%d rows)\n", inst, basename(inst_output_file), nrow(inst_df)))
}

cat("\n═══════════════════════════════════════════════════════════════\n")
cat("  ✅ COMPLETED SUCCESSFULLY!\n")
cat("═══════════════════════════════════════════════════════════════\n\n")
cat(sprintf("Total files created: %d\n", length(output_files)))
cat(sprintf("Serial Number: %s\n", serial))
cat(sprintf("Metrics per file: %d\n", length(metrics)))
cat("\nFiles are ready for PerfMonkey import! 🚀\n\n")


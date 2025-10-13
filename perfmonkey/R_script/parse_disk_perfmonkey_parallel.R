#!/usr/bin/env Rscript
# parse_disk_perfmonkey_parallel.R
# Converts Huawei Disk performance data to PerfMonkey format
# WITH parallel processing for faster execution on multi-core systems

library(parallel)

args <- commandArgs(trailingOnly = TRUE)

timedate_fmt <- "%Y/%m/%d %H:%M"
num_cores <- detectCores() - 2  # Leave 2 cores for system

if (length(args) == 0) {
  stop("At least one argument must be supplied <input file> [<timedate fmt>] [<num_cores>])", call.=FALSE)
} else {
  input_file <- args[1]
  if (length(args) > 1) {
    timedate_fmt <- args[2]
  }
  if (length(args) > 2) {
    num_cores <- as.numeric(args[3])
  }
}

# Ensure we don't use more cores than available
max_cores <- detectCores()
if (num_cores > max_cores) {
  num_cores <- max_cores - 1
}
if (num_cores < 1) {
  num_cores <- 1
}

cat("\n═══════════════════════════════════════════════════════════════\n")
cat("  DISK PERFORMANCE → PERFMONKEY (PARALLEL MODE)\n")
cat("═══════════════════════════════════════════════════════════════\n\n")
cat(sprintf("Using %d CPU cores (of %d available)\n\n", num_cores, max_cores))

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
data$Metric <- gsub("∞", "8", data$Metric)
data$Metric <- gsub('"', "", data$Metric)
cat("  ✓ Cleaned metric names\n")

# Sort data by InstanceName and Time
cat("\nSorting data...\n")
data <- data[order(data$InstanceName, data$Time), ]
cat("  ✓ Data sorted\n")

metrics <- unique(data$Metric)
instances <- unique(data$InstanceName)

cat(sprintf("\nData summary:\n"))
cat(sprintf("  • Unique instances (disks): %d\n", length(instances)))
cat(sprintf("  • Unique metrics: %d\n", length(metrics)))

# Function to process a single disk instance
process_disk_instance <- function(inst, data_subset, metrics, serial, label, mpcnt, pgcnt, ldcnt, alias, timedate_fmt) {
  # Filter data for this instance
  inst_data <- data_subset[data_subset$InstanceName == inst, ]
  
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
      if (!is.null(dataf_list[[i]])) {
        temp_df <- dataf_list[[i]]
        colnames(temp_df) <- c("Time", metrics[i])
        merged_df <- merge(merged_df, temp_df, by="Time", all=TRUE)
      }
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
  inst_output$Rg <- rep(inst, nrow(merged_df))
  inst_output$PgCnt <- rep(pgcnt, nrow(merged_df))
  inst_output$LdCnt <- rep(ldcnt, nrow(merged_df))
  inst_output$Alias <- rep(alias, nrow(merged_df))
  
  # Add metric columns
  for(metric in metrics) {
    inst_output[[metric]] <- merged_df[[metric]]
  }
  
  # Add row numbers as second column
  inst_output <- cbind(
    inst_output[, 1, drop=FALSE],
    "#" = seq(from = 1, to = nrow(inst_output), by = 1),
    inst_output[, 2:ncol(inst_output)]
  )
  
  # Set column names
  colnames(inst_output) <- c("RGPERF", "#", "BgnDateTime", "EndDateTime", "Serial",
                              "MpCnt", "Rg", "PgCnt", "LdCnt", "Alias", metrics)
  
  return(list(instance = inst, data = inst_output))
}

# Process all disks in parallel
cat("\n═══════════════════════════════════════════════════════════════\n")
cat(sprintf("  Processing %d disks in parallel...\n", length(instances)))
cat("═══════════════════════════════════════════════════════════════\n\n")

start_time <- Sys.time()

# Create cluster
cl <- makeCluster(num_cores)

# Export necessary variables to cluster
clusterExport(cl, c("data", "metrics", "serial", "label", "mpcnt", "pgcnt", "ldcnt", "alias", "timedate_fmt"))

# Process instances in parallel
results <- parLapply(cl, instances, function(inst) {
  process_disk_instance(inst, data, metrics, serial, label, mpcnt, pgcnt, ldcnt, alias, timedate_fmt)
})

# Stop cluster
stopCluster(cl)

end_time <- Sys.time()
processing_time <- difftime(end_time, start_time, units="secs")

cat(sprintf("\n✓ Parallel processing completed in %.1f seconds\n\n", processing_time))

# Write output files
cat("═══════════════════════════════════════════════════════════════\n")
cat("  Writing output files...\n")
cat("═══════════════════════════════════════════════════════════════\n\n")

output_files <- c()
for(result in results) {
  inst <- result$instance
  inst_df <- result$data
  
  # Clean disk name for filename
  inst_clean <- gsub("\\.", "_", inst)
  inst_clean <- gsub("/", "_", inst_clean)
  
  inst_output_file <- gsub("\\.csv.*$", "", input_file)
  inst_output_file <- paste0(inst_output_file, "_", inst_clean, "_output.csv")
  
  # Write to file WITHOUT QUOTES
  write.table(inst_df, file = inst_output_file, sep = ",",
              row.names = FALSE, col.names = TRUE,
              quote = FALSE)
  
  output_files <- c(output_files, inst_output_file)
  cat(sprintf("  ✓ %s (%d rows)\n", basename(inst_output_file), nrow(inst_df)))
}

cat("\n═══════════════════════════════════════════════════════════════\n")
cat("  ✅ COMPLETED SUCCESSFULLY!\n")
cat("═══════════════════════════════════════════════════════════════\n\n")
cat(sprintf("Total files created: %d\n", length(output_files)))
cat(sprintf("Serial Number: %s\n", serial))
cat(sprintf("Metrics per file: %d\n", length(metrics)))
cat(sprintf("Processing time: %.1f seconds\n", processing_time))
cat(sprintf("CPU cores used: %d\n", num_cores))
cat("\nFiles are ready for PerfMonkey import! 🚀\n\n")


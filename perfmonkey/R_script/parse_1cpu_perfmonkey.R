#!/usr/bin/env Rscript
# PerfMonkey compatible version - no quotes, replace commas in metric names

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
type<-"CPU"

# Extract Serial Number from filename
filename <- basename(input_file)
filename_clean <- gsub("\\.csv.*$", "", filename)
sn_match <- regmatches(filename_clean, regexpr("[0-9A-Z]{15,}", filename_clean))
if (length(sn_match) > 0) {
  serial <- sn_match[1]
  cat(sprintf("Extracted Serial Number: %s\n", serial))
} else {
  serial <- "111111"
  cat("WARNING: Could not extract SN from filename, using default: 111111\n")
}

output_file<-paste0(input_file,"_output.csv")

cat("Reading CSV file...\n")
# Read CSV with semicolon separator
data <- read.csv(input_file, sep=";", stringsAsFactors = FALSE)

# Sort data by InstanceName and Time for proper ordering
cat("Sorting data by instance and time...\n")
data <- data[order(data$InstanceName, data$Time), ]

# Clean metric names for PerfMonkey compatibility
# Replace commas with underscores
# Replace infinity symbol and other special characters
cat("Cleaning metric names...\n")
data$Metric <- gsub(",", "_", data$Metric)
data$Metric <- gsub("∞", "8", data$Metric)  # infinity symbol
data$Metric <- gsub('"', "", data$Metric)   # remove quotes if any

# Get unique metrics and instances
metrics <- unique(data$Metric)
instances <- unique(data$InstanceName)

cat(sprintf("Found %d metrics, %d instances\n", 
            length(metrics), length(instances)))

# Process each instance separately to handle different timepoints
all_instance_data <- list()

for(inst in instances) {
  cat(sprintf("\nProcessing instance: %s\n", inst))
  
  # Filter data for this instance
  inst_data <- data[data$InstanceName == inst, ]
  
  # Get timepoints for this specific instance
  inst_timepoints <- unique(inst_data$Time)
  cat(sprintf("  Instance %s: %d timepoints\n", inst, length(inst_timepoints)))
  
  # Check for incomplete data
  expected_points <- length(metrics) * length(inst_timepoints)
  actual_points <- nrow(inst_data)
  if (actual_points < expected_points) {
    cat(sprintf("  WARNING: Instance '%s' has %d datapoints instead of %d\n", 
                inst, actual_points, expected_points))
  }
  
  # Create list split by metric for this instance
  dataf_list <- split(inst_data, f=inst_data$Metric)
  dataf_list <- lapply(dataf_list, function(df) {
    df[, c("InstanceName", "Time", "Value")]
  })
  
  # Start with first metric
  inst_output <- dataf_list[[metrics[1]]]
  inst_output$Label <- label
  inst_output$Serial <- serial
  inst_output$Type <- type
  
  # Convert time
  inst_output$BgnDateTime <- strftime(as.POSIXct(inst_output$Time, format=timedate_fmt), 
                                      format="%m/%d/%y %H:%M:%S")
  inst_output$EndDateTime <- inst_output$BgnDateTime
  
  # Reorder columns
  inst_output <- inst_output[, c("Label", "BgnDateTime", "EndDateTime", 
                                 "Serial", "InstanceName", "Type", "Value")]
  
  # Add other metrics as columns
  for(i in 2:length(metrics)) {
    df <- dataf_list[[metrics[i]]]
    inst_output <- cbind(inst_output, df[, "Value", drop=FALSE])
  }
  
  # Store for this instance
  all_instance_data[[inst]] <- inst_output
}

cat("\nCombining all instances...\n")
# Combine all instances
output_df <- do.call(rbind, all_instance_data)

# Add row numbers as second column (after Label)
output_df <- cbind(
  output_df[, 1, drop=FALSE],  # Label column
  "#" = seq(from = 1, to = nrow(output_df), by = 1),
  output_df[, 2:ncol(output_df)]  # Rest of columns
)

# Set column names properly
colnames(output_df) <- c("CPUPERF", "#", "BgnDateTime", "EndDateTime", "Serial", 
                        "Slot", "Type", metrics)

# Write output WITHOUT quotes for PerfMonkey compatibility
cat("Writing output...\n")
write.table(output_df, file = output_file, sep = ",", 
            row.names = FALSE, col.names = TRUE, 
            quote = FALSE)  # NO QUOTES!

cat(sprintf("\n=== SUCCESS! ===\n"))
cat(sprintf("Output written to: %s\n", output_file))
cat(sprintf("Rows: %d (data rows, excluding header)\n", nrow(output_df)))
cat(sprintf("Columns: %d (7 service + %d metrics)\n", ncol(output_df), length(metrics)))
cat(sprintf("Serial Number: %s\n", serial))
cat(sprintf("Instances: %s\n", paste(instances, collapse=", ")))
cat("File format: CSV without quotes, commas in metric names replaced with underscores\n")
cat("Data is sorted by instance and time\n")


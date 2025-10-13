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

cat("\nWriting separate files for each instance...\n")

output_files <- c()

for(inst in names(all_instance_data)) {
  # Get data for this instance
  inst_df <- all_instance_data[[inst]]
  
  # Add row numbers
  inst_df <- cbind(
    inst_df[, 1, drop=FALSE],  # Label column
    "#" = seq(from = 1, to = nrow(inst_df), by = 1),
    inst_df[, 2:ncol(inst_df)]  # Rest of columns
  )
  
  # Set column names
  colnames(inst_df) <- c("CPUPERF", "#", "BgnDateTime", "EndDateTime", "Serial", 
                          "Slot", "Type", metrics)
  
  # Create output filename for this instance
  inst_output_file <- gsub("\\.csv.*$", "", input_file)
  inst_output_file <- paste0(inst_output_file, "_", inst, "_output.csv")
  
  # Write to file
  write.table(inst_df, file = inst_output_file, sep = ",", 
              row.names = FALSE, col.names = TRUE, 
              quote = FALSE)
  
  output_files <- c(output_files, inst_output_file)
  
  cat(sprintf("  ✓ Instance %s: %s (%d rows)\n", inst, basename(inst_output_file), nrow(inst_df)))
}

cat(sprintf("\n=== SUCCESS! ===\n"))
cat(sprintf("Created %d files:\n", length(output_files)))
for(f in output_files) {
  cat(sprintf("  - %s\n", basename(f)))
}
cat(sprintf("\nSerial Number: %s\n", serial))
cat(sprintf("Instances: %s\n", paste(instances, collapse=", ")))
cat(sprintf("Columns per file: %d (7 service + %d metrics)\n", 7 + length(metrics), length(metrics)))
cat("File format: CSV without quotes, commas in metric names replaced with underscores\n")
cat("Each instance has its own file, sorted by time\n")


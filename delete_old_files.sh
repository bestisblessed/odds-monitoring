#!/bin/bash

# Set the date to October 24, 2024
input_date="20241024"

# Directory containing the files
data_dir="data"

# Ensure the data directory exists
if [ ! -d "$data_dir" ]; then
    echo "Error: Directory $data_dir does not exist."
    exit 1
fi

# Loop through files in the data directory
for file in "$data_dir"/*; do
    # Extract the date from the filename
    file_date=$(echo "$file" | grep -o '[0-9]\{8\}')
    
    # Check if file_date is not empty
    if [ -n "$file_date" ]; then
        # Compare file date with input date
        if [ "$file_date" -lt "$input_date" ]; then
            echo "Deleting $file"
            rm "$file"
        fi
    else
        echo "No date found in filename: $file"
    fi
done

echo "Deletion complete."

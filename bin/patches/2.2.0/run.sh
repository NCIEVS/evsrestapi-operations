#!/bin/bash

# Script to unzip fhir_transforms.zip and run fhirMetadataUpdates.sh
# Expects to find fhir_transforms.zip in the same directory as this script
# (e.g., patches/2.2.0/fhir_transforms.zip when run from patches/2.2.0/)

# Define the directory where fhir_transforms.zip is expected

SCRIPT_DIR=$(dirname "$0")
DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
BIN_DIR="$DIR/../.."
ZIP_FILE="$SCRIPT_DIR/fhir_transforms.zip"
UNZIP_DIR="$BIN_DIR"
UPDATE_SCRIPT="$BIN_DIR/fhir_transforms/fhirMetadataUpdates.sh"

# Check if fhir_transforms.zip exists in the expected directory
if [ -f "$ZIP_FILE" ]; then
  echo "Found fhir_transforms.zip in $SCRIPT_DIR"

  # Create the unzip directory if it doesn't exist
  mkdir -p "$UNZIP_DIR"

  # Unzip fhir_transforms.zip into the fhir_transforms directory
  unzip -o "$ZIP_FILE" -d "$UNZIP_DIR" && {
    echo "Successfully unzipped fhir_transforms.zip into $UNZIP_DIR"

    # Check if fhirMetadataUpdates.sh exists in the unzipped directory
    if [ -f "$UPDATE_SCRIPT" ]; then
      echo "Found $UPDATE_SCRIPT"

      # Make the update script executable
      chmod +x "$UPDATE_SCRIPT"

      # Run fhirMetadataUpdates.sh and pipe its output to the console
      "$UPDATE_SCRIPT" "$BIN_DIR"
      UPDATE_SCRIPT_EXIT_CODE=$?

      if [ "$UPDATE_SCRIPT_EXIT_CODE" -eq 0 ]; then
        echo "Successfully executed $UPDATE_SCRIPT"
      else
        echo "Error: Failed to execute $UPDATE_SCRIPT (exit code: $UPDATE_SCRIPT_EXIT_CODE)"
        exit 1 # Exit with an error code
      fi
    else
      echo "Error: $UPDATE_SCRIPT not found"
      exit 1 # Exit with an error code
    fi
  } || {
    echo "Error: Failed to unzip $ZIP_FILE into $UNZIP_DIR"
    exit 1 # Exit with an error code
  }
else
  echo "Error: $ZIP_FILE not found in $SCRIPT_DIR"
  exit 1 # Exit with an error code
fi

echo "Script completed."
exit 0 # Exit with success code

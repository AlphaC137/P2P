#!/bin/bash

# Configure cronjob for payment processing
# This script sets up a daily cron job to run the payment processing command

# Get the absolute path to the Django project
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Create a temporary cron file
TEMP_CRON_FILE=$(mktemp)

# Export current crontab
crontab -l > "$TEMP_CRON_FILE" 2>/dev/null || echo "" > "$TEMP_CRON_FILE"

# Check if the cron job already exists
if ! grep -q "process_payments" "$TEMP_CRON_FILE"; then
    # Add the new cron job - run daily at 1:00 AM
    echo "0 1 * * * cd $PROJECT_DIR && python manage.py process_payments >> $PROJECT_DIR/logs/payment_processing.log 2>&1" >> "$TEMP_CRON_FILE"
    
    # Create logs directory if it doesn't exist
    mkdir -p "$PROJECT_DIR/logs"
    
    # Install the new crontab
    crontab "$TEMP_CRON_FILE"
    
    echo "Cron job for payment processing has been installed. It will run daily at 1:00 AM."
else
    echo "Cron job for payment processing already exists."
fi

# Clean up
rm "$TEMP_CRON_FILE"

echo "You can view logs at: $PROJECT_DIR/logs/payment_processing.log"
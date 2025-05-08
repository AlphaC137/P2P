#!/usr/bin/env python
"""
Payment processing scheduler script
Run this script to process payments, send reminders, and handle late payments.
This can be scheduled with various scheduling systems (systemd, Windows Task Scheduler, etc.)
or run manually for testing.
"""

import os
import sys
import logging
import datetime

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'p2p_platform.settings')
import django
django.setup()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs', 'payment_processing.log')),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def main():
    """Run the payment processing command"""
    from django.core.management import call_command
    
    logger.info(f"Starting payment processing at {datetime.datetime.now()}")
    
    try:
        # Create logs directory if it doesn't exist
        logs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
        os.makedirs(logs_dir, exist_ok=True)
        
        # Call the Django management command
        call_command('process_payments')
        
        logger.info("Payment processing completed successfully.")
    except Exception as e:
        logger.error(f"Error processing payments: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
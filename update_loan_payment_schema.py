#!/usr/bin/env python
"""
Script to manually add the automated payment fields to the LoanPayment table
Run this script once to update the database schema if migrations are failing
"""

import os
import sys
import sqlite3

def main():
    """Add the missing columns to the LoanPayment table"""
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'db.sqlite3')
    
    print(f"Connecting to database at: {db_path}")
    
    try:
        # Connect to the SQLite database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if the table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='lending_loanpayment';")
        if not cursor.fetchone():
            print("Error: lending_loanpayment table does not exist.")
            return 1
        
        # Get current columns in the table
        cursor.execute("PRAGMA table_info(lending_loanpayment);")
        columns = [row[1] for row in cursor.fetchall()]
        
        # Add the new columns if they don't exist
        new_columns = {
            'reminder_sent': 'INTEGER DEFAULT 0',
            'reminder_sent_date': 'TIMESTAMP NULL',
            'late_notice_sent': 'INTEGER DEFAULT 0',
            'late_notice_sent_date': 'TIMESTAMP NULL',
            'late_fee_amount': 'DECIMAL(12, 2) DEFAULT 0.00',
            'auto_payment_enabled': 'INTEGER DEFAULT 0'
        }
        
        for column, data_type in new_columns.items():
            if column not in columns:
                print(f"Adding column {column} to lending_loanpayment table")
                cursor.execute(f"ALTER TABLE lending_loanpayment ADD COLUMN {column} {data_type};")
            else:
                print(f"Column {column} already exists in lending_loanpayment table")
        
        # Commit the changes
        conn.commit()
        print("Database schema update completed successfully.")
        
    except Exception as e:
        print(f"Error updating database schema: {str(e)}")
        return 1
    finally:
        if conn:
            conn.close()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
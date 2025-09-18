#!/usr/bin/env python3
"""
Database migration script for Incident Reporting System
Adds new fields to existing incidents table:
- reporter_job_title
- reporter_email  
- reporter_phone
- incident_type
"""

import os
import sys
import sqlite3
from datetime import datetime

def migrate_database(db_path):
    """Migrate the database to add new fields"""
    print(f"🔄 Starting database migration for: {db_path}")
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if migration is needed by looking for new columns
        cursor.execute("PRAGMA table_info(incident)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # All new columns (including detailed incident fields)
        new_columns = [
            'reporter_job_title', 'reporter_email', 'reporter_phone', 'incident_type',
            'threats_weapons', 'medical_treatment', 'law_enforcement', 
            'security_intervention', 'incident_response', 'contributing_factors', 
            'corrective_actions'
        ]
        missing_columns = [col for col in new_columns if col not in columns]
        
        # Check if we need to rename 'description' to 'incident_description'
        rename_description = 'description' in columns and 'incident_description' not in columns
        
        if not missing_columns and not rename_description:
            print("✅ Database is already up to date!")
            return True
        
        # Handle column renaming first
        if rename_description:
            print("📝 Renaming 'description' column to 'incident_description'...")
            cursor.execute("ALTER TABLE incident ADD COLUMN incident_description TEXT")
            cursor.execute("UPDATE incident SET incident_description = description")
            print("   ✓ Added incident_description column and copied data")
            # Note: SQLite doesn't support dropping columns easily, so we leave the old 'description' column
        
        if missing_columns:
            print(f"📝 Adding missing columns: {', '.join(missing_columns)}")
            
            # Add missing columns
            for column in missing_columns:
                if column == 'incident_type':
                    # incident_type is required, so we need to add it with a default value
                    cursor.execute(f"ALTER TABLE incident ADD COLUMN {column} TEXT DEFAULT 'Type 1 – Criminal Intent'")
                    print(f"   ✓ Added {column} column with default value")
                else:
                    # Other columns are optional
                    cursor.execute(f"ALTER TABLE incident ADD COLUMN {column} TEXT")
                    print(f"   ✓ Added {column} column")
            
            # Update existing records to have a valid incident_type if it was added
            if 'incident_type' in missing_columns:
                cursor.execute("UPDATE incident SET incident_type = 'Type 1 – Criminal Intent' WHERE incident_type IS NULL OR incident_type = ''")
                updated_rows = cursor.rowcount
                print(f"   ✓ Updated {updated_rows} existing records with default incident type")
        
        # Commit changes
        conn.commit()
        conn.close()
        
        print("✅ Database migration completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False

def main():
    """Main migration function"""
    print("🗃️  Incident Reporting System - Database Migration")
    print("=" * 50)
    
    # Default database paths to check
    default_paths = [
        'instance/incidents.db',           # Local development
        'incidents.db',                    # Current directory
        '/var/lib/incident-reports/incidents.db',  # Production deployment
    ]
    
    # Check if database path was provided as argument
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
        if not os.path.exists(db_path):
            print(f"❌ Database file not found: {db_path}")
            return False
        return migrate_database(db_path)
    
    # Try to find database automatically
    found_db = None
    for path in default_paths:
        if os.path.exists(path):
            found_db = path
            break
    
    if found_db:
        print(f"📍 Found database at: {found_db}")
        return migrate_database(found_db)
    else:
        print("❌ No database file found in default locations:")
        for path in default_paths:
            print(f"   - {path}")
        print()
        print("Usage: python migrate_database.py [path_to_database.db]")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)

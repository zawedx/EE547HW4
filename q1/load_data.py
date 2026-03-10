import os
import sys
import csv
import argparse
import psycopg2

def create_schema(cursor, connection, schema_file='schema.sql'):
    print("Creating schema...")
    if not os.path.exists(schema_file):
        print(f"Error: Schema file '{schema_file}' not found.")
        sys.exit(1)
        
    with open(schema_file, 'r', encoding='utf-8') as f:
        schema_sql = f.read()
        
    try:
        cursor.execute(schema_sql)
        connection.commit()
        print("Tables created: lines, stops, line_stops, trips, stop_events\n")
    except Exception as e:
        print(f"Error executing schema: {e}")
        connection.rollback()
        sys.exit(1)

def load_csv_to_table(cursor, filepath, table_name):
    if not os.path.exists(filepath):
        print(f"Warning: File not found: {filepath}")
        return 0

    print(f"Loading {filepath}...", end=" ", flush=True)
    
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        try:
            headers = next(reader)
        except StopIteration:
            print("0 rows (empty file)")
            return 0
            
        headers = [h.strip() for h in headers]
        
        columns = ", ".join(headers)
        placeholders = ", ".join(["%s"] * len(headers))
        insert_query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"
        
        data = []
        for row in reader:
            cleaned_row = [col.strip() if isinstance(col, str) else col for col in row]
            data.append(cleaned_row)
            
        if not data:
            print("0 rows")
            return 0
            
        try:
            cursor.executemany(insert_query, data)
            row_count = len(data)
            print(f"{row_count} rows")
            return row_count
        except Exception as e:
            print(f"\nError loading {filepath} into {table_name}: {e}")
            raise e

def main():
    parser = argparse.ArgumentParser(description="Load transit data into PostgreSQL")
    parser.add_argument("--datadir", default="data", help="Directory containing CSV files")
    parser.add_argument("--host", default="db", help="Database host")
    parser.add_argument("--dbname", default="transit", help="Database name")
    parser.add_argument("--user", default="transit", help="Database user")
    parser.add_argument("--password", default="transit123", help="Database password")
    args = parser.parse_args()

    try:
        conn = psycopg2.connect(
            host=args.host,
            dbname=args.dbname,
            user=args.user,
            password=args.password
        )
        print(f"Connected to {args.user}@{args.host}")
    except psycopg2.OperationalError as e:
        print(f"Unable to connect to the database: {e}")
        sys.exit(1)

    cursor = conn.cursor()

    create_schema(cursor, conn)

    load_plan = [
        ("lines.csv", "lines"),
        ("stops.csv", "stops"),
        ("line_stops.csv", "line_stops"),
        ("trips.csv", "trips"),
        ("stop_events.csv", "stop_events")
    ]

    total_rows = 0
    try:
        for filename, table_name in load_plan:
            filepath = os.path.join(args.datadir, filename)
            rows_loaded = load_csv_to_table(cursor, filepath, table_name)
            total_rows += rows_loaded
            
        conn.commit()
        print(f"\nTotal: {total_rows} rows loaded")
        
    except Exception as e:
        print("\nAn error occurred during data loading. Rolling back changes.")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    main()
import sys
import json
import argparse
import datetime
import decimal
import psycopg2
import psycopg2.extras

class TransitJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime.datetime, datetime.date, datetime.time)):
            return obj.isoformat()
        if isinstance(obj, datetime.timedelta):
            return str(obj)
        if isinstance(obj, decimal.Decimal):
            return float(obj)
        return super(TransitJSONEncoder, self).default(obj)

QUERIES = {
    "Q1": {
        "description": "Route 20 stops in order",
        "sql": """
            SELECT stop_name, sequence, time_offset 
            FROM line_stops 
            WHERE line_name = 'Route 20' 
            ORDER BY sequence;
        """
    },
    "Q2": {
        "description": "Trips during morning rush (7-9 AM)",
        "sql": """
            SELECT trip_id, line_name, scheduled_departure 
            FROM trips 
            WHERE CAST(scheduled_departure AS TIME) BETWEEN '07:00:00' AND '09:00:00'
            ORDER BY scheduled_departure;
        """
    },
    "Q3": {
        "description": "Transfer stops (stops on 2+ routes)",
        "sql": """
            SELECT stop_name, COUNT(line_name) as line_count 
            FROM line_stops 
            GROUP BY stop_name 
            HAVING COUNT(line_name) > 1
            ORDER BY line_count DESC, stop_name;
        """
    },
    "Q4": {
        "description": "Complete route for trip T0001",
        "sql": """
            SELECT se.stop_name, se.scheduled, se.actual, se.passengers_on, se.passengers_off
            FROM stop_events se
            JOIN trips t ON se.trip_id = t.trip_id
            JOIN line_stops ls ON t.line_name = ls.line_name AND se.stop_name = ls.stop_name
            WHERE se.trip_id = 'T0001'
            ORDER BY ls.sequence;
        """
    },
    "Q5": {
        "description": "Routes serving both Wilshire / Veteran and Le Conte / Broxton",
        "sql": """
            SELECT line_name 
            FROM line_stops 
            WHERE stop_name IN ('Wilshire / Veteran', 'Le Conte / Broxton')
            GROUP BY line_name 
            HAVING COUNT(DISTINCT stop_name) = 2;
        """
    },
    "Q6": {
        "description": "Average ridership by line",
        "sql": """
            WITH trip_totals AS (
                SELECT t.line_name, t.trip_id, SUM(se.passengers_on) AS trip_ridership
                FROM trips t
                JOIN stop_events se ON t.trip_id = se.trip_id
                GROUP BY t.line_name, t.trip_id
            )
            SELECT line_name, ROUND(AVG(trip_ridership), 2) AS avg_passengers
            FROM trip_totals
            GROUP BY line_name
            ORDER BY avg_passengers DESC;
        """
    },
    "Q7": {
        "description": "Top 10 busiest stops",
        "sql": """
            SELECT stop_name, SUM(passengers_on + passengers_off) AS total_activity
            FROM stop_events
            GROUP BY stop_name
            ORDER BY total_activity DESC
            LIMIT 10;
        """
    },
    "Q8": {
        "description": "Count delays by line (>2 min late)",
        "sql": """
            SELECT t.line_name, COUNT(*) AS delay_count
            FROM stop_events se
            JOIN trips t ON se.trip_id = t.trip_id
            WHERE se.actual > se.scheduled + INTERVAL '2 minutes'
            GROUP BY t.line_name
            ORDER BY delay_count DESC;
        """
    },
    "Q9": {
        "description": "Trips with 3+ delayed stops",
        "sql": """
            SELECT trip_id, COUNT(*) AS delayed_stop_count
            FROM stop_events
            WHERE actual > scheduled + INTERVAL '2 minutes'
            GROUP BY trip_id
            HAVING COUNT(*) >= 3
            ORDER BY delayed_stop_count DESC;
        """
    },
    "Q10": {
        "description": "Stops with above-average ridership",
        "sql": """
            WITH stop_totals AS (
                SELECT stop_name, SUM(passengers_on) AS total_boardings
                FROM stop_events
                GROUP BY stop_name
            )
            SELECT stop_name, total_boardings
            FROM stop_totals
            WHERE total_boardings > (SELECT AVG(total_boardings) FROM stop_totals)
            ORDER BY total_boardings DESC;
        """
    }
}

def execute_query(cursor, query_id):
    if query_id not in QUERIES:
        print(f"Error: Query {query_id} not found.")
        return None
        
    query_info = QUERIES[query_id]
    
    try:
        cursor.execute(query_info["sql"])
        results = cursor.fetchall()
        
        return {
            "query": query_id,
            "description": query_info["description"],
            "results": results,
            "count": len(results)
        }
    except Exception as e:
        print(f"Error executing {query_id}: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description="Run Metro Transit SQL Queries")
    parser.add_argument("query", help="Query ID to run (e.g., Q1, Q2... or 'all')")
    parser.add_argument("--format", default="json", choices=["json"], help="Output format")
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
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    except psycopg2.OperationalError as e:
        print(f"Unable to connect to the database: {e}")
        sys.exit(1)

    queries_to_run = list(QUERIES.keys()) if args.query.lower() == 'all' else [args.query.upper()]
    
    output_data = []
    
    for q_id in queries_to_run:
        result = execute_query(cursor, q_id)
        if result:
            output_data.append(result)

    cursor.close()
    conn.close()

    if output_data:
        final_output = output_data[0] if len(output_data) == 1 else output_data
        print(json.dumps(final_output, indent=2, cls=TransitJSONEncoder))

if __name__ == "__main__":
    main()
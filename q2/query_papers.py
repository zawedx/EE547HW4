import sys
import json
import argparse
import time
import boto3
from boto3.dynamodb.conditions import Key
import decimal

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, decimal.Decimal):
            return float(obj) if obj % 1 > 0 else int(obj)
        return super(DecimalEncoder, self).default(obj)

def format_output(query_type, params, items, start_time):
    clean_items = []
    for item in items:
        clean_item = {k: v for k, v in item.items() if not k.startswith(('PK', 'SK', 'GSI'))}
        clean_items.append(clean_item)
        
    execution_time = int((time.time() - start_time) * 1000)
    
    result = {
        "query_type": query_type,
        "parameters": params,
        "results": clean_items,
        "count": len(clean_items),
        "execution_time_ms": execution_time
    }
    print(json.dumps(result, cls=DecimalEncoder, indent=2))

def query_recent(table, category, limit):
    start_time = time.time()
    response = table.query(
        KeyConditionExpression=Key('PK').eq(f"CATEGORY#{category}"),
        ScanIndexForward=False,
        Limit=limit
    )
    format_output("recent_in_category", {"category": category, "limit": limit}, response.get('Items', []), start_time)

def query_author(table, author):
    start_time = time.time()
    response = table.query(
        IndexName='AuthorIndex',
        KeyConditionExpression=Key('GSI1PK').eq(f"AUTHOR#{author}")
    )
    format_output("papers_by_author", {"author": author}, response.get('Items', []), start_time)

def query_get(table, arxiv_id):
    start_time = time.time()
    response = table.query(
        IndexName='PaperIdIndex',
        KeyConditionExpression=Key('GSI3PK').eq(f"PAPER#{arxiv_id}")
    )
    format_output("get_paper", {"arxiv_id": arxiv_id}, response.get('Items', []), start_time)

def query_daterange(table, category, start_date, end_date):
    start_time = time.time()
    response = table.query(
        KeyConditionExpression=Key('PK').eq(f"CATEGORY#{category}") & 
                               Key('SK').between(start_date, end_date + "T23:59:59Z")
    )
    format_output("papers_in_daterange", {"category": category, "start_date": start_date, "end_date": end_date}, response.get('Items', []), start_time)

def query_keyword(table, keyword, limit):
    start_time = time.time()
    response = table.query(
        IndexName='KeywordIndex',
        KeyConditionExpression=Key('GSI2PK').eq(f"KEYWORD#{keyword}"),
        ScanIndexForward=False,
        Limit=limit
    )
    format_output("papers_by_keyword", {"keyword": keyword, "limit": limit}, response.get('Items', []), start_time)

def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='command', required=True)

    p_recent = subparsers.add_parser('recent')
    p_recent.add_argument('category')
    p_recent.add_argument('--limit', type=int, default=20)
    p_recent.add_argument('--table', required=True)
    p_recent.add_argument('--region', default='us-west-2')

    p_author = subparsers.add_parser('author')
    p_author.add_argument('author_name')
    p_author.add_argument('--table', required=True)
    p_author.add_argument('--region', default='us-west-2')

    p_get = subparsers.add_parser('get')
    p_get.add_argument('arxiv_id')
    p_get.add_argument('--table', required=True)
    p_get.add_argument('--region', default='us-west-2')

    p_date = subparsers.add_parser('daterange')
    p_date.add_argument('category')
    p_date.add_argument('start_date')
    p_date.add_argument('end_date')
    p_date.add_argument('--table', required=True)
    p_date.add_argument('--region', default='us-west-2')

    p_kw = subparsers.add_parser('keyword')
    p_kw.add_argument('keyword')
    p_kw.add_argument('--limit', type=int, default=20)
    p_kw.add_argument('--table', required=True)
    p_kw.add_argument('--region', default='us-west-2')

    args = parser.parse_args()
    dynamodb = boto3.resource('dynamodb', region_name=args.region)
    table = dynamodb.Table(args.table)

    if args.command == 'recent':
        query_recent(table, args.category, args.limit)
    elif args.command == 'author':
        query_author(table, args.author_name)
    elif args.command == 'get':
        query_get(table, args.arxiv_id)
    elif args.command == 'daterange':
        query_daterange(table, args.category, args.start_date, args.end_date)
    elif args.command == 'keyword':
        query_keyword(table, args.keyword, args.limit)

if __name__ == "__main__":
    main()
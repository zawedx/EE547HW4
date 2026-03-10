import sys
import json
import argparse
import boto3
import re
from collections import Counter
from stopwords import STOPWORDS

def extract_keywords(abstract):
    if not abstract:
        return []
    words = re.findall(r'[a-z0-9]+', abstract.lower())
    valid_words = [w for w in words if w not in STOPWORDS and len(w) > 2]
    most_common = Counter(valid_words).most_common(10)
    return [word for word, count in most_common]

def create_table_if_not_exists(dynamodb, table_name):
    existing_tables = [t.name for t in dynamodb.tables.all()]
    if table_name in existing_tables:
        print(f"Table '{table_name}' already exists. Skipping creation.")
        return dynamodb.Table(table_name)

    print(f"Creating DynamoDB table: {table_name}")
    print("Creating GSIs: AuthorIndex, KeywordIndex, PaperIdIndex...")
    
    table = dynamodb.create_table(
        TableName=table_name,
        KeySchema=[
            {'AttributeName': 'PK', 'KeyType': 'HASH'},
            {'AttributeName': 'SK', 'KeyType': 'RANGE'}
        ],
        AttributeDefinitions=[
            {'AttributeName': 'PK', 'AttributeType': 'S'},
            {'AttributeName': 'SK', 'AttributeType': 'S'},
            {'AttributeName': 'GSI1PK', 'AttributeType': 'S'},
            {'AttributeName': 'GSI1SK', 'AttributeType': 'S'},
            {'AttributeName': 'GSI2PK', 'AttributeType': 'S'},
            {'AttributeName': 'GSI2SK', 'AttributeType': 'S'},
            {'AttributeName': 'GSI3PK', 'AttributeType': 'S'},
            {'AttributeName': 'GSI3SK', 'AttributeType': 'S'}
        ],
        GlobalSecondaryIndexes=[
            {
                'IndexName': 'AuthorIndex',
                'KeySchema': [
                    {'AttributeName': 'GSI1PK', 'KeyType': 'HASH'},
                    {'AttributeName': 'GSI1SK', 'KeyType': 'RANGE'}
                ],
                'Projection': {'ProjectionType': 'ALL'},
                'ProvisionedThroughput': {'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
            },
            {
                'IndexName': 'KeywordIndex',
                'KeySchema': [
                    {'AttributeName': 'GSI2PK', 'KeyType': 'HASH'},
                    {'AttributeName': 'GSI2SK', 'KeyType': 'RANGE'}
                ],
                'Projection': {'ProjectionType': 'ALL'},
                'ProvisionedThroughput': {'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
            },
            {
                'IndexName': 'PaperIdIndex',
                'KeySchema': [
                    {'AttributeName': 'GSI3PK', 'KeyType': 'HASH'},
                    {'AttributeName': 'GSI3SK', 'KeyType': 'RANGE'}
                ],
                'Projection': {'ProjectionType': 'ALL'},
                'ProvisionedThroughput': {'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
            }
        ],
        ProvisionedThroughput={'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
    )
    
    table.meta.client.get_waiter('table_exists').wait(TableName=table_name)
    print("Table created successfully.")
    return table

def load_data(papers_path, table):
    print(f"Loading papers from {papers_path}...")
    print("Extracting keywords from abstracts...")
    
    with open(papers_path, 'r', encoding='utf-8') as f:
        papers = json.load(f)

    stats = {
        "papers": len(papers),
        "total_items": 0,
        "category_items": 0,
        "author_items": 0,
        "keyword_items": 0,
        "paper_id_items": 0
    }

    with table.batch_writer() as batch:
        for p in papers:
            arxiv_id = p.get('arxiv_id')
            pub_date = p.get('published', '')
            base_sk = f"{pub_date}#{arxiv_id}"
            
            keywords = extract_keywords(p.get('abstract', ''))
            
            base_item = {
                "arxiv_id": arxiv_id,
                "title": p.get('title'),
                "authors": p.get('authors', []),
                "abstract": p.get('abstract'),
                "categories": p.get('categories', []),
                "keywords": keywords,
                "published": pub_date
            }
            
            for cat in p.get('categories', []):
                item = base_item.copy()
                item['PK'] = f"CATEGORY#{cat}"
                item['SK'] = base_sk
                batch.put_item(Item=item)
                stats['category_items'] += 1
                stats['total_items'] += 1
                
            for author in p.get('authors', []):
                item = base_item.copy()
                item['PK'] = f"AUTH_DUMMY#{author}#{arxiv_id}"
                item['SK'] = base_sk
                item['GSI1PK'] = f"AUTHOR#{author}"
                item['GSI1SK'] = base_sk
                batch.put_item(Item=item)
                stats['author_items'] += 1
                stats['total_items'] += 1
                
            for kw in keywords:
                item = base_item.copy()
                item['PK'] = f"KW_DUMMY#{kw}#{arxiv_id}"
                item['SK'] = base_sk
                item['GSI2PK'] = f"KEYWORD#{kw}"
                item['GSI2SK'] = base_sk
                batch.put_item(Item=item)
                stats['keyword_items'] += 1
                stats['total_items'] += 1
                
            item = base_item.copy()
            item['PK'] = f"ID_DUMMY#{arxiv_id}"
            item['SK'] = base_sk
            item['GSI3PK'] = f"PAPER#{arxiv_id}"
            item['GSI3SK'] = f"PAPER#{arxiv_id}"
            batch.put_item(Item=item)
            stats['paper_id_items'] += 1
            stats['total_items'] += 1

    factor = stats['total_items'] / stats['papers'] if stats['papers'] > 0 else 0
    print(f"Loaded {stats['papers']} papers")
    print(f"Created {stats['total_items']:,} DynamoDB items (denormalized)")
    print(f"Denormalization factor: {factor:.1f}x\n")
    print("Storage breakdown:")
    print(f"  - Category items: {stats['category_items']} ({stats['category_items']/stats['papers']:.1f} per paper avg)")
    print(f"  - Author items: {stats['author_items']} ({stats['author_items']/stats['papers']:.1f} per paper avg)")
    print(f"  - Keyword items: {stats['keyword_items']} ({stats['keyword_items']/stats['papers']:.1f} per paper avg)")
    print(f"  - Paper ID items: {stats['paper_id_items']} ({stats['paper_id_items']/stats['papers']:.1f} per paper)")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("papers_json")
    parser.add_argument("table_name")
    parser.add_argument("--region", default="us-west-2")
    args = parser.parse_args()

    dynamodb = boto3.resource('dynamodb', region_name=args.region)
    table = create_table_if_not_exists(dynamodb, args.table_name)
    load_data(args.papers_json, table)

if __name__ == "__main__":
    main()
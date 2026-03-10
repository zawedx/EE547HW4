### Q2

1. **Schema Design Decisions:** CATEGORY#{category} was chosen as the primary key (PK) because it's the most common aggregation dimension for academic papers. Three GSIs (Author, Keyword, ID) were created to meet the precise retrieval requirements of different dimensions. The trade-off was trading storage space for query time.

2. **Denormalization Analysis:** Denormalization factor: 20.4x. Keywords caused the biggest data bloat (because extracting 10 keywords per article resulted in 10 additional items).

3. **Query Limitations:** Global aggregation queries (such as "most cited articles globally" or "count the total number of articles by a specific author") cannot be executed efficiently. In DynamoDB, performing COUNT or SUM operations requires scanning all data and performing calculations in memory, which is extremely expensive and inefficient.

4. **When to Use DynamoDB:** When the access patterns are very clear, the business requires millisecond-level low latency, and the data volume is so large that ordinary relational databases cannot easily scale (e.g., e-commerce shopping carts, high-frequency log records). However, if the business requires frequent table joins and flexible analytical reporting, then we should choose PostgreSQL.
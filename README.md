### Q1

1. **Schema Decisions:** I chose natural keys (such as `line_name` and `stop_name`) because they perfectly match the original CSV data stream, avoiding ID mapping and join queries during import.

2. **Constraints:** I added a `CHECK` constraint to ensure that the number of passengers and time offsets are not negative, and used a `UNIQUE` constraint to ensure that the sequence number of each station on the same route is absolutely unique.

3. **Complex Query:** Q4 (Complete Route Reconstruction) is the most complex because it requires simultaneously joining three different tables (`stop_events`, `trips`, `line_stops`) and relying on the business logic sequence of another table to ensure strict sorting.

4. **Foreign Keys:** Foreign key mechanisms perfectly prevent the generation of "ghost data," such as preventing the insertion of a departure schedule belonging to a non-existent bus route (`line_name`) into the database.

5. **When Relational:** Relational databases are well-suited for the public transportation sector because the entities (routes, stations, services) in this domain have highly structured, tightly networked dependencies, and there is a high demand for summary statistics (aggregate queries).

### Q2

1. **Schema Design Decisions:** CATEGORY#{category} was chosen as the primary key (PK) because it's the most common aggregation dimension for academic papers. Three GSIs (Author, Keyword, ID) were created to meet the precise retrieval requirements of different dimensions. The trade-off was trading storage space for query time.

2. **Denormalization Analysis:** Denormalization factor: 20.4x. Keywords caused the biggest data bloat (because extracting 10 keywords per article resulted in 10 additional items).

3. **Query Limitations:** Global aggregation queries (such as "most cited articles globally" or "count the total number of articles by a specific author") cannot be executed efficiently. In DynamoDB, performing COUNT or SUM operations requires scanning all data and performing calculations in memory, which is extremely expensive and inefficient.

4. **When to Use DynamoDB:** When the access patterns are very clear, the business requires millisecond-level low latency, and the data volume is so large that ordinary relational databases cannot easily scale (e.g., e-commerce shopping carts, high-frequency log records). However, if the business requires frequent table joins and flexible analytical reporting, then we should choose PostgreSQL.
# Data directory

| Path | Contents |
|------|----------|
| `ddl/Table-Script.sql` | Source enterprise DDL (MS SQL / Snowflake style) |
| `seed/Product.csv` | Product master seed data |
| `seed/Inventory.csv` | Inventory fact seed data |
| `seed/Customer-Data.csv` | Customer seed data |

Load into PostgreSQL with:

```bash
python scripts/init_db.py
```

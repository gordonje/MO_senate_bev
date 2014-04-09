MO_senate_bev
=============

This is a web scraping and data presentation project for one of my journalism classes. The goal is to create a bird's-eye-view of the Missouri State Senate.

This is the query that gets me the date and description of the last action for each bill, so I don't have to actually collect these via the scraper and figure out how to keep it up to date in the db_catchup script:
```sql
select a.bill_year, a.bill_type, a.bill_number, a.action_date, a.action_desc
from bills_actions as a
join 
(select bill_year, bill_type, bill_number, max(rowid) as last
from bills_actions
group by bill_year, bill_type, bill_number) as b
on a.rowid = b.last
```

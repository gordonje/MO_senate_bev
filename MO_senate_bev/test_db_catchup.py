import sqlite3
from datetime import date, timedelta

conn = sqlite3.connect('MO_senate.sqlite')
conn.text_factory = lambda x: unicode(x, 'utf-8', 'ignore')
c = conn.cursor()

now = date.today()

bills_to_delete = []

for i in c.execute('''SELECT bill_type, bill_number FROM bills ORDER BY url_id DESC LIMIT 3'''):
	bills_to_delete.append([str(i[0]), str(i[1])])

c.executemany('''DELETE FROM bills WHERE bill_type = ? AND bill_number = ?''', bills_to_delete)
conn.commit()

c.executemany('''DELETE FROM bills_actions WHERE bill_type = ? AND bill_number = ?''', bills_to_delete)
conn.commit()

c.executemany('''DELETE FROM bills_cosponsors WHERE bill_type = ? AND bill_number = ?''', bills_to_delete)
conn.commit()

c.executemany('''DELETE FROM bills_topics WHERE bill_type = ? AND bill_number = ?''', bills_to_delete)
conn.commit()

print 'These bills (and their associated records) where deleted: '

for i in bills_to_delete:
	print '  ' + i[0] + ' ' + i[1]

three_days_ago = str(now - timedelta(days=3))

count_actions_deleted = 0

for i in c.execute('''SELECT count(*) FROM bills_actions WHERE date(action_date) > date(?)''', [three_days_ago]):
	count_actions_deleted += int(i[0])

c.execute('''DELETE FROM bills_actions WHERE action_date > ?''', [three_days_ago])
conn.commit()

print 'Also deleted all bills_actions after ' + three_days_ago + ' (' + str(count_actions_deleted) + ' records).'

conn.close()
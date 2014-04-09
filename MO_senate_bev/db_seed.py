from datetime import datetime
import sqlite3
from os import path, rename
import requests
import scrapers
from time import sleep
from sys import stdout

start_time = datetime.now()
print "Started at " + str(start_time) + "."

########## Connecting to / setting up the database ##########

# if there's already a database, archive it
if path.exists('MO_senate.sqlite'):
	print "Archiving old database..."
	time_str = str(start_time.date()) + "_" + str(start_time.hour) + str(start_time.minute) + str(start_time.second)
	rename('MO_senate.sqlite', 'Archive/MO_senate_' + time_str + '.sqlite')

conn = sqlite3.connect('MO_senate.sqlite')
conn.text_factory = lambda x: unicode(x, 'utf-8', 'ignore')
c = conn.cursor()

print "Creating database..."

c.execute('''CREATE TABLE bills (
	bill_year INTEGER NOT NULL,
	bill_type VARCHAR(4) NOT NULL,
	bill_number INTEGER NOT NULL,
	url_id INTEGER NOT NULL,
	brief_desc VARCHAR(255),
	sponsor VARCHAR(20),
	lr_number VARCHAR(50),
	committee VARCHAR(20),
	-- Decided not to collect last action on the bill records because I figured out how to query the database for it, which is easier than figuring out how to keep it up-to-date
	-- last_action_date DATE,
	-- last_action_desc TEXT,
	effective_date VARCHAR(24),
	summary TEXT,
	PRIMARY KEY (bill_year, bill_type, bill_number)
	)''')

c.execute('''CREATE TABLE bills_actions (
	bill_year INTEGER NOT NULL,
	bill_type VARCHAR(4) NOT NULL,
	bill_number INTEGER NOT NULL,
	action_date DATE NOT NULL,
	action_desc TEXT,
	FOREIGN KEY(bill_year, bill_type, bill_number) REFERENCES bills (bill_year, bill_type, bill_number)
	)''')

c.execute('''CREATE TABLE bills_cosponsors (
	bill_year INTEGER NOT NULL,
	bill_type VARCHAR(4) NOT NULL,
	bill_number INTEGER NOT NULL,
	cosponsor_name VARCHAR(20) NOT NULL,
	cosponsor_district INTEGER NOT NULL,
	FOREIGN KEY(bill_year, bill_type, bill_number) REFERENCES bills (bill_year, bill_type, bill_number)
	)''')

c.execute('''CREATE TABLE bills_topics (
	bill_year INTEGER NOT NULL,
	bill_type VARCHAR(4) NOT NULL,
	bill_number INTEGER NOT NULL,
	topic VARCHAR(255),
	FOREIGN KEY(bill_year, bill_type, bill_number) REFERENCES bills (bill_year, bill_type, bill_number)
	)''')

conn.commit()

########## Gathering bill ids ##########

session = requests.Session()
session.headers.update({"Connection": "keep-alive"})

print "Getting bills..."

current_year = start_time.year

all_bills = []

for i in scrapers.get_bills(current_year, session):
	all_bills.append(i)

# if this is an even year, then we need to get all of the previous year's bills as well because the sessions are every two years
if current_year % 2 == 0:
	for i in scrapers.get_bills(current_year - 1, session):
		all_bills.append(i)

totalBills = len(all_bills)
currentBillCount = 0

print "There are " + str(totalBills) + " bills to download (Approximately " + str((totalBills * 18)/60) + " minutes to complete)."

########## Getting bill info ##########

for i in all_bills:

	sleep(5)

	bill_info = scrapers.get_bill_info(i, session)

	bill_output= [
		bill_info['bill_year'],
		bill_info['bill_type'],
		bill_info['bill_number'],
		bill_info['url_id'],
		bill_info['brief_desc'],
		bill_info['sponsor'],
		bill_info['lr_number'],
		bill_info['committee'],
		bill_info['effective_date'],
		bill_info['summary']
## Decided not to collect last action on the bill records because I figured out how to query the database for it, which is easier than figuring out how to keep it up-to-date
		# bill_info['last_action_date'],
		# bill_info['last_action_desc'],
	]

	c.execute('INSERT INTO bills VALUES (?,?,?,?,?,?,?,?,?,?)', bill_output)
	conn.commit()

########## Getting actions ##########

	sleep(5)

	actions_output = scrapers.get_all_bill_actions(i, session)

	c.executemany('INSERT INTO bills_actions VALUES (?,?,?,?,?)', actions_output)
	conn.commit()

########## Getting cosponsors ##########

	if bill_info['has_Cosponsors']:

		sleep(3)

		cosponsors_output = scrapers.get_bill_cosponsors(i, session)

		c.executemany('INSERT INTO bills_cosponsors VALUES (?,?,?,?,?)', cosponsors_output)
		conn.commit()

########## Keeping track of where we are ##########

	currentBillCount += 1

	if currentBillCount < totalBills:
		stdout.write(" " + i['bill_type'] + " " + i['bill_number'] + " completed (" + str(currentBillCount) + " of " + str(totalBills) + ").\r")
		stdout.flush()
	else:
		print "All bills downloaded.                 "

########## Getting bill topics ##########

print "Getting topics..."

sleep(3)

topics_output = scrapers.get_bill_topics(current_year, session)

# if this is an even year, then we need to get all of the previous year's bills as well because the sessions are every two years
if current_year % 2 == 0:

	sleep(3)

	for i in scrapers.get_bill_topics(current_year - 1, session):
		topics_output.append(i)
	
c.executemany('INSERT INTO bills_topics VALUES (?,?,?,?)', topics_output)
conn.commit()

########## Finishing ##########

conn.close()

duration = datetime.now() - start_time

print "Finished (ran for " + str(duration) + ")."
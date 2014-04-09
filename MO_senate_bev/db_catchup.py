from datetime import datetime
from time import sleep
import requests
import scrapers
from bs4 import BeautifulSoup
import re
import sqlite3

start_time = datetime.now()
print "Started at " + str(start_time) + "."

conn = sqlite3.connect('MO_senate.sqlite')
conn.text_factory = lambda x: unicode(x, 'utf-8', 'ignore')
c = conn.cursor()

session = requests.Session()
session.headers.update({"Connection": "keep-alive"})

current_year = start_time.year

####### Getting data from new bills, if there are any #######

print "Checking for new bills..."

bills_from_db = []

for i in c.execute('SELECT url_id FROM bills'):
	url_id = int(i[0])
	bills_from_db.append(url_id)

all_bills = scrapers.get_bills(current_year, session)

# if this is an even year, then we need to get all of the previous year's bills as well because the sessions are every two years
if current_year % 2 == 0:
	for i in scrapers.get_bills(current_year - 1, session):
		all_bills.append(i)

new_bills = []

for i in all_bills:
	if int(i['url_id']) not in bills_from_db:
		new_bills.append(i)

# count_new_bills = len(new_bills)

if len(new_bills) > 0:
	print str(len(new_bills)) + " new bills found."
	for i in new_bills:
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

		sleep(5)

		actions_output = scrapers.get_all_bill_actions(i, session)

		c.executemany('INSERT INTO bills_actions VALUES (?,?,?,?,?)', actions_output)
		conn.commit()

		if bill_info['has_Cosponsors']:

			sleep(3)

			cosponsors_output = scrapers.get_bill_cosponsors(i, session)

			c.executemany('INSERT INTO bills_cosponsors VALUES (?,?,?,?,?)', cosponsors_output)
			conn.commit()

########## Rebuild the topics table ##########

	print "Rebuilding topics table..."

	sleep(3)

	topics_output = scrapers.get_bill_topics(current_year, session)

	# if this is an even year, then we need to get all of the previous year's bills as well because the sessions are every two years
	if current_year % 2 == 0:

		sleep(3)

		for i in scrapers.get_bill_topics(current_year - 1, session):
			topics_output.append(i)
		
	c.executemany('INSERT INTO bills_topics VALUES (?,?,?,?)', topics_output)
	conn.commit()

else:
	print "No new bills."

####### Getting new actions for existing bills, if there are any #######

print "Checking for new actions on old bills..."

date_from_db = ''

for i in c.execute('SELECT action_date FROM bills_actions ORDER BY action_date DESC LIMIT 1'):
	date_from_db = date_from_db + i[0]

date_from_db = datetime(int(date_from_db.split('-')[0]), int(date_from_db.split('-')[1]), int(date_from_db.split('-')[2]))

response = session.get('http://www.senate.mo.gov/' + str(current_year).lstrip("20") + 'info/BTS_Web/ActionDates.aspx?SessionType=R')
soup = BeautifulSoup(response.content)

dates_to_request = []

## Thought I need to check what the current date was listed on this page. Turns out I don't (I think)
# current_date_string = soup.find('a', id = 'hlCurrentAction').text.lstrip("Most Current Action - ")
# current_date = datetime(int(current_date_string.split('/')[2]), int(current_date_string.split('/')[0]), int(current_date_string.split('/')[1]))

# if current_date > date_from_db:
# 	dates_to_request.append(current_date_string)

action_dates_dl = soup.find('table', id = 'dlActionDates')

for td in action_dates_dl.findAll('a'):
	action_date_string = td.text
	action_date = datetime(int(action_date_string.split('/')[2]), int(action_date_string.split('/')[0]), int(action_date_string.split('/')[1]))
	if action_date > date_from_db:
		dates_to_request.append(action_date_string)

if len(dates_to_request) > 0:

	print str(len(dates_to_request)) + ' days to check...' 

	for i in dates_to_request:

		sleep(5)

		payload = {'SessionType': 'R', 'ActionDate': i}
		response = session.get('http://www.senate.mo.gov/' + str(current_year).lstrip("20") + 'info/BTS_Web/Daily.aspx', params = payload)

		soup = BeautifulSoup(response.content)

		actions_to_save = []

		for dt in soup.findAll('dt'):
			bill_link = dt.find('a')
			# if this is one of the bills we already have in the database (not a new one for which we just collected all the information)...
			if int(re.search('\d+', bill_link['href']).group()) in bills_from_db:
				# then we need to grab the actions for it...
				bill_type_number = dt.text.encode('utf-8').split(' - ', 1)[0]
				bill_type = bill_type_number.split(' ')[0]
				bill_number = bill_type_number.split(' ')[1]

				for dd in dt.findNextSiblings('dd'):
					# I have to do this sort of weird thing because <dd> tags sometimes are enclosed in adjacent tags
					desc_text = dd.text.lstrip(i + ' --  ').split(i + ' -- ')
					for j in desc_text:
						action_to_save = [current_year, bill_type, bill_number, i.split("/")[2] + '-' + i.split("/")[0] + '-' + i.split("/")[1], j]
						actions_to_save.append(action_to_save)

		c.executemany('INSERT INTO bills_actions VALUES (?,?,?,?,?)', actions_to_save)
		conn.commit()
else:
	print "Already up-to-date."

########## Finishing ##########

conn.close()

duration = datetime.now() - start_time

print "Finished (ran for " + str(duration) + ")."
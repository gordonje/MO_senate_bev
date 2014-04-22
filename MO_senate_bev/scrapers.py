import re
from datetime import date, timedelta
from bs4 import BeautifulSoup


def get_bills (year, requests_session):

####### Returns a list of bills, each of which is a dict with a bill_type, bill_number, url_id and year #######

	bills = []

	bill_list_url = 'http://www.senate.mo.gov/' + str(year).lstrip("20") + 'info/BTS_Web/BillList.aspx?SessionType=R'

	response = requests_session.get(bill_list_url)
	soup = BeautifulSoup(response.content)

	bill_list = soup.findAll('table', id='Table2')

	for i in bill_list:

		bill = {}

		bill_link = i.find("a", id = re.compile("dgBillList__ctl\d+_hlBillNum"))

		bill['bill_type'] = bill_link.text.split(" ")[0]
		bill['bill_number'] = bill_link.text.split(" ")[1]
		bill['url_id'] = re.search('\d+', bill_link["href"]).group()
		bill['bill_year'] = year
		
		bills.append(bill)

	return bills


def get_bill_info (bill, requests_session):

####### Returns a bill, represented as a dict, with all info, ready to save to the database #######

	payload = {'SessionType': 'R', 'BillID': str(bill['url_id'])}
	response = requests_session.get('http://www.senate.mo.gov/' + str(bill['bill_year']).lstrip("20") + 'info/BTS_Web/Bill.aspx', params = payload)

	soup = BeautifulSoup(response.content)

	bill['brief_desc'] = soup.find("span", id = "lblBriefDesc").text.encode('utf-8')
	bill['sponsor'] = soup.find("a", id = "hlSponsor").text.encode('utf-8')
	bill['lr_number'] = soup.find("span", id = "lblLRNum").text.encode('utf-8')
	bill['committee'] = soup.find("a", id = "hlCommittee").text.encode('utf-8')
	bill['effective_date'] = soup.find("span", id = "lblEffDate").text.encode('utf-8')
	bill['summary'] = soup.find("span", id = "lblSummary").text.encode('utf-8')
	## Decided not to collect last action on the bill records because I figured out how to query the database for it, which is easier than figuring out how to keep it up-to-date
	# bill['last_action_desc'] = soup.find("span", id = "lblLastAction").text.split(" - ", 1)[1]
	# last_action_date = soup.find("span", id = "lblLastAction").text.split(" - ", 1)[0]
	# bill['last_action_date'] = last_action_date.split("/")[2] + '-' + last_action_date.split("/")[0] + '-' + last_action_date.split("/")[1]

	bill['has_Cosponsors'] = False
	cosponsors_link = soup.find("a", id = "hlCoSponsors")
	if cosponsors_link.text == "Co-Sponsor(s)":
		bill['has_Cosponsors'] = True

	return bill


def get_all_bill_actions (bill, requests_session):

####### Returns a list of the bill's actions, each of which is represented as a list, ready to save to the database #######

	payload = {'SessionType': 'R', 'BillID': str(bill['url_id'])}
	response = requests_session.get('http://www.senate.mo.gov/' + str(bill['bill_year']).lstrip("20") + 'info/BTS_Web/Actions.aspx', params = payload)

	soup = BeautifulSoup(response.content)

	div = soup.find("div")

	actions = []

	for tr in div.findAll("tr"):

		date_td = tr.findChild('td')
		action_date = date(int(date_td.text.split('/')[2]), int(date_td.text.split('/')[0]), int(date_td.text.split('/')[1]))

		# excluding actions that haven't yet to occur

		tomorrow = date.today() + timedelta(days=1)

		if action_date < tomorrow:

			description = date_td.findNextSibling('td')

			action = [
				bill['bill_year'], 
				bill['bill_type'], 
				bill['bill_number'],
				str(action_date),
				description.text.encode('utf-8')
				]

			actions.append(action)

	return actions


def get_bill_cosponsors (bill, requests_session):

####### Returns a list of the bill's cosponsors, each of which is represented as a list, ready to save to the database #######

	payload = {'SessionType': 'R', 'BillID': str(bill['url_id'])}
	response = requests_session.get('http://www.senate.mo.gov/' + str(bill['bill_year']).lstrip("20") + 'info/BTS_Web/CoSponsors.aspx', params = payload)

	cosponsors = []

	soup = BeautifulSoup(response.content)

	cosponsors_table = soup.find("table", id = "dgCoSponsors")

	for a in cosponsors_table.findAll('a'):
		name = a.text.split(", ")[0]
		district = a.text.split(", ")[1].lstrip("District ")

		cosponsor = [bill['bill_year'], bill['bill_type'], bill['bill_number'], name, district]

		cosponsors.append(cosponsor)

	return cosponsors


def get_bill_topics (year, requests_session):

####### Gets the topics applied to each bill for the given year, ready to save to the database #######

	response = requests_session.get('http://www.senate.mo.gov/' + str(year).lstrip("20") + 'info/BTS_Web/Keywords.aspx?SessionType=R')

	soup = BeautifulSoup(response.content)

	bills_topics = []
	
	for h3 in soup.findAll('h3'):

		bill_count = re.search(' \(.+', h3.text).group()
		topic  = h3.text.rstrip(bill_count)

		bills_on_topic = h3.findNextSibling('span')


		for b in bills_on_topic.findAll('b'):
			bill_topic = [
				year,
				b.text.split(" ")[0],
				b.text.split(" ")[1],
				topic
				]
			bills_topics.append(bill_topic)

	return bills_topics

def get_senators (year, requests_session):

####### Gets info about the given years senators, including the name, party and district #######

	response = requests_session.get('http://www.senate.mo.gov/' + str(year).lstrip("20") + 'info/senateroster.htm')

	soup = BeautifulSoup(response.content)

	outer = soup.find('td', attrs = {'valign':"top", 'width': "49%"})
	
	inner = outer.find('table', attrs = {'border':"0", 'width':"90%"})

	senators = []

	for tr in inner.findAll('tr')[1:]:

		raw_senator = []

		for td in tr.findAll('td')[:2]:

			raw_senator.append(td.text.strip())

		name = raw_senator.pop(0)

		if name == 'Vacant':
			pass
		else:
			senator = [year]

			senator.append(name.split(" ")[0])
			senator.append(name.split(" ")[1])

			party_district = raw_senator.pop(-1).split('-')

			senator.append(party_district[0])
			senator.append(int(party_district[1]))

			senators.append(senator)

	return senators
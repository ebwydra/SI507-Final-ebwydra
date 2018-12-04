import requests
from bs4 import BeautifulSoup
import json
import csv
import sqlite3 as sqlite
from secrets import *
import plotly
import plotly.plotly as py

plotly.tools.set_credentials_file(username=PLOTLY_USERNAME, api_key=PLOTLY_API_KEY)

DBNAME = 'law.db'
STATESCSV = 'state_table.csv'
CACHE_FNAME = "cache.json"

try:
    f = open(CACHE_FNAME, 'r')
    f_contents = f.read()
    f.close()
    CACHE_DICTION = json.loads(f_contents)
except:
    CACHE_DICTION = {}

''' Functions that get data from the internet '''

def get_courts_data():
    list_of_courts = []

    url = 'https://en.wikipedia.org/wiki/List_of_United_States_district_and_territorial_courts'

    if url in CACHE_DICTION:
        # print("Getting cached data")
        html = CACHE_DICTION[url]
    else:
        # print("Getting new data")
        html = requests.get(url).text
        CACHE_DICTION[url] = html
        f = open(CACHE_FNAME, 'w')
        f.write(json.dumps(CACHE_DICTION))
        f.close

    soup = BeautifulSoup(html, 'html.parser')
    table = soup.find("table", class_="wikitable sortable")
    row_set = table.find_all("tr")

    for row in row_set[1:]:
        td_set = row.find_all("td")

        name_list = td_set[0].text.split()
        if name_list[-1] == "Columbia":
            state = "District of Columbia"
        elif name_list[-2] != "of":
            state = "{} {}".format(name_list[-2], name_list[-1])
        else:
            state = name_list[-1]

        name = td_set[0].text.strip()
        cite = td_set[1].text.strip()
        appeals = td_set[2].text.strip()
        estd = td_set[3].text.strip()
        judges = td_set[4].text.strip()

        tup = (state,name,cite,appeals,estd,judges)
        list_of_courts.append(tup)

    return list_of_courts

def get_cap_data():

    url = "https://api.case.law/v1/cases/?full_case=true&jurisdiction=us&decision_date_min=2016-01-01"
    page = 0
    list_of_case_tups = []

    while page < 10: # I want the first 10 pages
        if url in CACHE_DICTION:
            # print("Getting cached data")
            resp_dict = CACHE_DICTION[url]
        else:
            # print("Getting new data")
            resp = requests.get(url, headers = {'Authorization': "Token " + CAPAPI_KEY})
            resp_dict = json.loads(resp.text)
            CACHE_DICTION[url] = resp_dict
            f = open(CACHE_FNAME, 'w')
            f.write(json.dumps(CACHE_DICTION))
            f.close

        url = resp_dict['next']
        page += 1

        for case in resp_dict['results']: # there are 100 in a page
            name = case['name']
            name_abbr = case['name_abbreviation']
            date = case['decision_date']
            court = case['court']['name_abbreviation']
            text = ""
            for opinion in case['casebody']['data']['opinions']:
                text += opinion['text']

            case_tup = (name, name_abbr, date, court, text)
            list_of_case_tups.append(case_tup)

    return list_of_case_tups

''' Create database '''

def create_db():

    conn = sqlite.connect(DBNAME)
    cur = conn.cursor()

    ''' Drop existing tables '''

    statement = "DROP TABLE IF EXISTS Cases"
    cur.execute(statement)
    statement = "DROP TABLE IF EXISTS DistrictCourts"
    cur.execute(statement)
    # statement = "DROP TABLE IF EXISTS CircuitCourts"
    # cur.execute(statement)
    statement = "DROP TABLE IF EXISTS States"
    cur.execute(statement)

    conn.commit()

    ''' Create tables '''

    # Create States table
    statement = '''
    CREATE TABLE States (
    Id INTEGER PRIMARY KEY AUTOINCREMENT,
    Name TEXT,
    Abbr TEXT,
	AssocPress TEXT,
	CensusRegionName TEXT,
	CensusDivisionName TEXT,
	CircuitCourt TEXT
    );
    '''
    cur.execute(statement)

    # Create DistrictCourts table
    statement = '''
    CREATE TABLE DistrictCourts (
    Id INTEGER PRIMARY KEY AUTOINCREMENT,
    StateId INTEGER REFERENCES States(Id),
    CourtName TEXT,
    Citation TEXT,
    CircuitCourt TEXT,
    Established INTEGER,
    NumJudges INTEGER
    );
    '''
    cur.execute(statement)

    # Create Cases table
    statement = '''
    CREATE TABLE Cases (
    Id INTEGER PRIMARY KEY,
    Name TEXT,
    NameAbbr TEXT,
    DecisionDate INTEGER,
    CourtId INTEGER REFERENCES DistrictCourts(Id),
    CaseBody TEXT
    );
    '''
    cur.execute(statement)

    conn.commit()

    ''' Load data into tables '''

    # States table - from csv
    with open(STATESCSV, encoding = 'utf-8') as states_data:
        list_of_tuples = []

        csv_reader = csv.reader(states_data)
        for row in csv_reader:
            name = row[1]
            abbr = row[2]
            ap = row[10]
            region = row[13]
            division = row[15]
            circuit = row[16]
            tup = (name,abbr,ap,region,division,circuit)
            list_of_tuples.append(tup)

        for tup in list_of_tuples[1:]:
            statement = '''
            INSERT INTO States (Name, Abbr, AssocPress, CensusRegionName, CensusDivisionName, CircuitCourt)
            VALUES (?,?,?,?,?,?)
            '''
            cur.execute(statement, tup)
            conn.commit()

    # DistrictCourts table
    courts_list = get_courts_data() # list of tuples
    for court in courts_list:
        # Get State ID -- court[0]
        statement = '''
        SELECT Id
        FROM States
        WHERE Name LIKE \"{}\"
        '''.format(court[0])
        cur.execute(statement)
        result = cur.fetchone()
        try:
            id = result[0]
        except:
            id = None
        # print("{} {}".format(id, court[1]))
        court_l = list(court)
        court_l.append(id)
        court_l.remove(court_l[0]) # get rid of state name
        circuit = court_l[2].strip("abcdefghijklmnopqrstuvwxyz")
        court_l.remove(court_l[2])
        court_l.append(circuit)
        new_tup = tuple(court_l)
        # print(new_tup)

        statement = '''
        INSERT INTO DistrictCourts (CourtName, Citation, Established, NumJudges, StateId, CircuitCourt)
        VALUES (?, ?, ?, ?, ?, ?)
        '''
        cur.execute(statement, new_tup)
        conn.commit()

    statement = '''
    UPDATE DistrictCourts
    SET StateId = 51
    WHERE CourtName LIKE "District of Columbia"
    '''
    cur.execute(statement)
    conn.commit()

    # Cases table
    cases_list = get_cap_data()
    for case in cases_list:
        # Get Court ID - (name, name_abbr, date, court, text) - case[3]
        statement = '''
        SELECT Id
        FROM DistrictCourts
        WHERE Citation LIKE \"{}\"
        '''.format(case[3])
        cur.execute(statement)
        result = cur.fetchone()
        try:
            id = result[0]
        except:
            id = None
        case_l = list(case)
        case_l.append(id)
        case_l.remove(case_l[3])
        new_tup = tuple(case_l)

        statement = '''
        INSERT INTO Cases (Name, NameAbbr, DecisionDate, CaseBody, CourtId)
        VALUES (?, ?, ?, ?, ?)
        '''
        cur.execute(statement, new_tup)
        conn.commit()

''' Functions that access and process data from the database '''

def get_cases_by_state():
    conn = sqlite.connect(DBNAME)
    cur = conn.cursor()

    # Get total # of cases in all states
    statement = '''
    SELECT COUNT(*)
    FROM Cases
    JOIN DistrictCourts
    ON Cases.CourtId = DistrictCourts.Id
    JOIN States
    ON DistrictCourts.StateId = States.Id
    '''
    results = cur.execute(statement)
    n_tup = results.fetchone()
    n = n_tup[0] # n is an int representing the total # of district court cases in db

    statement = '''
    SELECT States.Abbr, States.Name, COUNT(*)
    FROM Cases
    JOIN DistrictCourts
    ON Cases.CourtId = DistrictCourts.Id
    JOIN States
    ON DistrictCourts.StateId = States.Id
    GROUP BY States.Abbr
    '''
    results = cur.execute(statement)
    result_list = results.fetchall() # list of tuples

    return_list = []

    for result_tup in result_list:
        state_abbr = result_tup[0]
        state_name = result_tup[1]
        count = result_tup[2]
        percent = count/n
        new_tup = (state_abbr, state_name, count, percent)
        return_list.append(new_tup)

    return return_list # list of tuples: (state_abbr, state_name, count, percent)

def get_percent_by_state_containing(word):
    conn = sqlite.connect(DBNAME)
    cur = conn.cursor()

    # get # of cases in each state
    statement = '''
    SELECT States.Abbr, COUNT(*)
    FROM Cases
    JOIN DistrictCourts
    ON Cases.CourtId = DistrictCourts.Id
    JOIN States
    ON DistrictCourts.StateId = States.Id
    GROUP BY States.Abbr
    '''
    results = cur.execute(statement)
    state_list = results.fetchall() # list of tuples
    total_dict = {}
    for state in state_list:
        total_dict[state[0]] = state[1] # keys are state abbreviations, values are total # of cases

    # get # of cases containing word in each state
    statement = '''
    SELECT States.Abbr, COUNT(*)
    FROM Cases
    JOIN DistrictCourts
    ON Cases.CourtId = DistrictCourts.Id
    JOIN States
    ON DistrictCourts.StateId = States.Id
    WHERE Cases.CaseBody LIKE \"%{}%\"
    GROUP BY States.Abbr
    '''.format(word)
    results = cur.execute(statement)
    case_matching_list = results.fetchall()

    case_matching_dict = {}
    for case in case_matching_list:
        case_matching_dict[case[0]] = case[1] # keys are state abbreviations, values are # of cases matching word

    result_dict = {}
    for state in list(total_dict.keys()):
        if state in case_matching_dict:
            result_dict[state] = case_matching_dict[state]/total_dict[state]
        else:
            result_dict[state] = 0

    return_list = []
    for state in list(result_dict.keys()):
        abbr = state
        percent = result_dict[state]
        tup = (abbr, percent)
        return_list.append(tup)

    return return_list # list of tuples: (abbr, percent)


'''
A table (https://www.plot.ly/python/table/) that displays all court cases containing a particular word or phrase (specified by the user), or matching other specified requirements such as court, state, year (also specified by the user).
'''

def get_list_of_cases_containing(word):
    conn = sqlite.connect(DBNAME)
    cur = conn.cursor()
    statement = '''
    SELECT States.Abbr, States.Name, Cases.Name, Cases.NameAbbr, DistrictCourts.CourtName, DistrictCourts.Citation
    FROM Cases
    JOIN DistrictCourts
    ON Cases.CourtId = DistrictCourts.Id
    JOIN States
    ON DistrictCourts.StateId = States.Id
    WHERE Cases.CaseBody LIKE \"%{}%\"
    ORDER BY States.Abbr
    '''.format(word)

    results = cur.execute(statement)
    result_list = results.fetchall()

    return result_list # list of tuples: (state abbr, state name, case name, case abbr, court name, court abbr)

'''
Line chart (https://www.plot.ly/python/line-charts/) displaying the frequency of one or more particular words or phrases (specified by the user) in the full text of cases from all courts over a period of time.
'''

def get_freq_by_time_for(list_of_words):
    conn = sqlite.connect(DBNAME)
    cur = conn.cursor()
    statement = '''
    SELECT DecisionDate, CaseBody
    FROM Cases
    '''
    results = cur.execute(statement)
    result_list = results.fetchall() # list of tuples representing every case: (date, full text)

    date_dictionary = {} # date_dictionary will have dates as keys, list of words all words from that day as values
    for result in result_list:
        if result[0] not in date_dictionary:
            date_dictionary[result[0]] = result[1].split()
        else:
            val = date_dictionary[result[0]]
            val += result[1].split() # append all the new words
            date_dictionary[result[0]] = val

    list_of_dicts = []

    for word in list_of_words:
        word_dict = {}
        for date in list(date_dictionary.keys()):
            count = 0
            for token in date_dictionary[date]:
                if token == word:
                    count += 1
            word_dict[date] = count/len(date_dictionary[date])
        list_of_dicts.append(word_dict)

    return list_of_dicts # list of dictionaries corresponding to each word where key is date and value is frequency of the word

''' Functions that display data '''

'''
A choropleth map (https://www.plot.ly/python/choropleth-maps/) of the United States that presents the number or percentage of district/territorial court cases from each state (that is, the sum of the count of cases in each of the districts comprising the state).

Helper function: get_cases_by_state() returns list of tuples: (state_abbr, state_name, count, percent)
'''

def make_map_of_cases(): # (state_abbr, state_name, count, percent)

    list_of_cases_by_state = get_cases_by_state()

    state_list = []
    z_list = []

    for state in list_of_cases_by_state:
        state_list.append(state[0])
        z_list.append(state[2])

    scl = [[0.0, 'rgb(242,240,247)'],[0.2, 'rgb(218,218,235)'],[0.4, 'rgb(188,189,220)'],[0.6, 'rgb(158,154,200)'],[0.8, 'rgb(117,107,177)'],[1.0, 'rgb(84,39,143)']]

    data = [ dict(
        type='choropleth',
        colorscale = scl,
        autocolorscale = False,
        locations = state_list,
        z = z_list,
        locationmode = 'USA-states',
        # text = df['text'],
        marker = dict(
            line = dict (
                color = 'rgb(255,255,255)',
                width = 2
            ) ),
        colorbar = dict(
            title = "Number of Cases")
        ) ]

    layout = dict(
        title = 'Number of U.S. District Court Cases by State',
        geo = dict(
            scope='usa',
            projection=dict( type='albers usa' ),
            showlakes = True,
            lakecolor = 'rgb(255, 255, 255)'),
             )

    fig = dict(data=data, layout=layout)
    py.plot(fig, filename='total-cases-by-state')

# make_map_of_cases()

'''
A choropleth map of the United States that presents the percentage of court cases containing a particular word or phrase (specified by the user) by state for a particular year (also specified by the user).

helper function: get_percent_by_state_containing(word) returns list of tuples: (abbr, percent)
'''

def make_map_of_word(word):

    state_percent_list = get_percent_by_state_containing(word)

    state_list = []
    z_list = []

    for state in state_percent_list:
        state_list.append(state[0])
        z_list.append(round(state[1],2))

    scl = [[0.0, 'rgb(242,240,247)'],[0.2, 'rgb(218,218,235)'],[0.4, 'rgb(188,189,220)'],[0.6, 'rgb(158,154,200)'],[0.8, 'rgb(117,107,177)'],[1.0, 'rgb(84,39,143)']]

    data = [ dict(
        type='choropleth',
        colorscale = scl,
        autocolorscale = False,
        locations = state_list,
        z = z_list,
        locationmode = 'USA-states',
        # text = df['text'],
        marker = dict(
            line = dict (
                color = 'rgb(255,255,255)',
                width = 2
            ) ),
        colorbar = dict(
            title = "Percentage of Cases")
        ) ]

    layout = dict(
        title = 'Percentage of U.S. District Court Cases Containing \"{}\" by State'.format(word),
        geo = dict(
            scope='usa',
            projection=dict( type='albers usa' ),
            showlakes = True,
            lakecolor = 'rgb(255, 255, 255)'),
             )

    fig = dict(data=data, layout=layout)
    py.plot(fig, filename='word-by-state')

# make_map_of_word("woman")

if __name__=="__main__":
    create_db()

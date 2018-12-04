# SI507-Final-ebwydra

Harvard University recently completed a massive project to expand access to U.S. caselaw by "digitizing roughly 40 million pages of court decisions contained in roughly 40,000 bound volumes owned by the Harvard Law School Library." This program uses data obtained from the Caselaw Access Project (CAP) API to provide insights into U.S. federal caselaw, particularly at the district court level.

## Data sources

### Caselaw Access Project (CAP) API

The CAP API provides access to information about all 6,000,000+ official U.S. court cases published in books from 1658 to 2018. More information about the CAP API can be found at the following link: https://case.law/api/.

The 'get_cap_data()' function makes a call to the CAP API 'cases' endpoint for information about 2,500 U.S. federal ('jurisdiction=us') court cases beginning on January 1, 2016 ('decision_date_min=2016-01-01'). Although some information about the cases is accessible without an API key, this project requests the full text of cases ('full_case=true') which requires authentication. The data obtained from the CAP API populates the 'Cases' table of the 'law.db' database.

A basic API key allows access to the full text of 500 cases per day (see https://case.law/api/#limits for details), but special researcher access is required for the volume of requests required by this program. The researcher API key should be entered into a file named 'secrets.py' that follows the structure of the 'secrets_example.py' file included in this repository.

### Wikipedia

The 'get_courts_data()' function scrapes the Wikipedia page 'List of United States district and territorial courts' (https://en.wikipedia.org/wiki/List_of_United_States_district_and_territorial_courts) for information about the 94 federal district and territorial courts in the United States, which presented in a table on Wikipedia. The data obtained from scraping Wikipedia populates the 'DistrictCourts' table of the 'law.db' database.

### CSV of U.S. states

The 'state_table.csv' file included in this repository was downloaded from Dave Ross's https://statetable.com/ and contains structured information about 56 U.S. states and territories (including Washington, D.C.). This information is used to populate the 'States' table of the 'law.db' database.

## Running the program

### Getting started

The 'capapi.py' file is the main program file, and 'requirements.txt' can be used to set up a virtual environment in which to run the program.

The program file will attempt to import API keys, etc. from a file called 'secrets.py' which must exist in the same directory as 'capapi.py' and must include three pieces of information for the program to run properly (see 'secrets_example.py'):

1) Caselaw Access Project API key, as 'CAPAPI_KEY' [Note: if you're not planning to rebuild the database from scratch or to access more than the 2,500 court cases I have in my cache file, this can be left as an empty string.]
2) Plotly username, as 'PLOTLY_USERNAME'
3) Plotly API key, as 'PLOTLY_API_KEY'

(See https://plot.ly/python/getting-started/ for more information about getting started with Plotly.)

The database and cache are pretty large: >50MB each. It is therefore recommended that you download the 'law.db' database directly rather than rebuilding the database yourself. If for some reason you would like to rebuild the database yourself, you have a couple of options...

Using my cached data:
1) The 'cache.json' and 'state_table.csv' files must be stored in the same directory as 'capapi.py'. Do not change the file names.
2) Uncomment line 687 ('create_db()') in the 'capapi.py' file.
3) Run the 'capapi.py' file.
4) Be a little patient.

From scratch:
1) The 'state_table.csv' files must be stored in the same directory as 'capapi.py'. Do not change the file name.
2) Ensure that you have an API key that provides you with unlimited research access to the CAP API.
3) Uncomment line 687 ('create_db()') in the 'capapi.py' file.
4) Run the 'capapi.py' file.
5) Be very patient.

### Using the interactive prompt

When you run the 'capapi.py' file, you will be greeted by a message that reads 'Enter command (or 'help' for options):'. The available commands are as follows:
* exit - exits the program
* help - displays list of available commands and what they do
* all_cases - creates and displays a map of the United States showing total number of district court cases in each state for the time period covered by the database (i.e., 2016-01-01 though 2016-02-04 for my database of 2,500 records)
* cases_matching <word> - creates and displays a table listing all of the cases from the time period covered by the database that contain the specified word in their full text (e.g., 'cases_matching gender')
* map_matching <word> - creates and displays a map of the United States presenting the percentage of cases from the time period covered by the database in each state containing the specified word (e.g., 'map_matching women')
* time_plot <word or list of words> - creates and displays a line chart presenting the frequency of one or more words in all U.S. federal court cases (not just district courts!) for the period of time covered by the database (e.g., 'time_plot woman women gender')

## Under the hood

### Outline
1. Lines 1 - 24: import statements, plotly configuration, global variables, caching setup
2. Lines 25 - 104: definition of functions that get data from the internet (i.e., from the CAP API and Wikipedia)
3. Lines 105 - 261: definition of function to (re)create 'law.db' database from data in cache
4. Lines 262 - 410: definitions of functions that query the 'law.db' database and process data for display (see below)
5. Lines 411 - 605: definitions of functions that use plotly to present data in four different ways, plus a little more processing (see below)
6. Lines 606 - 685: definition of interactive prompt function
7. Lines 686 - 688: showtime ;-)

### Important data processing functions

The program supports four different displays of data, each of which is supported by a function that queries the 'law.db' database and returns the specified information. These functions are then called within the data presentation functions, which further transform the data into the formats required by plotly to support the relevant presentation option.

#!/usr/bin/env python3
# =============================================================================
# File name: espn_scrape.py
# Author: Aaron Wade
# Email: aaron.wade@yale.edu
# Date created: 05/18/2020
# Date last modified: 06/08/2020
# Python Version: 3.7
# =============================================================================

# =============================================================================
import os
import pickle
import random
import re
import sys
import time
import traceback
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd
import selenium
import textdistance
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
# =============================================================================

# File paths (use forward slashes)
DROPBOX_PATH = r'C:/Users/OB Lab/Dropbox/ESPN_Scrape' # r"C:/Users/aaron/Dropbox/ESPN_Scrape/"
CHROMEDRIVER_PATH = r'C:/Users/OB Lab/Downloads/chromedriver_win32/chromedriver.exe' # r"C:/Users/aaron/Downloads/chromedriver_win32/chromedriver.exe/"

chromedriver_path_str = str(Path(CHROMEDRIVER_PATH).resolve())
data_path_str_csv = str((Path(DROPBOX_PATH) / 'espn_scrape_df.csv').resolve())
data_path_str_pickle = str((Path(DROPBOX_PATH) / 'espn_scrape_df.pkl').resolve())
progress_path_str_csv = str((Path(DROPBOX_PATH) / 'progress.csv').resolve())
progress_path_str_pickle = str((Path(DROPBOX_PATH) / 'progress.pkl').resolve())

driver = webdriver.Chrome(executable_path=chromedriver_path_str)
driver.implicitly_wait(10)

# Try to retrieve previously scraped data, or make a new data frame if this is the first run
try:
    espn_df = pd.read_pickle(data_path_str_pickle)
except:
    espn_df = pd.DataFrame(columns=["first_name", "last_name", "position","height", "weight", \
                                        "recruiting_class","hometown","hs_name","scout_grade", "n_stars",\
                                        "position_rank","regional_rank","state_rank", \
                                        "school", "status", "committed", "considering", "offer", "visit", "visit_date", \
                                        "commitment_status", "commitment_school", \
                                        "player_url", "school_commits_url", "school_considering_url", "school_offers_url", "school_visits_url", \
                                        "team_scraped_url"])

SCRAPED = 'Yes'
NOT_SCRAPED = 'No'
NOT_RANKED = 'NR'
NUM_TABS = 4
TAB_NAMES = ['Commits', 'Considering', 'Offers', 'Visits']
STATUS_COMMITTED = 'Committed'
SCHOOL_ID_PAGE = 'http://www.espn.com/colleges/basketball/recruiting/school'
START_RECRUITMENT_YEAR = 2007
END_RECRUITMENT_YEAR = 2021

# Get all school links
school_urls = {}
driver.get(SCHOOL_ID_PAGE)
for element in driver.find_elements_by_css_selector("a[href*='school/_/id/']"):
    school_urls[element.text] = element.get_attribute('href')

schools = sorted(school_urls.keys())
recruiting_classes = [str(year) for year in list(range(START_RECRUITMENT_YEAR, END_RECRUITMENT_YEAR + 1))]

# Make a dataframe to store progress
try:
    progress_df = pd.read_pickle(progress_path_str_pickle)
except:
    progress_df = pd.DataFrame(list(product(schools,recruiting_classes)), columns = ['School','Recruiting_Class'])
    progress_df['Scraped'] = NOT_SCRAPED
    progress_df.to_pickle(progress_path_str_pickle)

# Create a set of all player URLs scraped thus far
player_urls = set(espn_df['player_url'])

done = False

while not done:
    try:
        for school in schools:      
            school_subset = list(progress_df[progress_df['School'] == school]['Scraped'])
            # Check whether the school has already been scraped
            if not (NOT_SCRAPED in school_subset):
                continue
            # Go to school page
            driver.get(school_urls[school])

            for recruiting_class in recruiting_classes:
                # Check whether the year has already been scraped
                if list(progress_df[(progress_df['School'] == school) & (progress_df['Recruiting_Class'] == recruiting_class)]['Scraped'])[0] == SCRAPED:
                    continue
                
                year_to_select_xpath = "//option[text()='" + recruiting_class + "']"
                driver.find_element_by_xpath(year_to_select_xpath).click()

                for t in range(NUM_TABS):
                    tab_section = driver.find_element_by_css_selector("ul[id='tabs']")
                    current_tab = tab_section.find_element_by_css_selector("a[title='" + TAB_NAMES[t] + "']")
                    current_tab.click()

                    player_selector = "tr[class*='player']"
                    players = driver.find_elements_by_css_selector(player_selector)
                    player_url_selector = "a[href*='player/_/id/']"

                    for p in range(len(players)):
                        players = driver.find_elements_by_css_selector(player_selector)
                        current_player = players[p]
                        player_url = current_player.find_element_by_css_selector(player_url_selector).get_attribute('href')
                        # Check whether this player has already been scraped in a different school or tab
                        if player_url in player_urls:
                            continue
                        player_urls.add(player_url)
                        driver.execute_script("window.open('" + player_url + "', 'new_window')")
                        driver.switch_to.window(driver.window_handles[1])

                        time.sleep(1)

                        # Initialize variables
                        first_name = last_name = position = scout_grade = n_stars = position_rank = regional_rank = state_rank = \
                            height = weight = hometown = hs_name = commitment_status = commitment_school = url = ''

                        # Get player stats
                        names = driver.find_element_by_css_selector("div[class='player-name']").get_attribute('innerText').split(' ')
                        first_name = names[0]
                        last_name = names[1]
                        grade_section = driver.find_element_by_css_selector("div[class='grade']")
                        scout_grade = grade_section.find_element_by_xpath("./ul/li[1]").text
                        n_stars = grade_section.find_element_by_css_selector("li[class*='star']").get_attribute('class')
                        if 'one' in n_stars:
                            n_stars = 1
                        elif 'two' in n_stars:
                            n_stars = 2
                        elif 'three' in n_stars:
                            n_stars = 3
                        elif 'four' in n_stars:
                            n_stars = 4
                        elif 'five' in n_stars:
                            n_stars = 5
                        else:
                            n_stars = 'NR'

                        time.sleep(1)
                        
                        try:
                            position_rank_section = driver.find_element_by_css_selector("td[class='position border-bottom']")
                            position_rank = position_rank_section.find_element_by_xpath("./span").text
                        except NoSuchElementException as e:
                            position_rank = NOT_RANKED
                        try:
                            regional_rank_section = driver.find_element_by_css_selector("td[class='regional border-bottom']")
                            regional_rank = regional_rank_section.find_element_by_xpath("./span").text
                        except NoSuchElementException as e:
                            regional_rank = NOT_RANKED
                        try:
                            state_rank_section = driver.find_element_by_css_selector("td[class='state']")
                            state_rank = state_rank_section.find_element_by_xpath("./span").text
                        except NoSuchElementException as e:
                            state_rank = NOT_RANKED
                        
                        time.sleep(1)

                        bio_section = driver.find_element_by_css_selector("div[class='bio']")
                        position = bio_section.find_element_by_css_selector("a[href*='position']").text
                        height_and_weight_str = bio_section.find_element_by_xpath("./p").text
                        height_and_weight = re.split(', |\|', height_and_weight_str)
                        height_and_weight = list(map(lambda x: x.strip(), height_and_weight))
                        height = height_and_weight[0].replace('-', "'") + '"'
                        if height_and_weight[1].isnumeric():
                            weight = height_and_weight[1] + ' LBS'
                        hometown = bio_section.find_element_by_css_selector("a[href*='hometown']").text
                        try:
                            hs_name = bio_section.find_element_by_css_selector("a[href*='highschool']").text
                        except NoSuchElementException as e:
                            try:
                                hs_name = bio_section.find_element_by_css_selector("a[href*='prepSchool']").text
                            except:
                                pass
                        commitment_status = bio_section.find_element_by_xpath("./ul/li[4]").text[len('Status\n'):]

                        time.sleep(1)
                        
                        schools_section = driver.find_element_by_css_selector("div[class='mod-content no-footer tabular']")
                        school_rows = schools_section.find_elements_by_css_selector("tr:not([class='colhead'])")
                        school_rows = [row for row in school_rows if row.text]
                        school_data = [] 
                        
                        for row in school_rows:
                            name = status = visit_date = ''
                            committed = considering = offer = visit = int(False)
                            
                            # Check whether we're currently scraping the "Considering" tab
                            if TAB_NAMES[t] == 'Considering':
                                considering = int(True)
                            try:
                                status = row.find_element_by_xpath("./td[2]").text.strip()
                                school_name = row.text.replace(status, '').strip()
                                if status == STATUS_COMMITTED:
                                    committed = int(True)
                                    commitment_school = school_name
                            except:
                                school_name = row.text.strip()
                            try:
                                # Check for checkmark image in "Offer" column
                                row.find_element_by_xpath("./td[3]/img")
                                offer = int(True)
                            except NoSuchElementException:
                                pass
                            try:
                                # Check for checkmark image in "Visit" column
                                row.find_element_by_xpath("./td[4]/img")
                                visit = int(True)
                            except NoSuchElementException:
                                try:
                                    # Check for date in "Visit" column
                                    visit_date = row.find_element_by_xpath("./td[4]").text.strip()
                                    if visit_date:
                                        visit = int(True)
                                except:
                                    pass
                            
                            try:
                                school_page_url = school_urls[school_name] + '/class/' + recruiting_class
                                school_commits_url = school_page_url # Defaults to "Commits" tab
                                school_considering_url = school_urls[school_name] + '/class/' + recruiting_class + '/page/considering'
                                school_offers_url = school_urls[school_name] + '/class/' + recruiting_class + '/page/offers'
                                school_visits_url = school_urls[school_name] + '/class/' + recruiting_class + '/page/visits'
                            except KeyError:
                                # If there is no ESPN page for the school, default to the school links page
                                school_page_url = school_commits_url = school_considering_url = school_offers_url = school_visits_url = SCHOOL_ID_PAGE
                        
                            school_data.append({
                                "name"                   : school_name,
                                "status"                 : status,
                                "committed"              : committed,
                                "considering"            : considering,
                                "offer"                  : offer,
                                "visit"                  : visit,
                                "visit_date"             : visit_date,
                                "school_page_url"        : school_page_url,
                                "school_commits_url"     : school_commits_url,
                                "school_considering_url" : school_considering_url,
                                "school_offers_url"      : school_offers_url,
                                "school_visits_url"      : school_visits_url
                            })
                        
                        driver.close()
                        driver.switch_to.window(driver.window_handles[0])

                        for item in school_data:
                            # Append to the dataset
                            espn_df = espn_df.append({
                                "first_name"             : first_name.upper(),
                                "last_name"              : last_name.upper(),
                                "position"               : position.upper(),
                                "height"                 : height,
                                "weight"                 : weight,
                                "recruiting_class"       : ('CLASS OF' + recruiting_class),
                                "hometown"               : hometown.upper(),
                                "hs_name"                : hs_name,
                                "scout_grade"            : scout_grade,
                                "n_stars"                : n_stars,
                                "position_rank"          : position_rank,
                                "regional_rank"          : regional_rank,
                                "state_rank"             : state_rank,
                                "school"                 : item["name"].upper(),
                                "status"                 : item["status"].upper(),
                                "committed"              : item["committed"],
                                "considering"            : item["considering"],
                                "offer"                  : item["offer"],
                                "visit"                  : item["visit"],
                                "visit_date"             : item["visit_date"],
                                "commitment_status"      : commitment_status,
                                "commitment_school"      : commitment_school.upper(),
                                "player_url"             : player_url,
                                "school_commits_url"     : item["school_commits_url"],
                                "school_considering_url" : item["school_considering_url"],
                                "school_offers_url"      : item["school_offers_url"],
                                "school_visits_url"      : item["school_visits_url"],
                                "team_scraped_url"       : school_urls[school] + '/class/' + recruiting_class + '/page/' + TAB_NAMES[t].lower()
                            }, ignore_index=True)

                        time.sleep(1)

                # Write to file(s)
                espn_df.to_csv(data_path_str_csv)
                espn_df.to_pickle(data_path_str_pickle)

                # Update progress
                progress_df.loc[(progress_df['Recruiting_Class'] == recruiting_class) & (progress_df['School'] == school), 'Scraped'] = SCRAPED 
                progress_df.to_csv(progress_path_str_csv)
                progress_df.to_pickle(progress_path_str_pickle)

        done = True
    except Exception as e:
        traceback.print_exc()
        print('Retrying...\n')

driver.quit()

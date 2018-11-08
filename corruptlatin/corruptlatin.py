import pandas as pd
import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By 
from selenium.webdriver.common.keys import Keys 
from selenium.webdriver.support.ui import Select, WebDriverWait 
from selenium.common.exceptions import TimeoutException 
from selenium.webdriver.support import expected_conditions as EC 


driver = webdriver.Firefox()
driver.get("http://zakupki.gov.kg/popp/view/order/list.xhtml")

def date_range(begin_date, end_date):
    driver.find_element_by_xpath("//a[@onclick=\"SerachTabToggle()\"]").click()

    inputElement = driver.find_element_by_id("tv1:begin_input")
    inputElement.send_keys(begin_date)
    inputElement = driver.find_element_by_id("tv1:end_input")
    inputElement.send_keys(end_date)

    inputElement.submit()

def total_pages():
    #Show 50 per page
    time.sleep(2)
    dropdown = Select(driver.find_element_by_name("j_idt104:j_idt105:table_rppDD"))
    dropdown.select_by_visible_text("50")

    time.sleep(2)
    driver.find_element_by_xpath("//a[@aria-label=\"Last Page\"]").click()

    time.sleep(2)
    last_page = int(driver.find_elements_by_xpath
                    ("//a[@clas=\'ui-paginator-page ui-state-default ui-corner-all\']")[-1].text) +1
    driver.find_element_by_xpath("//[@aria-label=\"First Page\"]").click()

    return last_page

date_range('01.01.2015', '01.06.2015')
total_pages = total_pages()
print("Ther are ", total_pages, ". It will take approximately ", int(total_pages*4/60), "minutes to scrape it.")


page = 1
number = []
government_agency = []
procurement_name = []
cost_expected = []
date_published = []

while page <= total_pages: 
    time.sleep(2)
    nextpage = driver.find_element_by_link_text(str(page))
    nextpage.click()
    time.sleep(3)

    html = BeautifulSoup(driver.page_source, 'html.parser')
    name_box = html.find_all("td", attrs = {"role": "gridcell"})

    for line in name_box:
        if '№\n\t\t\t ' in line.text:
            number.append(line.text[26: 41])
        elif "Наименование органзаци" in line.text:
            government_agency.append(line.text.replace("\nНаименование органзаци", ""))
        elif "Наименование закупки" in line.text:
            government_agency.append(line.text.replace("\nНаименование закупки", ""))
        elif "Планируемая сумма" in line.text:
            government_agency.append(line.text.replace("\nПланируемая сумма", ""))
        elif "дата опубликования" in line.text:
            government_agency.append(line.text.replace("\дата опубликования", ""))
page+=1

list = [('number', number), ('government_agency', government_agency), ('procurement_name', procurement_name),
        ('cost_expected', cost_expected), ('date_published', date_published)]
df = pd.DataFrame.from_items(list)

if df.duplicated().sum() != 0:
    print("There are", df.duplicated().sum(), 'duplicate rows. Please increase "time.sleep()"')

column = [value for value in df["procurement_name"]]
iscorruptiblelatin = []

for string in column:
    string_latin_cyr = False

    for word in string.split():
        for index, char1 in enumerate(word):
            if char1.upper() in 'АЕТУОНКХСВМ':
                if index != len(word) -1: #if not the last char - check the right
                    char2 = word[index+1]

                    if 1039<ord(char2)<1104:
                        string_latin_cyr = True
                
                if index != 0: #if not the first char - check the left
                    char2 = word[index -1]

                    if 1039<ord(char2)<1104:
                        string_latin_cyr = True
    
    iscorruptlatin.append(string_latin_cyr)

df['iscorruptlatin'] = iscorruptiblelatin
corruptlatin2015 = df.loc[df['iscorruptlatin'] == True]
corruptlatin2015.to_excel('/Users/Shared/code/python_pieces/bellingcat/corruptlatin.xlsx')


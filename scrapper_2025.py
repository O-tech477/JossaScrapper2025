from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from database_manage import store_data_entry


JOSSA_URL = "https://josaa.admissions.nic.in/applicant/SeatAllotmentResult/CurrentORCR.aspx"

def initialize_scrapping():
    chrome_options = webdriver.ChromeOptions()
    #chrome_options.add_argument("--headless")

    driver = webdriver.Chrome(chrome_options)
    driver.get(JOSSA_URL)

    return driver

#Perhaps the single most important function of this code to click dropdown with JS scripts, Select() does not work because the divs are NOT visible on the screen so scipting is needed
#Plus as its .aspx postBack is important to be allowed to POST data of next dropdown
def set_dropdown_value(driver, value, dropdown_id, postback_control):
    dropdown = driver.find_element(By.ID, dropdown_id)

    driver.execute_script(
        "arguments[0].value = arguments[1]", 
        dropdown,
        value
    )

    driver.execute_script(
        f"__doPostBack('{postback_control}' , '')"
    )

    WebDriverWait(driver, 10).until(
        lambda d: d.find_element(By.ID, dropdown_id).get_attribute("value") == value
    )

def scrape_data():


    driver = initialize_scrapping()
    all_data = []
    rounds = ["1", "2", "3", "4", "5", "6"]


    for round in rounds:
        #Setting value of round
        set_dropdown_value(driver, round, "ctl00_ContentPlaceHolder1_ddlroundno", "ctl00$ContentPlaceHolder1$ddlroundno")

        #In this website after rounds is set I need to manually set the other fields too which is set to 'ALL' to retrive all data
        set_dropdown_value(driver, "ALL", "ctl00_ContentPlaceHolder1_ddlInstype", "ctl00$ContentPlaceHolder1$ddlInstype")
        set_dropdown_value(driver, "ALL", "ctl00_ContentPlaceHolder1_ddlInstitute", "ctl00$ContentPlaceHolder1$ddlInstitute")
        set_dropdown_value(driver, 'ALL', "ctl00_ContentPlaceHolder1_ddlBranch", "ctl00$ContentPlaceHolder1$ddlBranch")
        set_dropdown_value(driver, "ALL", "ctl00_ContentPlaceHolder1_ddlSeattype", "ctl00$ContentPlaceHolder1$ddlSeattype")

        #Pressing submit button
        #Using script because otherwise it wont work in headless mode. 
        submit_button = driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_btnSubmit")
        driver.execute_script("arguments[0].click()", submit_button)

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "ctl00_ContentPlaceHolder1_GridView1"))
        )

        #Retrieve the tables data 
        html_source = driver.page_source

        soup = BeautifulSoup(html_source, "html.parser")
        table = soup.find(id="ctl00_ContentPlaceHolder1_GridView1")


        if table:
            rows = table.find_all("tr")

            for row in rows[1:]:
                cells = row.find_all("td")
                
                if not cells:
                    continue
                    
                print("Found cells")
                
                row_data = [cell.get_text(strip=True) for cell in cells]
                
                row_data.append(round)
                row_data.append("2025")
                
                all_data.append(row_data)

    store_data_entry(all_data)


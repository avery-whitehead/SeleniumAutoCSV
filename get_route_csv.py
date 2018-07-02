"""
get_route_csv.py
Uses Selenium to automate the process of downloading a CSV
file of route patterns

URL for downloading exports:
&aid=<value of dropdown menu>
&aname=<vehicle registration>
"""

import glob
import os
import time
import logging
from typing import Tuple, List
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException

def get_vehicles(path: str) -> List[str]:
    """
    Gets the list of vehicles from a file. Each new line in the file
    is a new vehicle. Lines starting with # are to be ignored.
    Args:
        path (str): The path of the file containing the vehicles list
    Returns:
        List[str]: A list of all the vehicles read from the file
    """
    with open(path, 'r') as vehicles_f:
        vehicles = vehicles_f.readlines()
    # Remove newline characters and elements starting with #
    return [veh.strip() for veh in vehicles if not veh.startswith('#')]

def setup_driver(headless: bool, directory: str) -> webdriver:
    """
    Sets up the Chrome webdriver with arguments for use
    as a browser session
    Args:
        headless (bool): Runs the browser in a headless session if
        true, leaves option as default if true
        directory (str): The directory to download any files to
    """
    options = webdriver.ChromeOptions()
    options.add_argument('--disable-gpu')
    options.add_argument('--log-level=3')
    prefs = {
        'download.default_directory': directory,
        'download.prompt_for_download': False,
        'download.directory_upgrade': True,
        'safebrowsing.enabled': False,
        'safebrowsing.disable_download_protection': True}
    options.add_experimental_option('prefs', prefs)
    if headless:
        options.add_argument('--headless')
    driver = webdriver.Chrome(
        executable_path=r'.\chromedriver.exe',
        options=options)
    # Enables downloading through headless chrome
    command = '/session/$sessionId/chromium/send_command'
    driver.command_executor._commands['send_command'] = ('POST', command)
    driver.desired_capabilities['browserName'] = 'Chrome'
    params = {
        'cmd': 'Page.setDownloadBehavior',
        'params': {
            'behavior': 'allow',
            'downloadPath': directory}}
    driver.execute("send_command", params)
    print('Launching browser')
    return driver

def login(
        driver: webdriver,
        account: str,
        username: str,
        password: str) -> None:
    """
    Navigates through the fields of the login page
    Args:
        driver (webdriver): The webdriver used to run the browser session
        account (str): The account number
        username (str): The username to login with
        password (str): The password for the given username
    """
    driver.get('https://www.dennisconnect.co.uk/')
    # First page may be some cookie information that needs accepting
    if driver.title == 'Cookie Usage':
        driver.find_element_by_id('btnAccept').click()
    if 'Login' in driver.title:
        account_field = driver.find_element_by_id('txtAccountNumber')
        account_field.send_keys(account)
        username_field = driver.find_element_by_id('txtUserName')
        username_field.send_keys(username)
        password_field = driver.find_element_by_id('txtPassword')
        password_field.send_keys(password)
        password_field.send_keys(Keys.RETURN)
        print(f'Logging in as {username}')

def go_to_history(driver: webdriver) -> None:
    """
    Navigates to the history page
    Args:
    driver (webdriver): The webdriver used to run the browser session
    """
    # Go to History tab
    driver.find_element_by_xpath('//*[@id="tabContainer"]/li[3]').click()
    # Manually switch to History iframe after clicking the tab
    driver.switch_to_frame('tab4frame')
    ping_list = WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((
            By.ID,
            'ctl00_cphcontent_htPingList')))
    ping_list.click()

def get_vehicle_id(driver: webdriver, vehicle: str) -> Tuple[str, str]:
    """
    Gets the ID on the history page associated with the vehicle
    Args:
        driver (webdriver): The webdriver used to run the browser session
        vehicle (str): The registration of the vehicle to look up
    Returns:
        Tuple[str, str]: A 2-tuple consisting of the vehicle registration
        and its associated ID on the page
    """
    print(f'Finding history for {vehicle}')
    dropdown = Select(driver.find_element_by_id('ctl00_cphcontent_ddlVehicle'))
    dropdown.select_by_visible_text(vehicle)
    driver.find_element_by_id('ctl00_cphcontent_btnRunHistory').click()
    # Get value attribute from selected option
    selected = driver.find_element_by_xpath(
        f'//*[@id="ctl00_cphcontent_ddlVehicle"]/option[.="{vehicle}"]')
    return (vehicle, selected.get_attribute('value'))

def download_csv(driver: webdriver, dropdown_option: Tuple[str, str]) -> None:
    """
    Downloads the CSV containing route details for the selected vehicle
    Args:
        driver (webdriver): The webdriver used to run the browser session
        dropdown_option (Tuple[str, str]): The tuple returned from
        go_to_history(), used to fill in parameters for the download URL
    """
    aid = dropdown_option[1]
    aname = dropdown_option[0]
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%d/%m/%Y')
    url = 'https://www.dennisconnect.co.uk/_handler/csv.ashx?' \
        'req=HISTORY_LIST&' \
        f'sdate={yesterday}%2000:00&edate={yesterday}%2023:59' \
        f'&atype=V&aid={aid}&aname={aname}' \
        '&locfil=&useshape=false&dtl=0&s2r=false' \
        '&showdriverbehavioralerts=false'
    print('Downloading CSV file')
    driver.get(url)
    time.sleep(3)
    # Get name of downloaded file
    files = glob.glob('./*.csv')
    downloaded = max(files, key=os.path.getctime)
    newname = f'./{aname}_{downloaded[2:-4]}.csv'
    os.rename(downloaded, newname)
    print(f'Downloaded file {newname[2:]}\n')

if __name__ == '__main__':
    logging.basicConfig(filename='./get_routes.log', level=logging.INFO)
    vehicles = get_vehicles('./vehicles_list.txt')
    # Needs to be absolute path
    directory = r'C:\..\..\..'
    try:
        driver = setup_driver(True, directory)
        for vehicle in vehicles:
            login(driver, '####', '####', '####')
            go_to_history(driver)
            vehicle_id = get_vehicle_id(driver, vehicle)
            download_csv(driver, vehicle_id)
    except (NoSuchElementException, TimeoutException) as exc:
        logging.exception(exc)

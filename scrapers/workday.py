from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    StaleElementReferenceException,
    NoSuchElementException
)

from scrapers.base_scraper import BaseScraper
from filters import preliminary_filter as filter
import re
from datetime import datetime, timedelta
from utils.types import JobCardInfo
from typing import Optional
import time

class WorkdayScraper(BaseScraper):

    def open_jobs_page(self, url: str):
        self.driver.get(url)

    def get_job_results_section(self):

        return WebDriverWait(self.driver, 20).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "section[data-automation-id='jobResults']")
            )
        )
    
    def wait_for_page_ready(self):

        WebDriverWait(self.driver, 30).until(
            lambda d: d.execute_script(
                "return document.readyState"
            ) == "complete"
        )

    def wait_for_jobs_to_load(self):
        def jobs_loaded(driver):

            title_elements = driver.find_elements(
                By.CSS_SELECTOR,
                "a[data-automation-id='jobTitle']"
            )

            if len(title_elements) == 0:
                return False

            for el in title_elements:

                text = el.text.strip()

                if text == "":
                    return False

            return True

        WebDriverWait(self.driver, 30).until(jobs_loaded)

    def get_pagination_info(self, section):
        try:
            ul = section.find_element(
                By.CSS_SELECTOR,
                "ul[role='list']"
            )
        except:
            return None


        aria_label = ul.get_attribute("aria-label")

        # Example:
        # "Page 1 of 54"

        match = re.search(r'Page\s+(\d+)\s+of\s+(\d+)', aria_label)

        if not match:
            return None

        current_page = int(match.group(1))
        total_pages = int(match.group(2))

        return current_page, total_pages
            # "current_page": current_page,
            # "total_pages": total_pages
        

    def get_job_cards(self, section):
        jobs_list = section.find_element(
            By.CSS_SELECTOR,
            "ul[role='list']"
        )

        cards = jobs_list.find_elements(
            By.XPATH,
            "./li"
        )

        return cards
    
    def parse_posted_date(self, date_text: str) -> Optional[datetime]:
        if not date_text:
            return None
        
        text = date_text.strip().lower()
        now = self.today
    
        if "today" in text:
            return now

        # Posted Yesterday
        if "yesterday" in text:
            return now - timedelta(days=1)

        # Posted X Days Ago
        match = re.search(r'(\d+)\s+day', text)

        if match:
            days = int(match.group(1))
            return now - timedelta(days=days)

        # Posted X Weeks Ago
        match = re.search(r'(\d+)\s+week', text)

        if match:
            weeks = int(match.group(1))
            return now - timedelta(weeks=weeks)

        # Posted X Months Ago
        match = re.search(r'(\d+)\s+month', text)

        if match:
            months = int(match.group(1))

            # approximate month length
            return now - timedelta(days=months * 30)

        return None

    def parse_job_card(self, card, page) -> JobCardInfo:
        try:

            title_el = card.find_element(
                By.CSS_SELECTOR,
                "a[data-automation-id='jobTitle']"
            )

            title = title_el.text.strip()

            link = title_el.get_attribute("href")

        except:
            title = None
            link = None

        # LOCATION
        try:

            location_el = card.find_element(
                By.CSS_SELECTOR,
                "div[data-automation-id='locations'] dd"
            )

            location = location_el.text.strip()

        except:
            location = None

        # REMOTE TYPE
        try:

            remote_el = card.find_element(
                By.CSS_SELECTOR,
                "div[data-automation-id='remoteType'] dd"
            )

            remote_type = remote_el.text.strip()

        except:
            remote_type = None

        # POSTED DATE
        try:

            posted_el = card.find_element(
                By.CSS_SELECTOR,
                "div[data-automation-id='postedOn'] dd"
            )

            posted_date = posted_el.text.strip()

        except:
            posted_date = None

        # JOB ID
        try:

            job_id_el = card.find_element(
                By.CSS_SELECTOR,
                "ul[data-automation-id='subtitle'] li"
            )

            job_id = job_id_el.text.strip()

        except:
            job_id = None

        jobInfo = JobCardInfo(
            page=page,
            title=title,
            location=location,
            remote_type=remote_type,
            posted_date=self.parse_posted_date(posted_date),
            job_id=job_id,
            parsed_date=self.today,
            link=link
        )

        return jobInfo
    
    def parse_job_card_with_retry(self, card):

        for _ in range(3):

            try:
                return self.parse_job_card(card)

            except (
                StaleElementReferenceException,
                NoSuchElementException
            ):

                time.sleep(1)

        return None
    
    def navigate_to_next_page(self):

        try:

            old_section = self.get_job_results_section()

            old_cards = self.get_job_cards(old_section)

            next_button = old_section.find_element(
                By.CSS_SELECTOR,
                "button[aria-label='next']"
            )

            self.driver.execute_script(
                "arguments[0].scrollIntoView(true);",
                next_button
            )

            next_button.click()

            # wait for old DOM to disappear
            WebDriverWait(self.driver, 30).until(
                EC.staleness_of(old_cards[0])
            )

            # wait for new jobs to load
            self.wait_for_page_ready()

            self.wait_for_jobs_to_load()

            time.sleep(1)

            return True

        except Exception as e:

            print(f"Failed to navigate: {e}")

            return False
        
    
    def run(self, url: str):
        parsed_jobs = []
        self.open_jobs_page(url)
        self.wait_for_page_ready()
        self.wait_for_jobs_to_load()
        time.sleep(1)

        while True:
            section = self.get_job_results_section()
            pagination = self.get_pagination_info(section)
            if not pagination:
                break
            current_page, total_pages = pagination

            cards = self.get_job_cards(section)
            for card in cards:
                job = self.parse_job_card(card, current_page)
                if filter.passes_preliminary_filters(job, current_page):
                    parsed_jobs.append(job)
            
            # break
            if current_page == total_pages:
                break
            else:
                self.navigate_to_next_page(section)
        
        return parsed_jobs

            
    

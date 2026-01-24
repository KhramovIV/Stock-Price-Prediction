import selenium
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
import time
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from random import random
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
import csv
import os


class Parser():
    def __init__(self):
        options = webdriver.ChromeOptions()
        options.add_argument("--headless=new") 
        options.add_argument("--disable-gpu")
        options.add_argument("--log-level=3")
        options.page_load_strategy = 'eager'
        prefs = {"profile.managed_default_content_settings.images": 2}
        options.add_experimental_option("prefs", prefs)

        self.driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)
        
        self.driver.set_window_size(1920, 1080)    
        self.wait = WebDriverWait(self.driver, 5)
        self.SCROLL_TIME = 0.5
        self.START_DATE = datetime(2006, 1, 1)
        self.END_DATE = datetime(2025, 12, 20)


    def get_page_html(self, date):
        """
        Docstring для get_page_html

        :param date: Date format YYYYMMDD 
        """
        try:
            self.driver.get(f"https://ria.ru/economy/{date}/")
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

            show_more_div = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.list-more"))
            )
            self.driver.execute_script("arguments[0].click();", show_more_div)

            # Scroll until webpage can be scrolled
            time.sleep(0.8)
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

            html_content = self.driver.page_source
            return html_content
        except Exception as e:
            print(f"Ошибка при загрузке страницы {date}: {e}")
            return None


    def parse_page(self, date):
        html_content = self.get_page_html(date)
        if html_content is None:
            return None
        soup = BeautifulSoup(html_content, "lxml")

        news_data = []
        items = soup.find_all(class_="list-item")
        for item in items:
            text = item.find(class_="list-item__content").find(class_="list-item__title").text
            try:
                date, views = item.find_all(class_="list-item__info-item")
            except ValueError:
                print(f'Пропускаем {date}')
                break
            date = date.text
            views = views.text
            tags = item.find(class_="list-item__tags").find(class_="list-item__tags-list").find_all(class_="list-tag m-add")
            tag_text = []
            href = []
            for tag in tags:
                tag_text.append(tag.text)
                href.append(tag['href'])

            news_data.append({"text": text, 
                              "date": date, 
                              "views": views, 
                              "tag_text": tag_text, 
                              "href": href})            
        return news_data
    

    def parse(self):
        def date_range(start_date, end_date):
            for n in range(int((end_date - start_date).days) + 1):
                yield start_date + timedelta(n)

        file_exists = os.path.exists("news.csv")

        with open("../data/1-raw/news.csv", "a", newline="", encoding="utf-8") as f:
            writer = None
            for current_date in date_range(self.START_DATE, self.END_DATE):
                date = current_date.strftime('%Y%m%d')
                print(date)

                retries = 3
                news_data = self.parse_page(date)
                while retries > 0 and news_data is None:
                    news_data = self.parse_page(date)

                    if news_data is None:
                        retries -= 1
                        print(f"  retry... ({3 - retries}/3)")
                        time.sleep(1)  # пауза между попытками

                if news_data is None:
                    print(f"  FAILED for {date}")
                    continue

                if not news_data:  # пустой список
                    continue

                if writer is None:
                    writer = csv.DictWriter(f, fieldnames=news_data[0].keys())
                    if not file_exists:
                        writer.writeheader() 

                writer.writerows(news_data)


if __name__ == 'main':
    parser = Parser()
    parser.parse()

        
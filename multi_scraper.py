# Data Basics
import pandas as pd
import numpy as np
from datetime import datetime as dt

pd.options.display.float_format = "{:.0f}".format

import time
import requests
from tqdm import tqdm
import os
import re

# scraping 'STUFF'
from bs4 import BeautifulSoup
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options

chrome_options = Options()
### Use Headless ###
# chrome_options.add_argument("--no-sandbox")
# chrome_options.add_argument("--headless")
print(f"Chrome headless is set to: {chrome_options.headless}")
### don't load images ###
# prefs = {"profile.managed_default_content_settings.images": 2}
# chrome_options.add_experimental_option("prefs", prefs)
print(f"Chrome will download images is set to: {chrome_options.arguments}")


# chrome_options = webdriver.ChromeOptions()

# driver = webdriver.Chrome(chrome_options=chrome_options)

### attempting to scrape multiple cities at once - currently doesn't work (TODO) ###
import concurrent.futures


class SiteReader:
    def __init__(self):
        """ Headless options for script """
        self.driver = webdriver.Chrome(options=chrome_options)
        print("Stating Chrome...")

    def get_url_list(self, base_url, city_url):
        """Gets a list of urls from main page to scrape."""
        # self.driver.get(
        #     "https://www.trulia.com/for_rent/Austin,TX/APARTMENT,APARTMENT_COMMUNITY,APARTMENT%7CCONDO%7CTOWNHOUSE,CONDO,COOP,LOFT,TIC_type/"
        # )\

        url_list = []
        last_page = False
        i = 1
        print(base_url, city_url)

        # while last_page == False and i < 100:  # 100 picked because 92 pages for austin
        while last_page == False:
            time.sleep(0.1)
            print(base_url + city_url)
            self.driver.get(base_url + city_url)  # city + page of site
            html = self.driver.execute_script("return document.body.innerHTML;")
            soup = BeautifulSoup(html, features="lxml")

            # Test for reCaptcha
            if soup.find("h1").text == "Please verify you are a human":
                print("URL INFO - RECAPTCHA!!!!")
                time.sleep(300)

            for div in soup.find_all(
                "div",
                {
                    "data-hero-element-id": "srp-home-card",
                    "data-hero-element-id": "false",
                },
            ):
                # print(div)
                url = div.find("a").attrs["href"]
                url_list.append(url)

            # check if last page and exit while loop
            if soup.find("a", {"aria-label": "Next Page"}):
                last_page = False
                city_url = soup.find("a", {"aria-label": "Next Page"})["href"]
                # print(city_url)
                time.sleep(0.1)
            else:
                last_page = True
            # print(url_list)

            # keep this up, if recapcha fails this errors out so you can fix it,
            # headless=False in this senario of course...
            print(f"Page: {i} last listing: {url_list[-1]}")
            i += 1
        return url_list

    def get_apartment_data(self, base_url, current_url):
        """Gets apartment data for the url specified"""
        try:
            time.sleep(0.1)
            # print(base_url + current_url)
            response = self.driver.get(base_url + current_url)
            html = self.driver.execute_script("return document.body.innerHTML;")
            soup = BeautifulSoup(html, "lxml")
            # print(soup.text)

        except (ConnectionError, ConnectionResetError):
            pass

        # Test for reCaptcha
        if soup.find("h1").text == "Please verify you are a human":
            print("APT INFO - RECAPTCHA!!!!")
            time.sleep(300)

        apartment_list = []
        df = self.create_df()
        # print(f"made the dataframe: {df}")

        # Is this an apartment complex with a table to parse?
        if soup.find_all("table", {"data-testid": "floor-plan-group"}) != None:
            for floor_plan_table in soup.find_all(
                "table", {"data-testid": "floor-plan-group"}
            ):
                for tr in floor_plan_table.find_all("tr"):

                    unit = tr.find("div", {"color": "highlight"}).text
                    # print(unit)

                    sqft = tr.find(
                        "td",
                        {
                            "class": lambda L: L
                            and L.startswith("FloorPlanTable__FloorPlanFloorSpaceCell")
                        },
                    ).text

                    bed = tr.find_all(
                        "td",
                        {
                            "class": lambda L: L
                            and L.startswith("FloorPlanTable__FloorPlanFeaturesCell")
                        },
                    )[0].text

                    bath = tr.find_all(
                        "td",
                        {
                            "class": lambda L: L
                            and L.startswith("FloorPlanTable__FloorPlanFeaturesCell")
                        },
                    )[1].text

                    price = tr.find_all(
                        "td",
                        {
                            "class": lambda L: L
                            and L.startswith("FloorPlanTable__FloorPlanCell"),
                            "class": lambda L: L
                            and L.startswith("FloorPlanTable__FloorPlanSMCell"),
                        },
                        limit=2,
                    )[1].text

                    name = soup.find(
                        "span", {"data-testid": "home-details-summary-headline"}
                    ).text

                    address = soup.find_all(
                        "span", {"data-testid": "home-details-summary-city-state"}
                    )[0].text

                    city_state_zip = soup.find_all(
                        "span", {"data-testid": "home-details-summary-city-state"}
                    )[1].text

                    city, state, zipcode = city_state_zip.replace(",", "").rsplit(
                        maxsplit=2
                    )

                    description = soup.find(
                        "div", {"data-testid": "home-description-text-description-text"}
                    ).text

                    details = [
                        detail.text
                        for detail in soup.find_all(
                            "li",
                            {
                                "class": lambda L: L
                                and L.startswith("FeatureList__FeatureListItem")
                            },
                        )
                    ]
                    details = " ,".join(details)

                    apartment_url = base_url + current_url
                    date = str(dt.now().date())

                    df = pd.concat(
                        [
                            df,
                            pd.DataFrame(
                                [
                                    {
                                        "name": name,
                                        "address": address,
                                        "unit": unit,
                                        "sqft": sqft,
                                        "bed": bed,
                                        "bath": bath,
                                        "price": price,
                                        "city": city,
                                        "state": state,
                                        "zipcode": zipcode,
                                        "description": description,
                                        "details": details,
                                        "url": apartment_url,
                                        "date": date,
                                    }
                                ]
                            ),
                        ],
                        ignore_index=True,
                    )
        else:  # a home, condo, etc... not an apt complex
            try:
                home_deets = soup.find_all(
                    "div", {"data-testid": "home-details-summary-container"}
                )
                price = (
                    home_deets[0]
                    .find_all("div", lambda L: L and L.startswith("Text__TextBase"))[0]
                    .text
                )
                bed = (
                    home_deets[0]
                    .find_all(
                        "div", lambda L: L and L.startswith("MediaBlock__MediaContent")
                    )[0]
                    .text
                )
                bath = (
                    home_deets[0]
                    .find_all(
                        "div", lambda L: L and L.startswith("MediaBlock__MediaContent")
                    )[1]
                    .text
                )
                sqft = (
                    home_deets[0]
                    .find_all(
                        "div", lambda L: L and L.startswith("MediaBlock__MediaContent")
                    )[2]
                    .text
                )
                name = (
                    home_deets[0]
                    .find_all("span", {"data-testid": "home-details-summary-headline"})[
                        0
                    ]
                    .text
                )
                address = (
                    home_deets[0]
                    .find_all("span", {"data-testid": "home-details-summary-headline"})[
                        0
                    ]
                    .text
                )
                city_state_zip = (
                    home_deets[0]
                    .find_all(
                        "span", {"data-testid": "home-details-summary-city-state"}
                    )[0]
                    .text
                )
                city, state, zipcode = city_state_zip.replace(",", "").rsplit(
                    maxsplit=2
                )
                description = soup.find_all(
                    "div", {"data-testid": "home-description-text-description-text"}
                )[0].text
                details = [
                    detail.text
                    for detail in soup.find_all(
                        "li",
                        {
                            "class": lambda L: L
                            and L.startswith("FeatureList__FeatureListItem")
                        },
                    )
                ]
                unit = "home"
                date = str(dt.now().date())
                apartment_url = base_url + current_url
                df = pd.concat(
                    [
                        df,
                        pd.DataFrame(
                            [
                                {
                                    "name": name,
                                    "address": address,
                                    "unit": unit,
                                    "sqft": sqft,
                                    "bed": bed,
                                    "bath": bath,
                                    "price": price,
                                    "city": city,
                                    "state": state,
                                    "zipcode": zipcode,
                                    "description": description,
                                    "details": details,
                                    "url": apartment_url,
                                    "date": date,
                                }
                            ]
                        ),
                    ],
                    ignore_index=True,
                )
            except Exception as e:
                pass
        return df

    def get_all_apartments(self, base_url, url_list, city, state):
        """
        Wrapper function using "get_apartment_data" function to get data for all apartments in "url_list"
        """

        apts_data = self.create_df()
        for i, current_url in enumerate(
            tqdm(url_list.iloc[:, 1].to_list(), unit="site"), start=1
        ):
            if i % 10 == 0:
                apts_data.to_csv(f"DATA/scrape_files/partial_{city}_{state}.csv")
            # print(current_url)
            time.sleep(0.3)
            apts_data = pd.concat(
                [apts_data, self.get_apartment_data(base_url, current_url)],
                ignore_index=True,
            )
            print(apts_data.tail(1))
        return apts_data

    def create_df(self):
        df = pd.DataFrame(
            columns=[
                "name",
                "address",
                "unit",
                "sqft",
                "bed",
                "bath",
                "price",
                "city",
                "state",
                "zipcode",
                "description",
                "details",
                "url",
                "date",
            ]
        )
        return df

    def df_converter(self, df):
        """Converts rows to numeric and float for calculations"""
        df = df.astype(
            {"sqft": "int32", "price": "int32", "bath": "float32", "bed": "float32"}
        )

        return df


def main():
    """ MAIN """
    # bot = SiteReader()
    base_url = "https://www.trulia.com"

    cities = [
        # ["Chicago", "IL"],
        # ["Saint_Louis", "MO"],
        # ["New_York", "NY"],
        # ["Las_Vegas", "NV"],
        # ["Dallas", "TX"],
        # ["Portland", "OR"],
        # ["Seattle", "WA"],
        # ["Minneapolis", "MN"],
        # ["Orlando", "FL"],
        # ["San_Francisco", "CA"],
        # ["Austin", "TX"],
        # ["Ann_Arbor", "MI"],
    ]

    ### will attempt multi-site reading from here ###
    today = int(dt.today().strftime("%Y%m%d"))

    austin = SiteReader()
    austin_url = f"/for_rent/Austin,TX/"
    austin_residence_urls = f"DATA/urls/apt_page_listings_Austin_TX_{today}.csv"
    austin_unit_info = f"DATA/scrape_files/apt_unit_listings_Austin_TX_{today}.csv"

    # would expect it hang here...
    austin_list = bot.get_url_list(base_url, austin_url)
    to_save = pd.DataFrame(ulist)
    to_save.to_csv(residence_urls)
    url_list = pd.read_csv(residence_urls)

    # Generate list of URLs to walk through, skip if saved list is recent
    for i, city_state in enumerate(tqdm(cities, unit="city"), start=1):
        days_back = 10
        today = int(dt.today().strftime("%Y%m%d"))
        city, state = city_state

        city_url = f"/for_rent/{city},{state}/"
        residence_urls = f"DATA/urls/apt_page_listings_{city}_{state}_{today}.csv"
        unit_info = f"DATA/scrape_files/apt_unit_listings_{city}_{state}_{today}.csv"

        for i in range(7):
            if os.path.isfile(
                f"DATA/urls/apt_page_listings_{city}_{state}_{today - i}.csv"
            ):
                url_list = pd.read_csv(
                    f"DATA/urls/apt_page_listings_{city}_{state}_{today - i}.csv"
                )
                break  # only breaks one-level out of for-loop
            elif i < (days_back - 1):
                continue
            else:
                print("No recent file found, generating new list")
                ulist = bot.get_url_list(base_url, city_url)
                to_save = pd.DataFrame(ulist)
                to_save.to_csv(residence_urls)
                url_list = pd.read_csv(residence_urls)

        # Find all the units available for a listing
        if os.path.isfile(unit_info):
            print("units file found")
        else:
            print("units file not found")
            apts_data = bot.get_all_apartments(base_url, url_list, city, state)
            to_save = pd.DataFrame(apts_data)
            to_save.to_csv(unit_info)


if __name__ == "__main__":
    print(f"Starting...")
    os.system("echo $DISPLAY")

    main()
    # with concurrent.futures.ThreadPoolExecutor() as executor:
    #     for i, city_state in enumerate(tqdm(cities, unit="city"), start=1):
    #         executor.map(main, [i, city_state])

    # https://testdriven.io/blog/building-a-concurrent-web-scraper-with-python-and-selenium/
    # https://medium.com/@pyzzled/running-headless-chrome-with-selenium-in-python-3f42d1f5ff1d
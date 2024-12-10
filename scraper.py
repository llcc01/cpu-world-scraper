#!/usr/bin/env python
# -*- coding:UTF-8 -*-

# rikujjs


import pickle
from bs4 import BeautifulSoup
from time import sleep
from selenium import webdriver
from selenium.webdriver.chrome.service import Service

# column_headers array contains the names for the columns.
column_headers = [
    "Brand",
    "Model",
    "Type",
    "Release",
    "Clockrate",
    "Cores",
    "Cache",
    "Socket",
    "URL",
]


months_dict = {
    "January": 1,
    "February": 2,
    "March": 3,
    "April": 4,
    "May": 5,
    "June": 6,
    "July": 7,
    "August": 8,
    "September": 9,
    "October": 10,
    "November": 11,
    "December": 12,
}

page_cache = {}

chrome_options = webdriver.ChromeOptions()
chrome_options.add_experimental_option("detach", True)

service = Service("/home/lc/tools/bin/chromedriver")

driver = None

class Scraper:

    # make the parsed soup in to a variable called "soup"
    def __init__(self, url, year, output):
        global driver

        self.url = url
        self.year = year
        self.write_handle = output

        # member variables
        self.soup = None
        self.datastorage = {}
        self.page_data = []

        # initialize the datastorage[] dict
        for header in column_headers:
            self.datastorage[header] = "-"

        if url in page_cache:
            print("Using cache", url)
        else:
            # include possible spoofed header, and get the page
            if driver is None:
                driver = webdriver.Chrome(service=service, options=chrome_options)
            driver.get(url)
            html_text = driver.page_source

            page_cache[url] = html_text

            # be nice
            sleep(1)

        self.soup = BeautifulSoup(page_cache[url], "html.parser")

    # we go thru the datastorage[] dict and write the info to a string, separated with ','
    def info_to_string(self):

        info_string = ""

        # write the columns to a single string, place a ',' in between
        for header in column_headers:

            info_string += ","
            info_string += self.datastorage[header].strip().replace(",", "")

        # get rid of the first ,
        info_string = info_string.replace(",", "", 1)

        return info_string

    # format the date to a more usable form, eg. 2-2005
    def get_date(self, month):

        try:
            month_number = months_dict[month]
        except KeyError:
            print(self.url)
            return self.year

        return str(self.year) + "-" + str(month_number)

    def get_months_models(self, data, brand, date, type="Unknown"):

        self.datastorage["Brand"] = brand
        self.datastorage["Release"] = self.get_date(date)

        models = data.findAll("a")
        specs = data.findAll("div", "rel_sp")

        assert len(models) == len(
            specs
        ), f"Models and specs length mismatch: {len(models)} != {len(specs)}"

        for model, spec_ in zip(models, specs):

            try:

                # make sure the dict is empty
                for key in self.datastorage:
                    self.datastorage[key] = "-"

                # brand and release
                self.datastorage["Brand"] = brand
                self.datastorage["Release"] = self.get_date(date)

                self.datastorage["Model"] = model.text
                self.datastorage["URL"] = "https://www.cpu-world.com" + model["href"]
                self.datastorage["Type"] = type

                specs_split = spec_.text.split("/")

                for spec in specs_split:

                    if "Hz" in spec:
                        self.datastorage["Clockrate"] = spec.strip()
                    elif "core" in spec.lower():
                        self.datastorage["Cores"] = spec.replace("cores", "").replace("core", "").replace(" ", "").strip()
                    elif "socket" in spec.lower():
                        self.datastorage["Socket"] = spec.strip()
                    elif "fsb" in spec.lower():
                        self.datastorage["FSB"] = spec.strip()
                    elif (
                        "l1" in spec.lower()
                        or "l2" in spec.lower()
                        or "l3" in spec.lower()
                        or "l4" in spec.lower()
                    ):
                        self.datastorage["Cache"] = spec.strip()
                    else: 
                        pass
                        # print(spec)
                        # print(self.url)

                # place the model info into a string, and store in a array for later use
                model_specs = self.info_to_string()
                self.page_data.append(model_specs)

                # self.write_handle(model_specs)
                # self.write_handle('\n')
            except IndexError:
                pass

    # do the actual scraping
    def get_pageinfo(self, type="Unknown"):

        # do the actual scraping here
        info = self.soup.find("div", "p_div")
        monthly_info = info.findAll("div", "rel_data")

        for month_info in monthly_info:
            info_line = month_info.findAll("div")

            date = info_line[0].text

            if date is None:
                continue

            data_div = info_line[1].findAll("div")

            if len(data_div) > 0:
                self.get_months_models(data_div[0], "AMD", date, type)
                self.get_months_models(data_div[1], "Intel", date, type)

        # # eventualy return the collected data
        return self.page_data


if __name__ == "__main__":

    # load cache
    try:
        page_cache = pickle.load(open("page_cache.p", "rb"))
    except:
        print("No cache found")

    # modifie the starting id if you need the restart the program from a different location. eg. after a crash
    start_year = 2015
    years = 10

    type_list = ["Desktop", "Embedded", "Mobile", "Server"]

    # the file we are gonna write the gotten info, the file has the starting_id in it, in case starting
    # from somewhere else than the begining.
    output_file = "cpu-world_{0}_{1}.csv".format(start_year, start_year + years - 1)
    output = open(output_file, "w")

    # write header
    output.write(",".join(column_headers))
    output.write("\n")


    for type in type_list:
        # loop the games from starting_id to end.
        for year in range(start_year, start_year + years):

            baseurl = "http://www.cpu-world.com/Releases/{type}_CPU_releases_({id}).html".format(
                id=year, type=type
            )

            print(baseurl)

            # get the page, BS it, and get the pageinfo
            page_to_get = Scraper(baseurl, year, output)
            page_info = page_to_get.get_pageinfo(type)

            for page in page_info:
                output.write(page)
                output.write("\n")

    # close the file
    output.close()

    # save the cache
    pickle.dump(page_cache, open("page_cache.p", "wb"))

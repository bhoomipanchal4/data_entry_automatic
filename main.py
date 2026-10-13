from  bs4 import BeautifulSoup
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
import time
#Using BeautifulSoup
response = requests.get("https://appbrewery.github.io/Zillow-Clone/")
zillow_page = response.text

soup = BeautifulSoup(zillow_page,"html.parser")
link = soup.select("article div a")
price = soup.select(".PropertyCardWrapper span")
address = soup.select(".StyledPropertyCardDataWrapper address")
all_links  = []
all_prices = []
all_adresses = []

for l in link:
    new_link = l.get("href")
    all_links.append(new_link)

for p in price:
    p1= p.get_text()
    p2 = p1.replace("/mo","")
    p3 = p2.split("+")[0]
    p4 = p3.split("$")[1]
    all_prices.append(p4)

for d in address:
    d1 = d.get_text()
    d1 = d1.replace("\n","").strip()
    d1 = d1.replace("|","").strip()
    add = all_adresses.append(d1)

all_new_adress = [a for a in all_adresses]
all_new_price = [p for p in all_prices]
all_new_link = [l for l in all_links]




form_link = "https://docs.google.com/forms/d/e/1FAIpQLScUcz3a1hjnqu194hrzIvkiKEh9TMPIsQDShJE2-_fU0gfAWg/viewform?usp=header"
driver = webdriver.Chrome()



for i in range(44):
    driver.get(form_link)
    time.sleep(0.2)

    addresses = driver.find_element(By.XPATH,'//*[@id="mG61Hd"]/div[2]/div/div[2]/div[1]/div/div/div[2]/div/div[1]/div/div[1]/input')
    price = driver.find_element(By.XPATH,'//*[@id="mG61Hd"]/div[2]/div/div[2]/div[2]/div/div/div[2]/div/div[1]/div/div[1]/input')
    link = driver.find_element(By.XPATH,'//*[@id="mG61Hd"]/div[2]/div/div[2]/div[3]/div/div/div[2]/div/div[1]/div/div[1]/input')
    submit = driver.find_element(By.XPATH,'//*[@id="mG61Hd"]/div[2]/div/div[3]/div[1]/div[1]/div/span/span')


    addresses.send_keys(all_new_adress[i])
    price.send_keys(all_new_price[i])
    link.send_keys(all_new_link[i])
    submit.click()
    time.sleep(0.1)

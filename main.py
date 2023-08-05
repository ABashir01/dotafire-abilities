#TODO: Consider just storing ability value as one text field so that the game display is just: 1. ability values 2. hero 3. image 4. description
#TODO: I actually do want to change this: I want to store: 1. all ability values 2. Cooldown + Mana Costs 3. Hero 4. Description + Image
from bs4 import *
import requests
import psycopg2
import os
import json
import sys

# conn = psycopg2.connect(host="localhost", dbname="postgres", user="postgres", \
#                         password="Megladon.1", port=5432)
# cur = conn.cursor()

# Drop the existing abilities table if it exists
# try:
#     cur.execute("""DROP TABLE abilities;""")
# except:
#     pass

# # Creates a new "abilities" table
# cur.execute("""CREATE TABLE abilities(
#             id INT PRIMARY KEY, 
#             name VARCHAR(255),
#             hero VARCHAR(255),
#             hero_img VARCHAR(255), 
#             ability_img VARCHAR(255),
#             description TEXT,  
#             mana_cost VARCHAR(255), 
#             cooldown VARCHAR(255), 
#             range VARCHAR(255), 
#             damage VARCHAR(255),
#             damage_per_second VARCHAR(255),
#             healing VARCHAR(255));""")

# url = "https://www.dotafire.com/dota-2/skills"

# r = requests.get(url)
# soup = BeautifulSoup(r.text, "lxml")

# table_elements = soup.find_all("tr")[1:]

def soup_handler() -> list:
    url = "https://www.dotafire.com/dota-2/skills"

    r = requests.get(url)
    soup = BeautifulSoup(r.text, "lxml")

    return soup.find_all("tr")[1:]

def json_handler() -> dict:
    try:
        with open("connection_details.json", "r") as f:
            data = json.load(f)
            return data
    except Exception as e:
        print("Json File didn't work, error: ", e)
        sys.exit()

def download_images(url, folder, name) -> str:
    os.chdir(folder)
    file_name = name.replace(" ", "-") + ".jpg"
    
    if not os.path.exists(file_name):
        img_url = "https://www.dotafire.com" + url

        with open(file_name, "wb") as f:
            img_request = requests.get(img_url)
            f.write(img_request.content)

    os.chdir("..")
    return file_name

# Returns the curr_val of the itr and the value for the current abiliy value
def get_ability_values_helper(itr, main_div) -> list:
    ret = ""
    curr_itr = itr

    while True:
        curr_itr += 1
        
        ret += str(main_div[curr_itr].text.strip())

        # print(str(main_div[curr_itr].text))
        try:
            if curr_itr == len(main_div) or "\n" in  str(main_div[curr_itr+1].text) or "Cooldown Time" in str(main_div[curr_itr+1].text) or "Additional Information" in str(main_div[curr_itr+1].text):     
                break
        except IndexError as e:
            print(main_div)
            sys.exit()

    return [ret, curr_itr]  

def get_ability_values(url) -> dict:

    # ret = {"description": "N/A", 
    #        "mana_cost": "0", 
    #        "cooldown": "0", 
    #        "range": "0,", 
    #        "damage": "0",
    #        "damage_per_second": "0",
    #        "healing": "0"}

    ret = {"description": "N/A", 
           "ability_values": "N/A",
           "cooldown": "0",
           "mana_cost": "0"}

    ability_url = "https://www.dotafire.com" + url
    ability_request = requests.get(ability_url)
    ability_soup = BeautifulSoup(ability_request.text, "lxml")

    main_div = ability_soup.find("div", class_="box-t").contents
    desc_div = ability_soup.find("div", class_="mt10").contents

    ret["description"] = desc_div[0].strip()
    # print(desc_div)

    val_string = ""
    for i in range(4,len(desc_div)): #Start on the 4th index
        element = desc_div[i]

        if str(element) == '<br/>':
            val_string += ";;"
        
        else:
            val_string += element.text.strip()

    ret["ability_values"] = val_string

    itr = 0
    while True:
        itr += 1

        if "Mana Cost" in main_div[itr]:
            # print(main_div)
            helper_list = get_ability_values_helper(itr, main_div)
            ret["mana_cost"] = helper_list[0]
            itr = helper_list[1]

        elif "Cooldown Time" in main_div[itr]:
            helper_list = get_ability_values_helper(itr, main_div)
            ret["cooldown"] = helper_list[0]
            itr = helper_list[1]

        if itr + 1 == len(main_div):
            break
    
    return ret


def populate_table(table_elements, cur):

    for i in range(len(table_elements)):

        # This section gets me the ability and hero names: ---------------------
        names = table_elements[i].find_all('a')
        ability_name = names[0].text
        print(ability_name)
        hero_name = names[1]["alt"]
        if hero_name == "":
            continue
        # ----------------------------------------------------------------------

        # This section gets me the ability and hero images: --------------------            
        images = table_elements[i].find_all("img")
        ability_img_url = images[0]["src"]
        hero_img_url = images[1]["src"]
        ability_img = download_images(ability_img_url, "ability-images",\
                                       ability_name)
        hero_img = download_images(hero_img_url, "hero-images", hero_name)
        # ----------------------------------------------------------------------

        # This section gets me the ability values ------------------------------
        
        # This gives me the sub-url of the ability page
        ability_page_url = names[0]["href"] 

        ability_map = get_ability_values(ability_page_url)
        # ----------------------------------------------------------------------
        # print(ability_map)

        try:
            query = """INSERT INTO dota_2_abilities (id, name, hero, hero_img, 
                    ability_img, description, mana_cost, cooldown, ability_list) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);"""
            data = (i, ability_name, hero_name, hero_img, ability_img, 
                    ability_map["description"], ability_map["mana_cost"], 
                    ability_map["cooldown"], ability_map["ability_values"])
            cur.execute(query, data)
        except Exception as e:
            print("Insertion Failed: ", e)
            


def sql_handler():
    json_map = json_handler()
    conn = psycopg2.connect(host=json_map["host"], 
                                dbname=json_map["dbname"], 
                                user=json_map["user"], 
                                password=json_map["password"], 
                                port=json_map["port"])
    cur = conn.cursor()
    
    # Drop the existing abilities table if it exists
    try:
        cur.execute("""DROP TABLE dota_2_abilities;""")
    except Exception as e:
        print("Didn't drop table", e)
        conn = psycopg2.connect(host=json_map["host"], 
                                dbname=json_map["dbname"], 
                                user=json_map["user"], 
                                password=json_map["password"], 
                                port=json_map["port"])
        cur = conn.cursor()
        # conn.rollback()

    # Creates a new "abilities" table
    try:
        cur.execute("""CREATE TABLE dota_2_abilities(
                            id INT PRIMARY KEY, 
                            name VARCHAR(255),
                            hero VARCHAR(255),
                            hero_img TEXT, 
                            ability_img TEXT,
                            description TEXT,  
                            mana_cost VARCHAR(255), 
                            cooldown VARCHAR(255), 
                            ability_list TEXT);""")
    except Exception as e:
        print("There was a SQL issue: ", e)
    
    table_elements = soup_handler()

    populate_table(table_elements, cur)

    conn.commit()

    cur.close()
    conn.close()

    print("Running successful")

        

# populate_table()

# conn.commit()

# cur.close()
# conn.close()

if __name__ == "__main__":
    sql_handler()
from tabula.io import read_pdf
import sqlite3
import pandas as pd
import numpy as np
import csv

def create_table():
    pages = [i for i in range(37, 64)]

    table = read_pdf("JICReport2025.pdf", pages=pages)

    table = pd.concat(table)
    table = table.to_numpy()

    with open("trial.csv", "w") as f:
        writer = csv.writer(f)
        for row in table:
            writer.writerow(row)

def sql_db_enter():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("CREATE TABLE center_code_data (center_code INTEGER, city VARCHAR, state VARCHAR)")

    with open("trial.csv", "r") as f:
        reader = csv.reader(f)
        for row in reader:
            if row != []:
                cursor.execute(f"INSERT INTO center_code_data VALUES ({row[0]}, '{row[3]}', '{row[4]}')")

    conn.commit()

def get_state_city(code):
    conn = sqlite3.connect("database.db")
    cursors = conn.cursor()

    cursors.execute(f"SELECT * FROM center_code_data WHERE center_code == {code}")

    results = cursors.fetchone()

    return results

#Function to get all allocated roll no and then map them to their cities and state
#First we get the crls and the city n state in a csv before uploading to the DB for saity sake :)
def crl_vs_state():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("CREATE TABLE roll_with_state (roll VARCHAR, city VARCHAR, state VARCHAR)")



    with open("trial.csv", "r") as f1:
        with open("secondary.csv", "w") as f:
            writer = csv.writer(f)
            reader = csv.reader(f1)
            for row in reader:
                if row != []:
                    rank1 = row[1]
                    rank2 = row[5]

                    citycode1 = rank1[2: 6]
                    citycode2 = rank2[2:6]

                    city_details1 = get_state_city(citycode1)
                    city_details2 = get_state_city(citycode2)
                    city_details1 = [rank1, city_details1[1], city_details1[2]]
                    city_details2 = [rank2, city_details2[1], city_details2[2]]

                    cursor.execute(f"INSERT INTO roll_with_state VALUES ('{city_details1[0]}', '{city_details1[1]}', '{city_details1[2]}')")
                    cursor.execute(f"INSERT INTO roll_with_state VALUES ('{city_details2[0]}', '{city_details2[1]}', '{city_details2[2]}')")

    conn.commit()


crl_vs_state()
import sqlite3
import os
import re


def initialize_db():
    if(not os.path.exists("database.db")):

        conn = sqlite3.connect("database.db")

        with open("schema.sql", "r") as f:
            sql_script = f.read()

        conn.executescript(sql_script)
        conn.commit()
        conn.close()

def get_insti_type(insti_name):
    insti_name = re.sub(r"\s+", " ", insti_name).strip().upper()
    if "INDIAN INSTITUTE OF TECHNOLOGY" in insti_name:
        return "IIT"
    elif "NATIONAL INSTITUTE OF TECHNOLOGY" in insti_name:
        return "NIT"
    # Detect IIIT explicitly
    elif "INDIAN INSTITUTE OF INFORMATION TECHNOLOGY" in insti_name or re.search(r"\bIIIT\b", insti_name):
        return "IIIT"
    else:
        return "OTHER"

def get_or_create_dim(cursor, table, index_col, value_col, data_val):
    cursor.execute(f"SELECT {index_col} FROM {table} WHERE {value_col} = ?", (data_val,))

    result = cursor.fetchone()

    if result is not None:
        return result[0]
    else:
        cursor.execute(f"INSERT INTO {table} ({value_col}) VALUES (?)", (data_val,))
        return cursor.lastrowid
    
def store_data_entry(all_data):

    initialize_db()

    connection = sqlite3.connect("database.db")
    cursor = connection.cursor()

    for row_entry in all_data:

        print("ROW ENTRY: ", row_entry)

        insti_name = row_entry[0]
        acad_program = row_entry[1]
        quota_val = row_entry[2]
        cat_val = row_entry[3]
        gender_val = row_entry[4]
        opening_rank = row_entry[5]
        closing_rank = row_entry[6]
        round = row_entry[7]
        year = row_entry[8]

        insti_type = get_insti_type(insti_name)


        insti_index = get_or_create_dim(cursor, 'Dim_InstiName', 'insti_index', 'insti_value', insti_name)
        insti_type_index = get_or_create_dim(cursor, "Dim_InstiType", "insti_type_index", "insti_type", insti_type)
        acad_program_index = get_or_create_dim(cursor, "Dim_AcadProgram", "acad_prog_index", "acad_prog_value", acad_program)
        quota_index = get_or_create_dim(cursor, "Dim_Quota", "quota_index", "quota_value", quota_val)
        cat_index = get_or_create_dim(cursor, "Dim_Category", "cat_index", "cat_value", cat_val)
        gender_index = get_or_create_dim(cursor, "Dim_Gender", "gender_index", "gender_value", gender_val)

        cursor.execute("INSERT INTO FactsTable (year, round, insti_index, insti_type_index, quota_index, gender_index, cat_index, acad_prog_index, opening_rank, closing_rank) VALUES(?,?,?,?,?,?,?,?,?,?)", (year, round, insti_index, insti_type_index, quota_index, gender_index, cat_index, acad_program_index, opening_rank, closing_rank))
    connection.commit()
    connection.close()

import numpy as np
import pandas as pd
import csv
import sqlite3
from tabula.io import read_pdf


def create_csv():
    pages = [508, 509]
    allotted_crl_table = read_pdf("JICReport2025.pdf", pages = pages, multiple_tables=True)

    combined_tables = pd.concat(allotted_crl_table, ignore_index=True)
    combined_tables = combined_tables.to_numpy()

    with open("trial.csv", "w") as f:
        writer = csv.writer(f)
        for i in combined_tables:
            writer.writerow(i)


create_csv()
--Using Star schema to prevent storing big insti names multiple times. No need dimension tables for round and year cuz obvisouly no use.
--Mainly for institute name, gender, institute type, quato and category and academic programme we need these tables.

CREATE TABLE Dim_InstiName(
    insti_index INTEGER PRIMARY KEY AUTOINCREMENT,
    insti_value VARCHAR(300)
);

CREATE TABLE Dim_InstiType(
    insti_type_index INTEGER PRIMARY KEY AUTOINCREMENT,
    insti_type VARCHAR(300)
);

CREATE TABLE Dim_Quota(
    quota_index INTEGER PRIMARY KEY AUTOINCREMENT,
    quota_value VARCHAR(300)
);

CREATE TABLE Dim_Gender(
    gender_index INTEGER PRIMARY KEY AUTOINCREMENT,
    gender_value VARCHAR(300)
);

CREATE TABLE Dim_Category(
    cat_index INTEGER PRIMARY KEY AUTOINCREMENT,
    cat_value VARCHAR(300)
);

CREATE TABLE Dim_AcadProgram(
    acad_prog_index INTEGER PRIMARY KEY AUTOINCREMENT,
    acad_prog_value VARCHAR(300)
);

--Creating the main facts table
CREATE TABLE FactsTable (
    year INTEGER,
    round INTEGER,
    insti_index INTEGER,
    insti_type_index INTEGER,
    quota_index INTEGER,
    gender_index INTEGER,
    cat_index INTEGER,
    acad_prog_index INTEGER,
    opening_rank INTEGER,
    closing_rank INTEGER,

    FOREIGN KEY (insti_index) REFERENCES Dim_InstiName(insti_index),
    FOREIGN KEY (insti_type_index) REFERENCES Dim_InstiType(insti_type_index),
    FOREIGN KEY (quota_index) REFERENCES Dim_Quota(quota_index),
    FOREIGN KEY (gender_index) REFERENCES Dim_Gender(gender_index),
    FOREIGN KEY (cat_index) REFERENCES Dim_Category(cat_index),
    FOREIGN KEY (acad_prog_index) REFERENCES Dim_AcadProgram(acad_prog_index)

);
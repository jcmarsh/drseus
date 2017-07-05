# coding=UTF-8
# This coding is used so I can have my default value below :)

import sqlite3
import os # Used for delete the database at the end of the test

# Overview of all datatypes that are supported by SQLite3:
#     INTEGER: A signed integer up to 8 bytes depending on the magnitude of the value.
#     REAL: An 8-byte floating point value.
#     TEXT: A text string, typically UTF-8 encoded (depending on the database encoding).
#     BLOB: A blob of data (binary large object) for storing binary data.
#     NULL: A NULL value, represents missing data or an empty cell.

# Note on PRIMARY KEYs:
#     The advantage of a PRIMARY KEY index is a significant performance gain if we use
#     the PRIMARY KEY column as query for accessing rows in the table. Every table can
#     only have max. 1 PRIMARY KEY (single or multiple column(s)), and the values in
#     this column MUST be unique


test_db = "test_db.sqlite"

# -----------------------------------------------------------------------------------------

# TEST creating a new db file and opening it
conn = sqlite3.connect(test_db)
# Another option is to use: .connect(':memory:') to run a db just in RAM memory
# Just be sure it is small enough. See: https://www.sqlite.org/inmemorydb.html for more info

# If we performed any operation on the database other than sending queries, we need
#     to commit those changes via the .commit() method before we close the connection
conn.close()

# -----------------------------------------------------------------------------------------

# TEST creating db file with two tables, one w/ and one w/o a PRIMARY KEY column
table_name1 = "my_table_1"
table_name2 = "my_table_2"
new_field = "my_1st_column" # Column name
field_type = "INTEGER" # Column data type

conn = sqlite3.connect(test_db)
c = conn.cursor() # object to interact with the database, can call execute

# Create a new SQLite table with 1 column
c.execute('CREATE TABLE {tn} ({nf} {ft})'\
    .format(tn=table_name1, nf=new_field, ft=field_type))

# Create a new SQLite table with 1 column and set it as PRIMARY KEY
#     note that PRIMARY KEY column must consist of unique values!
c.execute('CREATE TABLE {tn} ({nf} {ft} PRIMARY KEY)'\
    .format(tn=table_name2, nf=new_field, ft=field_type))

conn.commit()
conn.close()

# -----------------------------------------------------------------------------------------

# TEST add a new column

new_column = "my_new_column"
column_type = "TEXT"
default_val = "( ͡° ͜ʖ ͡°)"
my_table = table_name2

conn = sqlite3.connect(test_db)
c = conn.cursor()

c.execute("ALTER TABLE {tn} ADD COLUMN '{nc}' DEFAULT '{dv}'"\
    .format(tn=my_table, nc=new_column, dv=default_val))

conn.commit()
conn.close()

# -----------------------------------------------------------------------------------------

# TEST inserting and updating rows

id_column = new_field # From the first test, the column defined as the PRIMARY KEY in my_table
text_column = new_column

conn = sqlite3.connect(test_db)
c = conn.cursor()

# Inserts an ID with a specific value into a column
try:
    c.execute("INSERT INTO {tn} ({c1}, {c2}) VALUES (1, 'test')"\
        .format(tn=my_table, c1=id_column, c2=text_column))
    c.execute("INSERT INTO {tn} ({c1}) VALUES (2)"\
        .format(tn=my_table, c1=id_column, c2=text_column))
except sqlite3.IntegrityError:
    print("ERROR: ID already exists in PRIMARY KEY column {}".format(id_column))

# Updates a pre-existing entry, little backwards because we are changing the PRIMARY KEY with
# a non PRIMARY KEY in this example
c.execute("UPDATE {tn} SET {c1}=(101) WHERE {c2}=('test')"\
    .format(tn=my_table, c1=id_column, c2=text_column))

conn.commit()
conn.close()

# -----------------------------------------------------------------------------------------

# TEST creating unique indexes
# TODO, unique indexes are used to access specific elements within a certain column
# PRIMARY KEY is an example of a unique index, we are able to add more

# -----------------------------------------------------------------------------------------

# TEST querying the database = selecting rows

conn = sqlite3.connect(test_db)
c = conn.cursor()

# Contents of all columns for row that match a certain value in 1 column
c.execute("SELECT * FROM {tn} WHERE {cn}='test'"\
    .format(tn=my_table, cn=text_column))
all_rows = c.fetchall()
print("1): " + str(all_rows))

c.execute("SELECT * FROM {tn} WHERE {cn}=(2)"\
    .format(tn=my_table, cn=id_column))
all_rows = c.fetchall()
print("2): " + str(all_rows))

# More examples found online

conn.close()

# -----------------------------------------------------------------------------------------

# Test printing a database summary

def connect(sqlite_file):
    """ Make connection to an SQLite database file """
    conn = sqlite3.connect(sqlite_file)
    c = conn.cursor()
    return conn, c

def close(conn):
    """ Commit changes and close connection to the database """
    # conn.commit()
    conn.close()

def total_rows(cursor, table_name, print_out=False):
    """ Returns the total number of rows in the database """
    cursor.execute('SELECT COUNT(*) FROM {}'.format(table_name))
    count = cursor.fetchall()
    if print_out:
        print('\nTotal rows: {}'.format(count[0][0]))
    return count[0][0]

def table_col_info(cursor, table_name, print_out=False):
    """ Returns a list of tuples with column informations:
        (id, name, type, notnull, default_value, primary_key)
    """
    cursor.execute('PRAGMA TABLE_INFO({})'.format(table_name))
    info = cursor.fetchall()

    if print_out:
        print("\nColumn Info:\nID, Name, Type, NotNull, DefaultVal, PrimaryKey")
        for col in info:
            print(col)
    return info

def values_in_col(cursor, table_name, print_out=True):
    """ Returns a dictionary with columns as keys and the number of not-null
        entries as associated values.
    """
    cursor.execute('PRAGMA TABLE_INFO({})'.format(table_name))
    info = cursor.fetchall()
    col_dict = dict()
    for col in info:
        col_dict[col[1]] = 0
    for col in col_dict:
        cursor.execute('SELECT ({0}) FROM {1} WHERE {0} IS NOT NULL'.format(col, table_name))
        # In my case this approach resulted in a better performance than using COUNT
        number_rows = len(cursor.fetchall())
        col_dict[col] = number_rows
    if print_out:
        print("\nNumber of entries per column:")
        for i in col_dict.items():
            print('{}: {}'.format(i[0], i[1]))
    return col_dict

conn, c = connect(test_db)

total_rows(c, my_table, print_out=True)
table_col_info(c, my_table, print_out=True)
values_in_col(c, my_table, print_out=True) # Slow on large data bases

close(conn)

# -----------------------------------------------------------------------------------------

# Remove database file
os.remove(test_db)

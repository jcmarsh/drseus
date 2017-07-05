from os import makedirs, remove
from os.path import isfile
from termcolor import colored, cprint
from sqlite3 import connect

from .database import get_campaign

def delete_sqlite_database(sqlite_database):
    cprint("Removing " + sqlite_database.database, 'red')
    remove(sqlite_database.database)

def assembly_golden_run(sqlite_database):
    #TODO
    pass

def print_sqlite_database(sqlite_database):
    conn = connect(sqlite_database.database)
    c = conn.cursor()
    print(colored("\n+++++++++++++++++++++++++++++++++++++++++++++++++++++++++\n", 'yellow'))

    for tn in sqlite_database.table_list:
        c.execute("PRAGMA TABLE_INFO({})".format(tn))
        info = c.fetchall()

        # Loop through once before printing to determine table dimensions
        row_spacing = 19
        len_y = 1 # Initial |
        for col in info:
            len_y += row_spacing + 1 # Extra 1 is for the | that comes with each new column
        len_x = (int)((len_y - len(str(tn))) / 2)
        len_z = len_x + len_x + len(str(tn))

        print(((len_x-1) * '-') + '_' + str(tn) + '_' + ((len_x-1) * '-'))

        # Print the column names
        for col in info:
            print('|', end="")
            print(" " + str(col[1]) + (row_spacing - len(str(col[1])) - 1) * " ", end="")
        print('|')

        # Print rows
        c.execute("SELECT * FROM {}".format(tn))
        all_rows = c.fetchall()
        for row in all_rows:
            i = 0
            while(i < len(row)):
                print('|', end="")
                print(" " + str(row[i]) + (row_spacing - len(str(row[i])) - 1) * " ", end="")
                i += 1
            print('|')

        print(len_z * '-')

    print(colored("\n+++++++++++++++++++++++++++++++++++++++++++++++++++++++++\n", 'yellow'))
    conn.close()

class sqlite_database(object):
    def __init__(self, options):
        self.options = options
        self.campaign = get_campaign(options)
        self.database = self.__create_database()
        self.__initialize_database()

    def __create_database(self):
        print(colored("Creating sqlite database", 'yellow'))
        sqlite_folder = 'campaign-data/{}/sqlite'.format(self.campaign.id)
        database = sqlite_folder + '/' + 'database.sqlite'
        if isfile(database):
             print(colored("Sqlite database already exists for this campaign", 'red'))
             return
        makedirs(sqlite_folder)
        conn = connect(database)
        conn.close()
        print(colored("database: " + database, 'yellow'))
        return database

    def __initialize_database(self):
        print(colored("\tInitializing database...", 'yellow'))

        # Fields for the Assmbly table
        self.asm_tbl         = "assembly_table"
        self.address_col     = "address" # PRIMARY KEY
        address_type         = "INTEGER"
        self.list_cycles_col = "cycles_list"
        list_cycles_type     = "TEXT"

        # Fields for the load / store table
        self.ldstr_tbl      = "loadstore_table"
        self.cache_col      = "cache_line"
        cache_type          = "INTEGER"
        self.cycle_col      = "cycles"
        cycle_type          = "INTEGER"
        self.ldstr_col      = "load_or_store"
        ldstr_type          = "INTEGER"
        self.ldstr_addr_col = "loadstore_address"
        ldstr_addr_type     = "INTEGER"

        #Save the tables in a list to make printing and changing the database easier
        self.table_list = [self.asm_tbl, self.ldstr_tbl]

        conn = connect(self.database)
        c = conn.cursor()

        # Add to database
        c.execute('CREATE TABLE {tn} ({c1} {t1} PRIMARY KEY, {c2} {t2})'\
            .format(tn=self.asm_tbl,\
            c1=self.address_col, t1=address_type,\
            c2=self.list_cycles_col, t2=list_cycles_type))

        c.execute('CREATE TABLE {tn} ({c1} {t1}, {c2} {t2} PRIMARY KEY, {c3} {t3}, {c4} {t4})'\
            .format(tn=self.ldstr_tbl,\
            c1=self.cache_col, t1=cache_type,\
            c2=self.cycle_col, t2=cycle_type,\
            c3=self.ldstr_col, t3=ldstr_type,\
            c4=self.ldstr_addr_col, t4=ldstr_addr_type))

        conn.commit()
        conn.close()

    def __create_reslut(self):
        #TODO
        pass

    def log_asm(self, address, cycles):
        #TODO
        # Modify the Assembly Table
        # Search to see if address already is in the assembly table
        # If it is, update cycle list to contain the new entry
        # If it is not, add the new entry
        pass

    def log_ldstr(self, cache, cycles, ldstr, ldstr_addr):
        # Modify the Load/Store Table
        conn = connect(self.database)
        c = conn.cursor()

        # Make sure that cycles is unique
        c.execute("SELECT * FROM {tn} WHERE {cn}=({val})"\
             .format(tn=self.ldstr_tbl, cn=self.cycle_col, val=cycles))
        if c.fetchone() != None:
            conn.close()
            cprint("Conflict in log_ldstr, cycles collision", 'red')
            cprint("Exiting")
            exit()

        c.execute("INSERT INTO {tn} ({c1}, {c2}, {c3}, {c4}) VALUES ({t1}, {t2}, {t3}, {t4})"
            .format(tn=self.ldstr_tbl,
            c1=self.cache_col, c2=self.cycle_col, c3=self.ldstr_col, c4=self.ldstr_addr_col,\
            t1=cache, t2=cycles, t3=ldstr, t4=ldstr_addr))

        conn.commit()
        conn.close()

import subprocess
import re
from os import makedirs, remove
from os.path import isfile
from termcolor import colored, cprint
from sqlite3 import connect
from .dut import dut
from time import sleep

from .database import get_campaign

def delete_sqlite_database(sqlite_database):
    cprint("Removing " + sqlite_database.database, 'red')
    remove(sqlite_database.database)

def assembly_golden_run(sqlite_database, dut):
    cprint("Running assembly golden run", 'yellow')
    # Get assembly instrucitons into raw files
    p = subprocess.Popen('cd ../scripts/;./start_asm_golden_run.sh', shell=True)
    p.communicate()
    p.kill()
    cprint("Begin parsing, this may take a few minutes...", 'yellow')
    cprint("\tStoring load and store instructions...", 'yellow')
    with open("../etc/ldstr.txt") as ldstr:
        for line in ldstr:

            inst_addr = subprocess.check_output("echo " + "\"" + str(line) + "\"" + " | awk '{ print $1 }'", shell=True)
            inst_addr = str(inst_addr).lstrip("b\'")
            inst_addr = str(inst_addr).rstrip(":\\n\\n\'")
            #print(inst_addr)

            cache = -1
            cycles = -1

            ldstr_str = subprocess.check_output("echo " + "\"" + str(line) + "\"" + " | awk '{ print $3 }'", shell=True)
            ldstr_str = str(ldstr_str).lstrip("b\'")
            ldstr_str = str(ldstr_str).rstrip(":\\n\\n\'")
            #TODO add in check to make sure the command always starts with st or ld
            if re.match('st', ldstr_str) is not None:
                ldstr = 1
            else:
                ldstr = 0
            #print(ldstr_str + ", value is: " + str(ldstr))

            ldstr_addr = -1

            sqlite_database.log_ldstr(inst_addr, cache, cycles, ldstr, ldstr_addr)
    cprint("\tStoring branch instructions...", 'yellow')
    with open("../etc/branch.txt") as ldstr:
        for line in ldstr:

            inst_addr = subprocess.check_output("echo " + "\"" + str(line) + "\"" + " | awk '{ print $1 }'", shell=True)
            inst_addr = str(inst_addr).lstrip("b\'")
            inst_addr = str(inst_addr).rstrip(":\\n\\n\'")
            #print(inst_addr)

            inst_name = subprocess.check_output("echo " + "\"" + str(line) + "\"" + " | awk '{ print $3 }'", shell=True)
            inst_name = str(inst_name)[2:-5]
            #print(inst_name)

            sqlite_database.log_branch(inst_addr, inst_name)


    print_sqlite_database(sqlite_database)
    cprint("Done", 'yellow')

    cprint("Transfering database to embedded board...", 'yellow')
    cprint("\tGetting username and ip...", 'yellow')

    username = subprocess.check_output("cat ../login_info | awk -F = '/user/{ print $2 }'", shell=True)
    username = str(username)[2:-3]
    cprint("\t\tusername: " + username, 'yellow')

    ip = subprocess.check_output("cat ../login_info" + " | awk -F = '/ip/{ print $2 }'", shell=True)
    ip = str(ip)[2:-3]
    cprint("\t\tip: " + ip, 'yellow')

    localpath = sqlite_database.database
    p = subprocess.Popen("scp " + localpath + " " + username + "@" + ip + ":~/jtag_eval/openOCD_cfg/mnt", shell=True)
    p.communicate()
    p.kill()

    # Let Zybo run until control is read
    p = subprocess.Popen('cd ../scripts/;./start.sh', shell=True)
    dut.read_until("control ", False, False, True)
    p.kill()

    # Halt Zybo from running any further
    p = subprocess.Popen('cd ../scripts/;./halt.sh', shell=True)
    sleep(1)
    p.communicate()
    p.kill()

    # Run on the database
    command = " 'cd ./jtag_eval/openOCD_cfg/mnt;python ./asm_golden_run.py'"
    p = subprocess.Popen("x-terminal-emulator -e \"ssh " + username + "@" + ip + command + "\"", shell=True)
    # Run until program is done
    dut.read_until()
    p.kill()

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

        self.branch_tbl      = "branch_table"
        self.address_col     = "address" # PRIMARY KEY
        address_type         = "TEXT"
        self.inst_name_col   = "instruction_name"
        inst_name_type       = "TEXT"

        # Fields for the load / store table
        self.ldstr_tbl      = "loadstore_table"
        # This table too uses address columns
        #self.address_col   = "address" # PRIMARY KEY
        #address_type       = "INTEGER"
        self.cache_col      = "cache_line"
        cache_type          = "INTEGER"
        self.cycles_col     = "cycles"
        cycles_type         = "BLOB"
        self.ldstr_col      = "load0_store1"
        ldstr_type          = "INTEGER"
        self.ldstr_addr_col = "loadstore_address"
        ldstr_addr_type     = "TEXT"

        #Save the tables in a list to make printing and changing the database easier
        self.table_list = [self.branch_tbl, self.ldstr_tbl]

        conn = connect(self.database)
        c = conn.cursor()

        # Add to database
        c.execute('CREATE TABLE {tn} ({c1} {t1} PRIMARY KEY, {c2} {t2})'\
            .format(tn=self.branch_tbl,\
            c1=self.address_col, t1=address_type,\
            c2=self.inst_name_col, t2=inst_name_type))

        c.execute('CREATE TABLE {tn} ({c1} {t1} PRIMARY KEY, {c2} {t2}, {c3} {t3}, {c4} {t4}, {c5} {t5})'\
            .format(tn=self.ldstr_tbl,\
            c1=self.address_col, t1=address_type,\
            c2=self.cache_col, t2=cache_type,\
            c3=self.cycles_col, t3=cycles_type,\
            c4=self.ldstr_col, t4=ldstr_type,\
            c5=self.ldstr_addr_col, t5=ldstr_addr_type))

        conn.commit()
        conn.close()

    def __create_reslut(self):
        #TODO
        pass

    def log_branch(self, inst_addr, inst_name):
        conn = connect(self.database)
        c = conn.cursor()

        # Make sure that cycles is unique
        c.execute("SELECT * FROM {tn} WHERE {cn}=('{val}')"\
             .format(tn=self.branch_tbl, cn=self.address_col, val=str(inst_addr)))
        if c.fetchone() != None:
            conn.close()
            cprint("Conflict in log_branch, primary key instruction address collision", 'red')
            cprint("Exiting")
            exit()

        c.execute("INSERT INTO {tn} ({c1}, {c2}) VALUES ('{t1}', '{t2}')"
             .format(tn=self.branch_tbl,
             c1=self.address_col, c2=self.inst_name_col, \
             t1=str(inst_addr), t2=str(inst_name)))

        conn.commit()
        conn.close()

    def log_ldstr(self, inst_addr, cache, cycles, ldstr, ldstr_addr):
        conn = connect(self.database)
        c = conn.cursor()

        # Make sure that cycles is unique
        c.execute("SELECT * FROM {tn} WHERE {cn}=('{val}')"\
             .format(tn=self.ldstr_tbl, cn=self.address_col, val=str(inst_addr)))
        if c.fetchone() != None:
            conn.close()
            cprint("Conflict in log_ldstr, primary key instruction address collision", 'red')
            cprint("Exiting")
            exit()

        c.execute("INSERT INTO {tn} ({c1}, {c2}, {c3}, {c4}, {c5}) VALUES ('{t1}', {t2}, {t3}, {t4}, '{t5}')"
             .format(tn=self.ldstr_tbl,
             c1=self.address_col, c2=self.cache_col, c3=self.cycles_col, c4=self.ldstr_col, c5=self.ldstr_addr_col,\
             t1=str(inst_addr), t2=cache, t3=cycles, t4=ldstr, t5=str(ldstr_addr)))

        conn.commit()
        conn.close()

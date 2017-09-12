import subprocess
import re
from os import makedirs, remove
from os.path import isfile
from termcolor import colored, cprint
from sqlite3 import connect
from .jtag.openocd import openocd
from time import sleep

from .database import get_campaign

def get_database_path(options):
    database = "campaign-data/" + str(options.campaign_id) + "/sqlite/database.sqlite"
    return database

def delete_sqlite_database(sqlite_database):
    cprint("Removing " + sqlite_database.database, 'red')
    remove(sqlite_database.database)

def record_tags(sqlite_database):
    with open("../etc/tags.txt") as tags:
        lines = tags.readlines()
# '{} {}'.format('one', 'two')
        start_addr = '0x{}'.format(lines[0].strip())
        end_addr = '0x{}'.format(lines[1].strip())
        sqlite_database.log_tags(start_addr, end_addr)

def assembly_golden_run(sqlite_database, debugger):
    cprint("Running assembly golden run", 'yellow')
    cprint("Begin parsing, this may take a few minutes...", 'yellow')
    cprint("\tStoring load and store instructions...", 'yellow')
    with open("../etc/ldstr.txt") as ldstr:
        for line in ldstr:

            inst_addr = subprocess.check_output("echo " + "\"" + str(line) + "\"" + " | awk '{ print $1 }'", shell=True)
            inst_addr = str(inst_addr).lstrip("b\'")
            inst_addr = str(inst_addr).rstrip(":\\n\\n\'")
            #print(inst_addr)

            hex_addr = int(inst_addr, 16)
            bin_addr = bin(hex_addr)
            bin_addr = bin_addr[:-5]
            bin_addr = bin_addr[-11:]
            bin_addr = int(bin_addr, 2)
            cache = int(str(bin_addr), 10)

            cycles_diff = '-1'
            cycles_total = '-1'

            ldstr_str = subprocess.check_output("echo " + "\"" + str(line) + "\"" + " | awk '{ print $3 }'", shell=True)
            ldstr_str = str(ldstr_str).lstrip("b\'")
            ldstr_str = str(ldstr_str).rstrip(":\\n\\n\'")
            if re.match('st', ldstr_str) is not None or re.match('push', ldstr_str):
                ldstr = 1
            else:
                ldstr = 0
            #print(ldstr_str + ", is a: " + str(ldstr))

            ldstr_addr = -1

            sqlite_database.log_ldstr(inst_addr, cache, cycles_diff, cycles_total, ldstr, ldstr_addr, ldstr_str)
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
    #p.kill()

    # Start zybo but halt at the drseus_sync_tag label address
    start_addr = sqlite_database.get_start_addr()
    print("Start and end tag addresses", start_addr, sqlite_database.get_end_addr())
    debugger.break_dut(start_addr)

    # TODO: remove sleep?
    sleep(1)

    # Run on the database
    print("Running asm_golden_run.py")
    command = " 'cd ./jtag_eval/openOCD_cfg/mnt;python ./asm_golden_run.py'"
    p = subprocess.Popen("x-terminal-emulator -e \"ssh " + username + "@" + ip + command + "\"", shell=True)
    # Run until program is done
    debugger.dut.read_until()
    subprocess.call("ssh " + username + "@" + ip + " 'touch ~/jtag_eval/openOCD_cfg/mnt/done'", shell=True)
    p.communicate()

    # Transfer back updated database
    print("Transfering back database")
    p = subprocess.Popen("scp " + username + "@" + ip + ":~/jtag_eval/openOCD_cfg/mnt/database.sqlite " + localpath, shell=True)
    p.communicate()
    #p.kill()

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
    def __init__(self, options, database_path=None):
        self.options = options
        self.campaign = get_campaign(options)
        #TODO check to make sure the database still exists
        self.__initialize_params()
        if database_path is not None:
            self.database = database_path
        else:
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

    def __initialize_params(self):
        self.branch_tbl      = "branch_table"
        self.address_col     = "address" # PRIMARY KEY
        self.address_type    = "TEXT"
        self.inst_name_col   = "instruction_name"
        self.inst_name_type  = "TEXT"

        # Fields for the load / store table
        self.ldstr_tbl         = "loadstore_table"
        # This table uses address columns too
        #self.address_col      = "address" # PRIMARY KEY
        #address_type          = "INTEGER"
        self.cache_set_col     = "cache_set"
        self.cache_set_type    = "INTEGER"
        self.cycles_total_col  = "cycles_total"
        self.cycles_total_type = "TEXT"
        self.cycles_diff_col   = "cycles_diff"
        self.cycles_diff_type  = "TEXT"
        self.ldstr_col         = "load0_store1"
        self.ldstr_type        = "INTEGER"
        self.ldstr_addr_col    = "loadstore_address"
        self.ldstr_addr_type   = "TEXT"
        #self.inst_name_col    = "instruction_name"
        #self.inst_name_type   = "TEXT"

        # Execution information for injection (start and stop cycle counts)
        self.inject_tbl        = "injection_info_table"
        self.id_col            = "id"
        self.id_type           = "INTEGER"
        self.start_addr_col    = "start_tag_address"
        self.start_addr_type   = "TEXT"
        self.start_cycle_col   = "start_cycle"
        self.start_cycle_type  = "INTEGER"
        self.end_addr_col      = "end_tag_address"
        self.end_addr_type     = "TEXT"
        self.end_cycle_col     = "end_cycle"
        self.end_cycle_type    = "INTEGER"

        #Save the tables in a list to make printing and changing the database easier
        self.table_list = [self.branch_tbl, self.ldstr_tbl, self.inject_tbl]

    def __initialize_database(self):
        print(colored("\tInitializing database...", 'yellow'))

        conn = connect(self.database)
        c = conn.cursor()

        # Add to database
        c.execute('CREATE TABLE {tn} ({c1} {t1} PRIMARY KEY, {c2} {t2})'\
            .format(tn=self.branch_tbl,\
            c1=self.address_col, t1=self.address_type,\
            c2=self.inst_name_col, t2=self.inst_name_type))

        c.execute('CREATE TABLE {tn} ({c1} {t1} PRIMARY KEY, {c2} {t2}, {c3} {t3}, {c4} {t4}, {c5} {t5})'\
            .format(tn=self.inject_tbl,\
                    c1=self.id_col, t1=self.id_type,\
                    c2=self.start_addr_col, t2=self.start_addr_type,\
                    c3=self.start_cycle_col, t3=self.start_cycle_type,\
                    c4=self.end_addr_col, t4=self.end_addr_type,\
                    c5=self.end_cycle_col, t5=self.end_cycle_type))

        c.execute('CREATE TABLE {tn} ({c1} {t1} PRIMARY KEY, {c2} {t2}, {c3} {t3}, {c4} {t4}, {c5} {t5}, {c6} {t6}, {c7} {t7})'\
            .format(tn=self.ldstr_tbl,\
            c1=self.address_col, t1=self.address_type,\
            c2=self.cache_set_col, t2=self.cache_set_type,\
            c3=self.cycles_diff_col, t3=self.cycles_diff_type,\
            c4=self.cycles_total_col, t4=self.cycles_total_type,\
            c5=self.ldstr_col, t5=self.ldstr_type,\
            c6=self.ldstr_addr_col, t6=self.ldstr_addr_type,\
            c7=self.inst_name_col, t7=self.inst_name_type))

        conn.commit()
        conn.close()

    def __create_reslut(self):
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

    def log_ldstr(self, inst_addr, cache, cycles_diff, cycles_total, ldstr, ldstr_addr, inst_name):
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

        c.execute("INSERT INTO {tn} ({c1}, {c2}, {c3}, {c4}, {c5}, {c6}, {c7}) VALUES ('{t1}', {t2}, {t3}, {t4}, {t5}, '{t6}', '{t7}')"
             .format(tn=self.ldstr_tbl,
             c1=self.address_col, c2=self.cache_set_col, c3=self.cycles_diff_col, c4=self.cycles_total_col, c5=self.ldstr_col, c6=self.ldstr_addr_col, c7=self.inst_name_col,\
             t1=str(inst_addr), t2=cache, t3=cycles_diff, t4=cycles_total, t5=ldstr, t6=str(ldstr_addr), t7=inst_name))

        conn.commit()
        conn.close()

    def log_tags(self, start_addr, end_addr):
        print("Adding start and end tag addresses.", start_addr, end_addr)
        conn = connect(self.database)
        c = conn.cursor()

        c.execute("INSERT INTO {} (\"{}\", \"{}\") VALUES ('{}', '{}')".format(self.inject_tbl, self.start_addr_col, self.end_addr_col, start_addr, end_addr))

        conn.commit()
        conn.close()

    def log_start_end(self, start_cycle, end_cycle):
        print("Adding start and end cycle counts.", start_cycle, end_cycle)
        conn = connect(self.database)
        c = conn.cursor()

        c.execute("UPDATE {} SET {} = {}, {} = {} WHERE {} = {}".format(self.inject_tbl, self.start_cycle_col, start_cycle, self.end_cycle_col, end_cycle, self.id_col, 1))

        conn.commit()
        conn.close()

    def get_start_addr(self):
        conn = connect(self.database)
        c = conn.cursor()

        c.execute("SELECT {} FROM {}".format(self.start_addr_col, self.inject_tbl))
        retval = c.fetchone()[0]

        conn.commit()
        conn.close()
        return retval

    def get_end_addr(self):
        conn = connect(self.database)
        c = conn.cursor()

        c.execute("SELECT {} FROM {}".format(self.end_addr_col, self.inject_tbl))
        retval = c.fetchone()[0]

        conn.commit()
        conn.close()
        return retval

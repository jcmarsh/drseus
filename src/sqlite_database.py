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
        start_addr = int(lines[0].strip(), 16)
        end_addr = int(lines[1].strip(), 16)
        sqlite_database.log_tags(start_addr, end_addr)

def assembly_golden_run(sqlite_database, debugger):
    cprint("Running assembly golden run", 'yellow')
    cprint("Begin parsing, this may take a few minutes...", 'yellow')
    cprint("\tStoring load and store instructions...", 'yellow')
    with open("../etc/ldstr.txt") as ldstr:
        for line in ldstr:

            inst_addr = line.split()[0]
            inst_addr = inst_addr.strip(":")
            inst_addr = int(inst_addr, 16)

            # TODO: Double check. Cutting of binary bits in this way is clever.
            # TODO: Move to asm_golden_run? Should be of ls_addr right?
            bin_addr = bin(inst_addr)
            bin_addr = bin_addr[:-5]
            bin_addr = bin_addr[-11:]
            bin_addr = int(bin_addr, 2)
            cache = int(str(bin_addr), 10)

            ldstr_str = subprocess.check_output("echo " + "\"" + str(line) + "\"" + " | awk '{ print $3 }'", shell=True)
            ldstr_str = str(ldstr_str).lstrip("b\'")
            ldstr_str = str(ldstr_str).rstrip(":\\n\\n\'")

            sqlite_database.log_ldstr(inst_addr, ldstr_str)

    cprint("\tStoring branch instructions...", 'yellow')
    with open("../etc/branch.txt") as ldstr:
        for line in ldstr:

            inst_addr = subprocess.check_output("echo " + "\"" + str(line) + "\"" + " | awk '{ print $1 }'", shell=True)
            inst_addr = str(inst_addr).lstrip("b\'")
            inst_addr = int(str(inst_addr).rstrip(":\\n\\n\'"), 16)
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
    start_addr = hex(sqlite_database.get_start_addr())
    print("Start and end tag addresses", start_addr, hex(sqlite_database.get_end_addr()))
    debugger.break_dut(start_addr)

    # TODO: remove sleep?
    sleep(1)

    # Run on the database
    print("Running asm_golden_run.py")
    command = " 'cd ./jtag_eval/openOCD_cfg/mnt;python ./asm_golden_run.py |& tee asm_output.txt'"
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

        # Loop through once before printing to determine row spacing
        row_spacing = 5
        for col in info:
            if len(str(col[1])) > row_spacing:
                row_spacing = len(str(col[1]))
        row_spacing = row_spacing + 1
        print('Row spacing = ' + str(row_spacing))

        print('----__' + str(tn) + '__----')

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

        print('-----------------')

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
        # TODO: Not convinced that primary keys are needed
        self.branch_tbl      = "branch"
        self.address_col     = "address" # PRIMARY KEY
        self.address_type    = "INTEGER"
        self.inst_name_col   = "instruction"
        self.inst_name_type  = "TEXT"

        self.ldstr_tbl       = "loadstore"
        # self.address_col     = "address" # PRIMARY KEY
        # self.address_type    = "INTEGER"
        # self.inst_name_col   = "instruction"
        # self.inst_name_type  = "TEXT"

        # Fields for the load / store table
        #def add_ldstr_inst(cycles_total, cycles_diff, inst_addr, ldstr_addr):
        self.ldstr_inst_tbl    = "ls_inst"
        # self.id_col            = "id" <- not needed: sqlite automatically makes a rowid column
        # self.id_type           = "INTEGER PRIMARY KEY"
        self.cycles_total_col  = "cycles_total"
        self.cycles_total_type = "INTEGER"
        self.cycles_diff_col   = "cycles_diff"
        self.cycles_diff_type  = "INTEGER"
        # This table uses address column as well
        #self.address_col      = "address"
        #address_type          = "INTEGER"
        self.ldstr_col         = "load0_store1"
        self.ldstr_type        = "INTEGER"
        self.ldstr_addr_col    = "l_s_addr"
        self.ldstr_addr_type   = "INTEGER"
        #self.inst_name_col    = "instruction"
        #self.inst_name_type   = "TEXT"
        self.cache_set_col     = "L2_set"
        self.cache_set_type    = "INTEGER"

        # Execution information for injection (start and stop cycle counts)
        self.inject_tbl        = "injection_info"
        self.id_col            = "id"
        self.id_type           = "INTEGER"
        self.start_addr_col    = "start_tag_addr"
        self.start_addr_type   = "INTEGER"
        self.start_cycle_col   = "start_cycle"
        self.start_cycle_type  = "INTEGER"
        self.end_addr_col      = "end_tag_addr"
        self.end_addr_type     = "INTEGER"
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

        c.execute('CREATE TABLE {tn} ({c1} {t1} PRIMARY KEY, {c2} {t2})'\
            .format(tn=self.ldstr_tbl,\
                    c1=self.address_col, t1=self.address_type,\
                    c2=self.inst_name_col, t2=self.inst_name_type))

        c.execute('CREATE TABLE {tn} ({c1} {t1} PRIMARY KEY, {c2} {t2}, {c3} {t3}, {c4} {t4}, {c5} {t5})'\
            .format(tn=self.inject_tbl,\
                    c1=self.id_col, t1=self.id_type,\
                    c2=self.start_addr_col, t2=self.start_addr_type,\
                    c3=self.start_cycle_col, t3=self.start_cycle_type,\
                    c4=self.end_addr_col, t4=self.end_addr_type,\
                    c5=self.end_cycle_col, t5=self.end_cycle_type))

        c.execute('CREATE TABLE {tn} ({c1} {t1}, {c2} {t2}, {c3} {t3}, {c4} {t4}, {c5} {t5}, {c6} {t6}, {c7} {t7})'\
            .format(tn=self.ldstr_inst_tbl,\
                    c1=self.cycles_total_col, t1=self.cycles_total_type,\
                    c2=self.cycles_diff_col, t2=self.cycles_diff_type,\
                    c3=self.address_col, t3=self.address_type,\
                    c4=self.ldstr_col, t4=self.ldstr_type,\
                    c5=self.ldstr_addr_col, t5=self.ldstr_addr_type,\
                    c6=self.inst_name_col, t6=self.inst_name_type,\
                    c7=self.cache_set_col, t7=self.cache_set_type))

        conn.commit()
        conn.close()

    def __create_reslut(self):
        pass

    def log_branch(self, inst_addr, inst_name):
        conn = connect(self.database)
        c = conn.cursor()

        # Make sure that address is unique
        c.execute("SELECT * FROM {tn} WHERE {cn}=({val})"\
             .format(tn=self.branch_tbl, cn=self.address_col, val=inst_addr))
        if c.fetchone() != None:
            conn.close()
            cprint("Conflict in log_branch, primary key instruction address collision", 'red')
            cprint("Exiting")
            exit()

        c.execute("INSERT INTO {tn} ({c1}, {c2}) VALUES ({t1}, '{t2}')"
             .format(tn=self.branch_tbl,
             c1=self.address_col, c2=self.inst_name_col, \
             t1=inst_addr, t2=str(inst_name)))

        conn.commit()
        conn.close()

    def log_ldstr(self, inst_addr, inst_name):
        conn = connect(self.database)
        c = conn.cursor()

        # Make sure that cycles is unique
        c.execute("SELECT * FROM {tn} WHERE {cn}=({val})"\
             .format(tn=self.ldstr_tbl, cn=self.address_col, val=inst_addr))
        if c.fetchone() != None:
            conn.close()
            cprint("Conflict in log_ldstr, primary key instruction address collision", 'red')
            cprint("Exiting")
            exit()

        c.execute("INSERT INTO {tn} ({c1}, {c2}) VALUES ({t1}, '{t2}')"
             .format(tn=self.ldstr_tbl,
             c1=self.address_col, c2=self.inst_name_col,\
             t1=inst_addr, t2=str(inst_name)))

        conn.commit()
        conn.close()

    def log_tags(self, start_addr, end_addr):
        print("Adding start and end tag addresses.", start_addr, end_addr)
        conn = connect(self.database)
        c = conn.cursor()

        c.execute("INSERT INTO {} (\"{}\", \"{}\") VALUES ({}, {})".format(self.inject_tbl, self.start_addr_col, self.end_addr_col, start_addr, end_addr))

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

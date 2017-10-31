import subprocess
import re
from os import makedirs, remove
from os.path import isfile
from termcolor import colored, cprint
from sqlite3 import connect
# from .jtag.openocd import openocd
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
                # Special cases for injection_info
                if str(tn) == "injection_info":
                    if i == 1 or i == 3: # start_tag_addr, end_tag_addr
                        print(" " + hex(row[i]) + (row_spacing - len(hex(row[i])) - 1) * " ", end="")
                    else:
                        print(" " + str(row[i]) + (row_spacing - len(str(row[i])) - 1) * " ", end="")
                # Special cases for ldstr_inst_tbl
                elif str(tn) == "ls_inst":
                    if i == 2 or i == 4 or i == 6: # address, l_s_addr, or L2_set
                        print(" " + hex(row[i]) + (row_spacing - len(hex(row[i])) - 1) * " ", end="")
                    else:
                        print(" " + str(row[i]) + (row_spacing - len(str(row[i])) - 1) * " ", end="")
                # Everything else
                else:
                    print(" " + str(row[i]) + (row_spacing - len(str(row[i])) - 1) * " ", end="")
                i += 1
            print('|')

        print('----------------------------------------------------')

    print(colored("\n+++++++++++++++++++++++++++++++++++++++++++++++++++++++++\n", 'yellow'))
    conn.close()

class sqlite_database(object):
    def __init__(self, options, database_path=None):
        # Needed to search previous entries...
        self.stored_address = []
        self.stored_cycles = 0
        self.stored_cache_set = None

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

        # Fields for the load / store table
        self.ldstr_inst_tbl    = "ls_inst"
        self.cycles_total_col  = "cycles_total"
        self.cycles_total_type = "INTEGER"
        self.cycles_diff_col   = "cycles_diff"
        self.cycles_diff_type  = "INTEGER"
        self.address_col       = "address"
        self.address_type      = "INTEGER"
        self.ldstr_col         = "load0_store1"
        self.ldstr_type        = "INTEGER"
        self.ldstr_addr_col    = "l_s_addr"
        self.ldstr_addr_type   = "INTEGER"
        self.inst_name_col     = "instruction"
        self.inst_name_type    = "TEXT"
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
        self.table_list = [self.ldstr_inst_tbl, self.inject_tbl]

    def __initialize_database(self):
        print(colored("\tInitializing database...", 'yellow'))

        conn = connect(self.database)
        c = conn.cursor()

        # Add to database
        c.execute('CREATE TABLE {tn} ({c1} {t1}, {c2} {t2}, {c3} {t3}, {c4} {t4}, {c5} {t5}, {c6} {t6}, {c7} {t7})'\
            .format(tn=self.ldstr_inst_tbl,\
                    c1=self.cycles_total_col, t1=self.cycles_total_type,\
                    c2=self.cycles_diff_col, t2=self.cycles_diff_type,\
                    c3=self.address_col, t3=self.address_type,\
                    c4=self.ldstr_col, t4=self.ldstr_type,\
                    c5=self.ldstr_addr_col, t5=self.ldstr_addr_type,\
                    c6=self.inst_name_col, t6=self.inst_name_type,\
                    c7=self.cache_set_col, t7=self.cache_set_type))

        c.execute('CREATE TABLE {tn} ({c1} {t1} PRIMARY KEY, {c2} {t2}, {c3} {t3}, {c4} {t4}, {c5} {t5})'\
            .format(tn=self.inject_tbl,\
                    c1=self.id_col, t1=self.id_type,\
                    c2=self.start_addr_col, t2=self.start_addr_type,\
                    c3=self.start_cycle_col, t3=self.start_cycle_type,\
                    c4=self.end_addr_col, t4=self.end_addr_type,\
                    c5=self.end_cycle_col, t5=self.end_cycle_type))


        conn.commit()
        conn.close()

    # Given a cycle count, find the following load instructions.
    # addr, break_number = sql_db.get_next_load(injection.time)
    def get_next_load(self, cycle):
        print("Get next load...")
        conn = connect(self.database)
        c = conn.cursor()

        # SELECT * FROM ls_inst WHERE cycles_total > 18000 AND load0_store1 = 0 LIMIT 1;
        c.execute("SELECT address FROM {} WHERE {} > {} AND {} = 0 LIMIT 1;".format(self.ldstr_inst_tbl, self.cycles_total_col, cycle, self.ldstr_col))
        address = c.fetchone()[0]

        # TODO: Use the address to figure out the number of times you need to break first.
        return (address, 1)

    # Given a cycle count and cache set find the addresses that loaded / stored in that set
    # return the address or null if none
    def PreviousLdrStr(self, cycle, cache_set):
        print("Get the stores / loads to %d prior to cycle %d" % (cache_set, cycle))

        # Return saved address from a multi-access command
        if (self.stored_cache_set == cache_set):
            retval = self.stored_address.pop()
            if len(self.stored_address) == 0:
                self.stored_cache_set = None
            print("Multi, counting down: ", len(self.stored_address))
            return self.stored_cycles, retval

        # address, cycle
        conn = connect(self.database)
        c = conn.cursor()

        # Should just find the prvious load or store. Calling function worries about uniqueness.
        # Just want to know what is resident in the cache.

        # Multi loads / stores complicate things... need to get all of the accesses from the same command and then pass them back one at a time
        # Cache lines are 8 Words... addresses need to lose last three bits (offset)
        # SELECT l_s_addr FROM ls_inst WHERE cycles_total < 30500 AND L2_set = 1531 ORDER BY cycles_total DESC LIMIT 1;

        # Get the cycles of the line that matches the criteria
        # SELECT cycles_total FROM ls_inst WHERE cycles_total < 30500 AND L2_set = 1531 ORDER BY cycles_total DESC LIMIT 1;
        c.execute("SELECT cycles_total FROM ls_inst WHERE cycles_total < {} AND L2_set = {} ORDER BY cycles_total DESC LIMIT 1".format(cycle, cache_set))
        retval = c.fetchone()
        if retval == None:
            return None, None
        found_cycles = retval[0]

        # Get all lines that match that cycles_total (accounts for multi loads / stores)
        c.execute("SELECT l_s_addr FROM ls_inst WHERE cycles_total = {} AND L2_set = {}".format(found_cycles, cache_set))
        retval = c.fetchall()
        if len(retval) > 1:
            # A single command is accessing multiple lines, save others for future calls... what if multple injections in a run?
            self.stored_address = []
            self.stored_cycles = found_cycles
            self.stored_cache_set = cache_set
            for i in range(0, len(retval)): # TODO: Make go in reverse?
                self.stored_address.append(retval[i][0])
            print("Multi- FIRST")
            asdf = self.stored_address.pop()
            print("Addresses: ", self.stored_address)
            print("Returning: ", self.stored_cycles, " ", asdf)
            return self.stored_cycles, asdf

        # send back one
        print("Word")
        print(retval)

        # Cache set... Needs to be filled in in the database. Sigh.

        return found_cycles, retval[0]


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

    def get_start_cycle(self):
        conn = connect(self.database)
        c = conn.cursor()

        # SELECT MIN(cycles_total) FROM ls_inst
        c.execute("SELECT MIN({}) FROM {}".format(self.cycles_total_col, self.ldstr_inst_tbl))
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

    def get_end_cycle(self):
        conn = connect(self.database)
        c = conn.cursor()

        # SELECT MAX(cycles_total) FROM ls_inst
        c.execute("SELECT MAX({}) FROM {}".format(self.cycles_total_col, self.ldstr_inst_tbl))
        retval = c.fetchone()[0]

        conn.commit()
        conn.close()
        return retval

from termcolor import cprint
from .sqlite_database import sqlite_database, print_sqlite_database, delete_sqlite_database
from sqlite3 import connect

# Testing file for the sqlite_database class

def test_log_asm(sqlite_database):
    #TODO
    pass

def test_log_ldstr(sqlite_database):
    cache_section = 4
    cycles = 53244587
    ldstr = 1
    ldstr_addr = 0xBEEFCAFE

    cprint("Calling log_ldstr", 'cyan')
    sqlite_database.log_ldstr(cache_section, cycles, ldstr, ldstr_addr)
    print_sqlite_database(sqlite_database)
    cprint("Calling log_ldstr again with the same values, expect exit", 'cyan')
    sqlite_database.log_ldstr(cache_section, cycles, ldstr, ldstr_addr)

def run_sqlite_tests(options):

    cprint("Running tests on sqlite_database", 'cyan')
    db = sqlite_database(options)
    print_sqlite_database(db)
    test_log_asm(db)
    test_log_ldstr(db)
    delete_sqlite_database(db)

from os import makedirs, remove
from os.path import isfile
from termcolor import colored
import sqlite3

from .database import get_campaign

def delete_sqlite_databse(sqlite_database):
    #TODO 2nd
    pass

def assembly_golden_run(sqlite_database):
    #TODO
    pass

class sqlite_database(object):
    def __init__(self, options):
        self.options = options
        self.campaign = get_campaign(options)
        self.database = self.__create_database()

    def __create_database(self):
        print(colored("Creating sqlite database", 'yellow'))
        sqlite_folder = 'campaign-data/{}/sqlite'.format(self.campaign.id)
        if isfile(sqlite_folder):
             print(colored("Sqlite database already exists for this campaign", 'red'))
             return
        makedirs(sqlite_folder)
        database = sqlite_folder + '/' + 'database.sqlite'
        conn = sqlite3.connect(database)
        conn.close()
        print(colored("database: " + database, 'yellow'))
        return database

    def __create_reslut(self):
        #TODO
        pass

    def log_reslut(self):
        #TODO
        pass

    def log_event(self):
        #TODO
        pass

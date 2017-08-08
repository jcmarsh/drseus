from .sqlite_database import sqlite_database

# Can't import fault_injector circular dependancy as fault_injector depends on us
def perform_cache_injections(sqlite_database):
    pass

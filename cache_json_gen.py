import json

# Intended to generate a json file describing the cache configuration of a zynq

# Roughly, the A9 cores on the Zynq have the following caches:
#   All caches: 4 byte word size, cache line is 8 words, byte addressable
#   L1D (per core): 32KB, 4-way set associative, 256 sets with 4 lines each: 19 bit tag, 256 bit data, 2 bit flag
#   L1I (per core): 32KB, 4-way set associative, 256 sets with 4 lines each: 19 bit tag, 256 bit data, 1 bit flag
#       only modified by an instruction fetch (no write back / write through: doesn't make sense in this context)
#   L2 (per core): 512KB, 8-way set associative, 2048 sets with 8 lines each: 16 bit tag, 256 bit data, 2 bit flag

# Open file to write to

# Cache L1D
tag = [277, 258]
data = [257, 2]
flag = [1, 0]
cacheline = {"fields": [["tag", tag], ["data", data], ["flag", flag]]}
registers = {"cacheline_000" : cacheline, "cacheline_001": cacheline, "cacheline_002": cacheline, "cacheline_003": cacheline}
cache_l1d = {"core": False, "count": 2, "registers": registers}

print(json.dumps(cache_l1d, sort_keys=True, indent=2))

# Cache L1I

# Cache L2
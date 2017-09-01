import json
from math import log

# Intended to generate a json file describing the cache configuration of a zynq

# Roughly, the A9 cores on the Zynq have the following caches:
#   All caches: 4 byte word size, cache line is 8 words, byte addressable
#   L1D (per core): 32KB, 4-way set associative, 256 sets with 4 lines each: 19 bit tag, 256 bit data, 2 bit flag
#   L1I (per core): 32KB, 4-way set associative, 256 sets with 4 lines each: 19 bit tag, 256 bit data, 1 bit flag
#       only modified by an instruction fetch (no write back / write through: doesn't make sense in this context)
#   L2 (per core): 512KB, 8-way set associative, 2048 sets with 8 lines each: 16 bit tag, 256 bit data, 2 bit flag

# Cache settings
# L1D, in bits
L1D_TAG_SIZE = 19
L1D_DATA_SIZE = 256
L1D_FLAG_SIZE = 2

L1D_SIZE = 32768
L1D_ASSOC = 4

def create_cache(size, assoc, data_size, flag_bits):
	flag = [flag_bits - 1, 0]
	data = [(data_size - 1) + flag_bits, flag_bits]
	index_bits = log((size * 8) / (assoc * data_size), 2)
	block_offset_bits = log(data_size / 8, 2)
	tag_bits = 32 - (index_bits + block_offset_bits)
	print("Tag_bits:", tag_bits, "block bits:", block_offset_bits, "index bits:", index_bits)
	tag = [int((tag_bits - 1) + data_size + flag_bits), data_size + flag_bits]

	cacheline = {"fields": [["tag", tag], ["data", data], ["flag", flag]]}
	# Need to add the ways for fields (tag_0-3, data 0_3, etc)
	registers = {}
	cache = {"core": False, "count": 2, "registers": registers}

	for index in range(0, int(pow(2, index_bits))):
		registers["cachline_%03d" % index] = dict(cacheline.items())
		registers["cachline_%03d" % index].update({"index": index})

	return cache


# Cache L1D
# tag = [277, 258]
# data = [257, 2]
# flag = [1, 0]
# cacheline = {"fields": [["tag", tag], ["data", data], ["flag", flag]]}
# registers = {"cacheline_000" : cacheline, "cacheline_001": cacheline, "cacheline_002": cacheline, "cacheline_003": cacheline}
# cache_l1d = {"core": False, "count": 2, "registers": registers}

print(json.dumps(create_cache(L1D_SIZE, L1D_ASSOC, L1D_DATA_SIZE, L1D_FLAG_SIZE), sort_keys=True, indent=2))

# Cache L1I

# Cache L2
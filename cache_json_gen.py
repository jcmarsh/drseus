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
# L1D_TAG_SIZE = 19 <- derived
L1D_DATA_SIZE = 256
L1D_FLAG_SIZE = 2
L1D_SIZE = 32768 # 32KiB, in bytes
L1D_ASSOC = 4
L1D_COUNT = 2 # One per core

# L1I
# L1I_TAG_SIZE = 19 <- derived
L1I_DATA_SIZE = 256
L1I_FLAG_SIZE = 1
L1I_SIZE = 32768 # 32KiB, in bytes
L1I_ASSOC = 4
L1I_COUNT = 2 # One per core

# L2
# L2_TAG_SIZE = 16 <- derived
L2_DATA_SIZE = 256
L2_FLAG_SIZE = 2
L2_SIZE = 524288 # 512KiB, in bytes
L2_ASSOC = 8
L2_COUNT = 1 # One shared L2 cache


def create_cache(size, assoc, data_size, flag_bits, count):
	flag = [flag_bits - 1, 0]
	data = [(data_size - 1) + flag_bits, flag_bits]
	index_bits = int(log((size * 8) / (assoc * data_size), 2))
	block_offset_bits = int(log(data_size / 8, 2))
	tag_bits = 32 - (index_bits + block_offset_bits)
	# print("Tag_bits:", tag_bits, "block bits:", block_offset_bits, "index bits:", index_bits)
	tag = [(tag_bits - 1) + data_size + flag_bits, data_size + flag_bits]


        fields = []
        for index in range(0, assoc):
                fields.append(["tag_%d" % index, tag])
                fields.append(["data_%d" % index, data])
                fields.append(["flag_%d" % index, flag])
        # cacheline = {"fields": [["tag", tag], ["data", data], ["flag", flag]]}
	cacheline = {"bits": int(assoc * (tag_bits + data_size + flag_bits)), "fields": fields}

	# Need to add the ways for fields (tag_0-3, data 0_3, etc)
	registers = {}
	cache = {"core": False, "count": count, "registers": registers}

	for index in range(0, int(pow(2, index_bits))):
		registers["cacheline_%04d" % index] = dict(cacheline.items())
		registers["cacheline_%04d" % index].update({"index": index})

	return cache



# Formatting for including in the drseus json file
print("\"CACHE_L2\": ")

# Cache L1D
#print(json.dumps(create_cache(L1D_SIZE, L1D_ASSOC, L1D_DATA_SIZE, L1D_FLAG_SIZE, L1D_COUNT), sort_keys=True, indent=2))

# Cache L1I
#print(json.dumps(create_cache(L1I_SIZE, L1I_ASSOC, L1I_DATA_SIZE, L1I_FLAG_SIZE, L1I_COUNT), sort_keys=True, indent=2))

# Cache L2
print(json.dumps(create_cache(L2_SIZE, L2_ASSOC, L2_DATA_SIZE, L2_FLAG_SIZE, L2_COUNT), sort_keys=True, indent=2))

print("}")

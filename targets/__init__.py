# if count is not present it is assumed to be 1
# if bits is not present it is assumbed to be 32

from random import randrange


def calculate_target_bits(targets):
    for target in targets:
        # count bits for each target
        total_bits = 0
        for register in targets[target]['registers']:
            if 'bits' in targets[target]['registers'][register]:
                bits = (targets[target]['registers'][register]
                               ['bits'])
            else:
                bits = 32
            if 'count' in targets[target]['registers'][register]:
                count = 1
                if 'is_tlb' in \
                    targets[target]['registers'][register] \
                    and (targets[target]['registers'][register]
                                ['is_tlb']):
                    dimensions = (targets[target]['registers']
                                         [register]['count'][:-1])
                else:
                    dimensions = (targets[target]['registers']
                                         [register]['count'])
                for dimension in dimensions:
                    count *= dimension
            else:
                count = 1
            (targets[target]['registers']
                    [register]['total_bits']) = count * bits
            total_bits += count * bits
            # if a register is partially implemented generate an adjust_bit
            # mapping list to ensure an unimplemented field is not injected
            if 'partial' in targets[target]['registers'][register] \
                and (targets[target]['registers'][register]
                            ['partial']):
                adjust_bit = []
                if 'is_tlb' in \
                    targets[target]['registers'][register] \
                    and (targets[target]['registers'][register]
                                ['is_tlb']):
                    for field_range in (targets[target]['registers'][register]
                                               ['fields'].values()):
                        adjust_bit.extend(range(field_range[0],
                                                field_range[1]+1))
                else:
                    for field in (targets[target]['registers'][register]
                                         ['fields']):
                        try:
                            adjust_bit.extend(range(field[1][0], field[1][1]+1))
                        except:
                            print(field)
                if len(adjust_bit) != bits:
                    raise Exception('Bits mismatch for register: ' +
                                    register+' in target: '+target)
                else:
                    (targets[target]['registers'][register]
                            ['adjust_bit']) = sorted(adjust_bit)
        targets[target]['total_bits'] = total_bits


def choose_target(selected_targets, targets):
    """
    Given a list of targets, randomly choose one and return it.
    If no list of targets is given, choose from all available targets.
    Random selection takes into account the number of bits each target contains.
    """
    target_to_inject = None
    target_list = []
    total_bits = 0
    for target in targets:
        if selected_targets is None or target in selected_targets:
            bits = targets[target]['total_bits']
            target_list.append((target, bits))
            total_bits += bits
    random_bit = randrange(total_bits)
    bit_sum = 0
    for target in target_list:
        bit_sum += target[1]
        if random_bit < bit_sum:
            target_to_inject = target[0]
            break
    else:
        raise Exception('Error choosing injection target')
    if 'count' in targets[target_to_inject]:
        target_index = randrange(targets[target_to_inject]['count'])
    else:
        target_index = None
    return target_to_inject, target_index


def choose_register(target, targets):
    """
    Randomly choose a register from the target and return it.
    Random selection takes into account the number of bits each register
    contains.
    """
    registers = targets[target]['registers']
    register_list = []
    total_bits = 0
    for register in registers:
        bits = registers[register]['total_bits']
        register_list.append((register, bits))
        total_bits += bits
    random_bit = randrange(total_bits)
    bit_sum = 0
    for register in register_list:
        bit_sum += register[1]
        if random_bit < bit_sum:
            register_to_inject = register[0]
            break
    else:
        raise Exception('Error choosing register for target: '+target)
    if 'count' in registers[register_to_inject]:
        register_index = []
        for dimension in registers[register_to_inject]['count']:
            index = randrange(dimension)
            register_index.append(index)
    else:
        register_index = None
    if 'alias' in registers[register_to_inject]:
        register_alias = register_to_inject
        register_index = \
            registers[register_to_inject]['alias']['register_index']
        register_to_inject = registers[register_to_inject]['alias']['register']
    else:
        register_alias = None
    return register_to_inject, register_index, register_alias


def choose_bit(register_name, register_index, target, targets):
    register = targets[target]['registers'][register_name]
    if 'is_tlb' in register and register['is_tlb']:
        fields = register['fields']
        field_to_inject = None
        fields_list = []
        total_bits = 0
        for field in fields:
            bits = fields[field]['bits']
            fields_list.append((field, bits))
            total_bits += bits
        random_bit = randrange(total_bits)
        bit_sum = 0
        for field in fields_list:
            bit_sum += field[1]
            if random_bit < bit_sum:
                field_to_inject = field[0]
                break
        else:
            raise Exception('Error choosing TLB field to inject')
        if 'split' in fields[field_to_inject] and \
                fields[field_to_inject]['split']:
            total_bits = (fields[field_to_inject]['bits_h'] +
                          fields[field_to_inject]['bits_l'])
            random_bit = randrange(total_bits)
            if random_bit < fields[field_to_inject]['bits_l']:
                register_index[-1] = \
                    fields[field_to_inject]['index_l']
                start_bit_index = \
                    fields[field_to_inject]['bit_indicies_l'][0]
                end_bit_index = \
                    fields[field_to_inject]['bit_indicies_l'][1]
            else:
                register_index[-1] = \
                    fields[field_to_inject]['index_h']
                start_bit_index = \
                    fields[field_to_inject]['bit_indicies_h'][0]
                end_bit_index = \
                    fields[field_to_inject]['bit_indicies_h'][1]
        else:
            register_index[-1] = fields[field_to_inject]['index']
            start_bit_index = \
                fields[field_to_inject]['bit_indicies'][0]
            end_bit_index = \
                fields[field_to_inject]['bit_indicies'][1]
        bit_to_inject = randrange(start_bit_index, end_bit_index+1)
    else:
        if 'bits' in register:
            bit_to_inject = randrange(register['bits'])
        else:
            bit_to_inject = randrange(32)
        if 'adjust_bit' in register:
            bit_to_inject = register['adjust_bit'][bit_to_inject]
        if 'fields' in register:
            for field in register['fields']:
                if bit_to_inject in range(field[1][0], field[1][1]+1):
                    field_to_inject = field[0]
                    break
            else:
                raise Exception('Error finding register field name for '
                                'target: '+target+', register: '+register_name +
                                ', bit: '+str(bit_to_inject))
        else:
            field_to_inject = None
    return bit_to_inject, field_to_inject


def get_num_bits(register, target, targets):
    register = targets[target]['registers'][register]
    if 'actual_bits' in register:
        num_bits = register['actual_bits']
    elif 'bits' in register:
        num_bits = register['bits']
    else:
        num_bits = 32
    return num_bits

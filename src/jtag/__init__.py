from pyudev import Context
from random import uniform
from socket import AF_INET, SOCK_STREAM, socket
from telnetlib import Telnet
from termcolor import colored
from time import sleep

from ..dut import dut
from ..error import DrSEUsError
from ..targets import choose_injection, get_targets


def find_all_uarts():
    return sorted(
        dev['DEVNAME'] for dev in Context().list_devices(subsystem='tty')
        if 'DEVLINKS' in dev and not (dev['ID_VENDOR_ID'] == '0403' and
                                      dev['ID_MODEL_ID'] == '6014'))


def find_p2020_uarts():
    return sorted(
        dev['DEVNAME'] for dev in
        Context().list_devices(ID_VENDOR_ID='067b', ID_MODEL_ID='2303')
        if 'DEVLINKS' in dev)


def find_zedboard_jtag_serials():
    return sorted(
        {dev['ID_SERIAL_SHORT']
         for dev in Context().list_devices(ID_VENDOR_ID='0403')
         if 'DEVLINKS' not in dev} &
        {dev['ID_SERIAL_SHORT']
         for dev in Context().list_devices(ID_MODEL_ID='6014')
         if 'DEVLINKS' not in dev})


def find_zedboard_uart_serials():
    return {dev['DEVNAME']: dev['ID_SERIAL_SHORT'] for dev in
            Context().list_devices(ID_VENDOR_ID='04b4', ID_MODEL_ID='0008')
            if 'DEVLINKS' in dev}


def find_open_port():
            sock = socket(AF_INET, SOCK_STREAM)
            sock.bind(('', 0))
            port = sock.getsockname()[1]
            sock.close()
            return port


class jtag(object):
    def __init__(self, database, options):
        self.db = database
        self.bbzybo = 1
        self.options = options
        self.timeout = 30
        self.prompts = [bytes(prompt, encoding='utf-8')
                        for prompt in self.prompts]

    def __str__(self):
        string = 'JTAG Debugger at {}'.format(self.options.debugger_ip_address)
        try:
            string += ' port {}'.format(self.port)
        except AttributeError:
            pass
        return string

    def connect_telnet(self):
        try:
            print("ip addr for telnet: " + str(self.options.debugger_ip_address) + ", port: "  + str(self.port))
            self.telnet = Telnet(self.options.debugger_ip_address, self.port,
                                 timeout=self.timeout)
        except ConnectionRefusedError:
            attempt = 0
            while attempt < 3:
                attempt += 1;
                print("Connection to Telnet refused, retrying...")
                sleep(1)
                self.telnet = Telnet(self.options.debugger_ip_address, self.port,
                                     timeout=self.timeout)
                if self.telnet:
                    break;
        self.db.log_event(
            'Information', 'Debugger', 'Connected to telnet',
            '{}:{}'.format(self.options.debugger_ip_address, self.port))

    def open(self):
        self.dut = dut(self.db, self.options)
        if self.db.campaign.aux:
            self.aux = dut(self.db, self.options, aux=True)
        self.connect_telnet()

    def close(self):
        self.telnet.close()
        self.db.log_event(
            'Information', 'Debugger', 'Closed telnet')
        self.dut.close()
        if self.db.campaign.aux:
            self.aux.close()

    def set_targets(self, architecture):
        if hasattr(self.options, 'selected_targets'):
            selected_targets = self.options.selected_targets
        else:
            selected_targets = None
        if hasattr(self.options, 'selected_registers'):
            selected_registers = self.options.selected_registers
        else:
            selected_registers = None
        self.targets = get_targets(architecture, 'jtag', selected_targets,
                                   selected_registers)

    def reset_dut(self, expected_output, attempts):

        def attempt_exception(attempt, attempts, error, event_type):
            self.db.log_event(
                'Warning' if attempt < attempts-1 else 'Error', 'Debugger',
                event_type, self.db.log_exception)
            print(colored('{}: Error resetting DUT (attempt {}/{}): {}'.format(
                self.dut.serial.port, attempt+1, attempts, error), 'red'))
            if attempt < attempts-1:
                sleep(30)
            else:
                raise DrSEUsError(error.type)

    # def reset_dut(self, expected_output, attempts):
        self.dut.flush()
        self.dut.reset_ip()
        for attempt in range(attempts):
            try:
                self.command('reset', expected_output,
                             'Error resetting DUT', True)
            except DrSEUsError as error:
                attempt_exception(attempt, attempts, error,
                                  'Error resetting DUT')
            else:
                try:
                    self.dut.do_login()
                except DrSEUsError as error:
                    attempt_exception(attempt, attempts, error,
                                      'Error booting DUT')
                else:
                    break

    def halt_dut(self, halt_command, expected_output):
        event = self.db.log_event(
            'Information', 'Debugger', 'Halt DUT', success=False)
        self.command(halt_command, expected_output, 'Error halting DUT', False)
        self.dut.stop_timer()
        event.success = True
        event.save()

    def continue_dut(self, continue_command):
        event = self.db.log_event(
            'Information', 'Debugger', 'Continue DUT', success=False)
        self.command(continue_command, error_message='Error continuing DUT',
                     log_event=False)
        self.dut.start_timer()
        event.success = True
        event.save()

    # TODO: Doesn't need to be a class function
    def PrevAccess(self, sql_db, cycle, cache_set, assoc):
        candidates = []
        current_cycle = cycle;
        while len(candidates) < assoc:
            current_cycle, address = sql_db.PreviousLdrStr(current_cycle, cache_set)
            if address == None:
                return candidates
            if not (address in candidates):
                candidates.append(address)
        return candidates

    def inject_faults(self, sql_db):
        # Select injection times
        injection_times = []
        for i in range(self.options.injections):
            injection_times.append(int(uniform(sql_db.get_start_cycle(), sql_db.get_end_cycle())))

        # Select targets and injection object
        injections = []
        if hasattr(self, 'targets') and self.targets:
            for injection_time in sorted(injection_times):
                injection = choose_injection(self.targets, self.options.selected_target_indices)
                print(injection)
                injection = self.db.result.injection_set.create(success=False, time=injection_time, **injection)
                injections.append(injection)

        print("********************************************************************************")
        print("Injection times:")
        print("\t", injection_times)
        print("Injections:")
        for injection in injections:
            print("\tInjection:", injection.target)
            print("\t", injection)
            print("\t", injection.bit, " ", injection.field, " ", injection.register)
        print("Possible targets:")
        for target in self.targets:
            print("\tTarget:", target)
        print("Target Indices?:", self.options.selected_target_indices)
        print("********************************************************************************")

        if self.db.campaign.command:
            # TODO: Need to call self.dut.break_dut so skip first bits?
            # TODO: Needs to deal with timing better, at least for cache.
            print("**** It's an injection start ****")
            self.start_dut()
        previous_injection_time = 0

        # Perform the injections
        for injection in injections:
            if injection.target in ('CPU', 'GPR', 'TLB') or ('CP' in self.targets[injection.target] and self.targets[injection.target]['CP']):
                self.select_core(injection.target_index)

            if (injection.target == 'CACHE_L2'):
                # For cache injection:
                # Select the desired cache line (injection.bit / injection.field)
                # From the stopping time, find all future reads and writes
                cache_set = int(injection.register[-4:])
                print("Is cache_set being set for the cache? ", cache_set)
                ways = 8 # TODO: Hardcoding for L2 cache

                # While still finding them, do this...
                # Test code for now...
                candidates = self.PrevAccess(sql_db, 30500, 1531, 8)
                # candidates = self.PrevAccess(sql_db, injection.time, cache_set, ways)
                # Candidates are the addresses of the data in the cache shifted to remove the byte offset
                #   Since there are 32 bytes in each cache line, that means >> 5
                #   TODO: Make sure byte addressable and not word addressable.

                print("Candidate addresses for the injection!: ", candidates)

                # Parse from injection.field: 84   data_2   cacheline_1455
                # TODO: limits to a 1 digit number of ways
                #way_impacted = int(injection.field[-1:])
                way_impacted = 0

                if way_impacted >= len(candidates):
                    print("No fault injected: cache line was not valid.")
                    # TODO: How to return from this?
                    return None, None, False

                # target picked, so now need all following accesses (until a store or slow load)
                # For out example (way 0 of cache line 1531 at cycle 30500, address 1097584 for fib_short):
                #   SELECT * FROM ls_inst WHERE L2_set = 1531 AND l_s_addr = 1097584 AND cycles_total > 30500;
                #   30586|14|1055908|0|1097584|LDM|1531
                #   31133|13|1055900|1|1097584|STM|1531 <- don't return... signals end.
                #injection_targets = sql_db.NextLdrStr(cycle, cache_set, (candidates[way_impacted] << 5) + injection.bit)
                injection_targets = sql_db.NextLdrStr(30500, 1531, (candidates[way_impacted] << 5) + 16)
                print("Injection targets: ", injection_targets)

                if (len(injection_targets) == 0):
                    print("No Fault injected: value in cache never read.")
                    # TODO: How to return from this?
                    return None, None, False

                # Need advance the DUT to the first injection
                # On first injection, figure out the corrupted bit
                # On all injections, figure out the target and load the wrong value and continue.
                #skip_count = sql_db.SkipCount(injection_cycle...?, address)
                prev_cycle = injection_targets[0][0]
                skip_count = sql_db.SkipCount(0, prev_cycle, injection_targets[0][1]) #, (candidates[way_impacted] << 5) + 16)
                print("Skip Count! ", skip_count)

                # Skip the first
                # TODO: This first needs to run until the start tag (but this function restarts)
                self.break_dut_after(str(injection_targets[0][1]), skip_count) # runs from the beginning, Removes breakpoint.

                inject_value = None
                for target in injection_targets:
                    # Set breakpoint
                    print("Target: ", target)
                    skip_count = sql_db.SkipCount(prev_cycle, target[0], target[1])
                    if (skip_count >= 1):
                        print("********************************")
                        print("* Need to implement this case! *")
                        print("********************************")
                    self.single_dut_break(str(target[1]))

                    # find target
                    # inject fault
                    # set next breakpoint
                    # continue


                print("Going to inject on this guy %s on the %dth time." % (candidates[way_impacted]))

                # Check if any injections need to be performed
                # Summary: Pick the impacted cache set, find the address corresponding to resident values, pick one address to use injections.
                # For Round Robin policy:
                #   * W is the number of ways (4-way, 8-way)
                #   * Find the previous W unique stores / loads from that set
                #     This tells you what was in the cache. Unique as in target address (avoids bias with a single popular address)
                #   * Pick one of them at random to be the impacted way (if less than W, each valid way still has only an 1/W chance of being hit)
                #   * Find all following cached loads from that address up until the next store to that address or uncached load from that address
                #     * Those (if any) are the ones injected on.
                #   * Assume that all ways are unlocked and valid


            # Needs to have processor halted at correct point here.
            previous_injection_time = injection.time
            injection.processor_mode = self.get_mode()
            if 'access' in (self.targets[injection.target]
                                        ['registers'][injection.register]):
                injection.register_access = \
                    (self.targets[injection.target]
                                 ['registers'][injection.register]['access'])
            injection.gold_value = \
                self.get_register_value(injection)
            injection.injected_value = hex(
                int(injection.gold_value, base=16) ^ (1 << injection.bit))
            injection.save()
            if self.options.debug:
                print(colored(
                    'result id: {}\ninjection time: {}\ntarget: {}\n'
                    'register: {}\nbit: {}\ngold value: {}\ninjected value: {}'
                    ''.format(
                        self.db.result.id, injection.time,
                        injection.target_name, injection.register,
                        injection.bit, injection.gold_value,
                        injection.injected_value), 'magenta'))
            self.set_register_value(injection)
            if int(injection.injected_value, base=16) == \
                    int(self.get_register_value(injection), base=16):
                injection.success = True
                injection.save()
                self.db.log_event(
                    'Information', 'Debugger', 'Fault injected')
            else:
                self.set_mode()
                self.set_register_value(injection)
                if int(injection.injected_value, base=16) == \
                        int(self.get_register_value(injection), base=16):
                    injection.success = True
                    injection.save()
                    self.db.log_event(
                        'Information', 'Debugger',
                        'Fault injected as supervisor')
                else:
                    self.db.log_event(
                        'Error', 'Debugger', 'Injection failed')
                self.set_mode(injection.processor_mode)
            self.continue_dut()
        return None, None, False

    def command(self, command, expected_output, error_message,
                log_event, line_ending, echo):
        if log_event:
            event = self.db.log_event(
                'Information', 'Debugger', 'Command', command, success=False)
        expected_output = [bytes(output, encoding='utf-8')
                           for output in expected_output]
        return_buffer = ''
        if error_message is None:
            error_message = command
        buff = self.telnet.read_very_eager().decode('utf-8', 'replace')
        if self.db.result is None:
            self.db.campaign.debugger_output += buff
        else:
            self.db.result.debugger_output += buff
        if self.options.debug:
            print(colored(buff, 'yellow'))
        if command:
            self.telnet.write(bytes('{}{}'.format(command, line_ending),
                                    encoding='utf-8'))
            if echo:
                index, match, buff = self.telnet.expect(
                    [bytes(command, encoding='utf-8')], timeout=self.timeout)
                buff = buff.decode('utf-8', 'replace')
            else:
                buff = '{}\n'.format(command)
            if self.db.result is None:
                self.db.campaign.debugger_output += buff
            else:
                self.db.result.debugger_output += buff
            if self.options.debug:
                print(colored(buff, 'yellow'))
            if echo and index < 0:
                raise DrSEUsError(error_message)
        for i in range(len(expected_output)):
            index, match, buff = self.telnet.expect(expected_output,
                                                    timeout=self.timeout)
            buff = buff.decode('utf-8', 'replace')
            if self.db.result is None:
                self.db.campaign.debugger_output += buff
            else:
                self.db.result.debugger_output += buff
            return_buffer += buff
            if self.options.debug:
                print(colored(buff, 'yellow'), end='')
            if index < 0:
                raise DrSEUsError(error_message)
        else:
            if self.options.debug:
                print()
        index, match, buff = self.telnet.expect(self.prompts,
                                                timeout=self.timeout)
        buff = buff.decode('utf-8', 'replace')
        if self.db.result is None:
            self.db.campaign.debugger_output += buff
        else:
            self.db.result.debugger_output += buff
        return_buffer += buff
        if self.options.debug:
            print(colored(buff, 'yellow'))
        if self.db.result is None:
            self.db.campaign.save()
        else:
            self.db.result.save()
        if index < 0:
            raise DrSEUsError(error_message)
        for message in self.error_messages:
            if message in return_buffer:
                raise DrSEUsError(error_message)
        if log_event:
            event.success = True
            event.save()
        return return_buffer

    def select_core(self, core):
        pass

    def get_mode(self):
        pass

    def set_mode(self, mode):
        pass

    def get_register_value(self, register_info):
        pass

    def set_register_value(self, register_info, value):
        pass

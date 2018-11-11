# Makes a campaign
#./drseus.py --serial /dev/ttyUSBzybo --prompt safeword --jtag_ip rpi3open.local --timeout 40000 new --arch a9 -c unused -t 1 -o output.txt

./drseus.py --serial /dev/ttyUSBzybo --baud 460800 --prompt safeword --jtag_ip localhost --timeout 80000 new --arch a9 -c unused -t 1 -o output.txt

# Runs a campaign with n injection iteration using p processes
#./drseus.py --timeout 5 --serial /dev/ttyUSBzybo --prompt safeword inject -n 25 -i 1 -p 1 -T 0 -l 0

# Runs a campaign with n injection iteration using p processes with debug turned on
#./drseus.py --timeout 10 --serial /dev/ttyUSBzybo --prompt safeword inject -n 250 -i 1 -p 1 -T 0 -l 0 --debug

# Latest test on Fib_rec:
# ./python/bin/python3 drseus.py --serial /dev/ttyUSBzybo --prompt safeword --jtag_ip localhost --timeout 300 -c 665 inject -n 5

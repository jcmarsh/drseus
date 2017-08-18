# Makes a campaign
./drseus.py --serial /dev/ttyUSB1 --prompt safeword --jtag_ip raspberrypi.local --timeout 40000 new --arch a9 -c unused -t 1 -o output.txt


# Runs a campaign with n injection iteration using p processes
#./drseus.py --timeout 5 --serial /dev/ttyUSB1 --prompt safeword inject -n 25 -i 1 -p 1 -T 0 -l 0

# Runs a campaign with n injection iteration using p processes with debug turned on
#./drseus.py --timeout 10 --serial /dev/ttyUSB1 --prompt safeword inject -n 250 -i 1 -p 1 -T 0 -l 0 --debug

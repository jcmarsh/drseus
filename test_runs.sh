# Makes a campaign, does nothing else
# Needed a few tweaks:
#	In __init__.py (I think, search for #RG to confirm) set ip and port for open ocd to be the BB
# TODO set timing itterations to 5 and make the application be relaunched in DrSeus using the correct command
#./drseus.py --serial /dev/ttyUSB1 --prompt safeword --jtag_ip 192.168.7.2 new --arch a9 -c unused -t 1

# Runs a campaign with n injection iteration using p processes
./drseus.py --error_msg MISMATCH --serial /dev/ttyUSB1 --prompt safeword inject -n 20 -i 5 -p 1 -T 0 -l 0 --debug

# Runs a campaign under supervision
#./drseus.py --serial /dev/ttyUSB1 --prompt safeword s

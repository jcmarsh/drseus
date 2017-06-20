# Makes a campaign, does nothing else
# Needed a few tweaks:
#	In __init__.py (I think, search for #RG to confirm) set ip and port for open ocd to be the BB
#./drseus.py --serial /dev/ttyUSB1 --prompt safeword --jtag_ip 192.168.7.2 new --arch a9 --delay 5

# Runs a campaign with n injection iteration using p processes
./drseus.py --serial /dev/ttyUSB1 --prompt safeword inject -n 25 -p 1 --debug

# Runs a campaign under supervision
#./drseus.py --serial /dev/ttyUSB1 --prompt safeword s

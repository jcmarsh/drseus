#!/bin/sh

sudo pg_dropcluster --stop 9.6 main
sudo pg_createcluster 9.6 main
sudo service postgresql restart

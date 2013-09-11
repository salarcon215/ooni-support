#!/bin/bash

# 1. Fetch any dependencies
# we should have everything in the virtualenv? Or do we need to also get some
# system libraries? libyaml, anyone?
source /etc/mlab/slice-functions

set -e

# TODO: remove this is nothing breaks. 
#yum install -y PyYAML python-ipaddr

# 2. Generate a ssl certificate
cd $SLICEHOME

#XXX: we should think about setting these fields more carefully
OPENSSL_SUBJECT="/C=US/ST=CA/CN="`hostname`
OPENSSL_PASS=file:$SLICEHOME/cert.pass
sudo -u $SLICENAME dd if=/dev/random of=$SLICEHOME/cert.pass bs=32 count=1
sudo -u $SLICENAME openssl genrsa -des3 -passout $OPENSSL_PASS -out private.key 4096
sudo -u $SLICENAME openssl req -new -passin $OPENSSL_PASS -key private.key -out server.csr -subj $OPENSSL_SUBJECT
sudo -u $SLICENAME cp private.key private.key.org

# Remove passphrase from key
sudo -u $SLICENAME openssl rsa -passin file:$SLICEHOME/cert.pass -in private.key.org -out private.key
sudo -u $SLICENAME chmod 600 private.key
sudo -u $SLICENAME openssl x509 -req -days 365 -in server.csr -signkey private.key -out certificate.crt
rm private.key.org
rm cert.pass

# get the UID and GID to drop privileges to
OONIB_UID=`id -u $SLICENAME`
OONIB_GID=`id -g $SLICENAME`

# randomly select either a tcp backend helper or a http backend helper to
# listen on port 80. Otherwise, bind to port 81
coin=$[$RANDOM % 2]
if [[ $coin > 0 ]]; then
  TCP_ECHO_PORT=80
  HTTP_ECHO_PORT=81
else
  TCP_ECHO_PORT=81
  HTTP_ECHO_PORT=80
fi

# NOTE: create a directory for raw ooni reports before archiving.
ARCHIVE_DIR=$SLICERSYNCDIR
REPORT_DIR=/var/spool/raw_reports
DATA_DIR=$SLICEHOME/data
TOR_DIR=$DATA_DIR/tor
INPUT_DIR=$DATA_DIR/inputs
DECK_DIR=$DATA_DIR/decks

mkdir -p $REPORT_DIR
mkdir -p $TOR_DIR
mkdir -p $INPUT_DIR
mkdir -p $DECK_DIR

chown $SLICENAME:slices $REPORT_DIR

# drop a config in $SLICEHOME
echo "
main:
    report_dir: '$REPORT_DIR'
    archive_dir: '$ARCHIVE_DIR'
    input_dir: '$INPUT_DIR'
    deck_dir: '$DECK_DIR'

    policy_file: '$DATA_DIR/policy.yaml'
    bouncer_file: '$DATA_DIR/bouncer.yaml'

    tor_datadir: '$TOR_DIR'
    tor_binary: '$SLICEHOME/bin/tor'
    tor2webmode: true
    tor_hidden_service: true

    database_uri: 'sqlite://$SLICEHOME/oonib_test_db.db'
    db_threadpool_size: 10

    logfile: '$SLICEHOME/oonib.log'
    pidfile: '$SLICEHOME/oonib.pid'
    nodaemon: false
    originalname: Null
    chroot: Null
    rundir: '$SLICEHOME'
    umask: Null
    euid: Null
    uid: $OONIB_UID
    gid: $OONIB_GID
    socks_port: 9055
    uuid: Null
    no_save: true
    profile: Null
    debug: false
    stale_time: 3600

helpers:
    http-return-json-headers:
        address: Null
        port: $HTTP_ECHO_PORT
        server_version: Apache

    tcp-echo:
        address: Null
        port: $TCP_ECHO_PORT

    daphn3:
        yaml_file: Null
        pcap_file: Null
        port: Null

    dns:
        address: Null
        udp_port: Null
        tcp_port: Null

    ssl:
        address: Null
        private_key: '$SLICEHOME/private.key'
        certificate: '$SLICEHOME/certificate.crt'
        port: 443" > $SLICEHOME/oonib.conf

chown $SLICENAME:slices $SLICEHOME/oonib.conf

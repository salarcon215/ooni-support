#!/usr/bin/env python

# This script builds the portion of the bouncer.yaml config file for the Ooni
# collector and test helpers running on an M-Lab slice. To use it, run `python
# getconfig.py`, and if all goes well, the YAML portion will be printed to
# stdout. If something goes wrong, an error message will be printed to stdout,
# and the exit status will be non-zero. The script assumes the oonib.conf file
# is in /home/mlab_ooni/oonib.conf. If not, pass the path as the first command
# line option.

import sys
import os
import yaml
import json
import subprocess
import urllib2

# For a hack
import time

MLAB_SIMULATOR_URL = "http://127.0.0.1:8585/update-ooni"

def get_bouncer_config_part(oonib_conf):
    try:
        # Open this slice's oonib.conf
        f = open(oonib_conf, "r")
        oonib_conf_contents = f.read()
        f.close()
        oonib_conf_parsed = yaml.safe_load(oonib_conf_contents)
    except IOError:
        return_failure("Couldn't read oonib.conf")

    try:
        # Read this slice's (collector) .onion address.
        tor_datadir = oonib_conf_parsed['main']['tor_datadir']
        tor_hostname_path = os.path.join(tor_datadir, 'collector', 'hostname')
        f = open(tor_hostname_path, "r")
        tor_onion_address = f.read().strip()
        f.close()
    except IOError:
        return_failure("Couldn't read Tor hostname file")
    except KeyError:
        return_failure("Oonib.conf is not valid or is missing information.")

    # Find this slice's IP address.
    slice_ipv4_address = get_ipv4_address()

    # List the running test helpers and their addresses.
    test_helpers = {}
    # FIXME: This should be a dynamically-generated list of all the test helpers
    # that are actually running. However, I have no idea how to infer which ones
    # are running and which ones aren't from the oonib.conf, since it seems to
    # be the same regardless of whether they're running or not (is there some
    # other source of information?)
    try:
        # For this first M-Lab deployment, we only support one test, which is
        # http-return-json-headers. In the future, this script should
        # automatically determine which helpers are running on a slice and
        # include exactly those. This is tracked in:
        # https://github.com/m-lab-tools/ooni-support/issues/55

        http_return_headers_port = oonib_conf_parsed['helpers']['http-return-json-headers']['port']
        if http_return_headers_port is not None:
            test_helpers['http-return-json-headers'] = 'http://' + slice_ipv4_address + ':' + str(http_return_headers_port)

        tcp_echo_port = oonib_conf_parsed['helpers']['tcp-echo']['port']
        if tcp_echo_port is not None:
            test_helpers['tcp-echo'] = slice_ipv4_address + ':' + str(tcp_echo_port)

        # FIXME: What about the UDP port?
        dns_tcp_port = oonib_conf_parsed['helpers']['dns']['tcp_port']
        if dns_tcp_port is not None:
            test_helpers['dns'] = slice_ipv4_address + ':' + str(dns_tcp_port)

        # FIXME: What about the 'address' field of the ssl helper?
        ssl_port = oonib_conf_parsed['helpers']['ssl']['port']
        if ssl_port is not None:
            test_helpers['ssl'] = "https://" + slice_ipv4_address + ':' + str(ssl_port)

        # FIXME: Add daphn3 test helper.

    except KeyError:
        return_failure("Oonib.conf is not valid or is missing information.")

    config_part = {
        'httpo://' + tor_onion_address: {
            'test-helpers': test_helpers
        }
    }

    return config_part

def get_ipv4_address():
    output = subprocess.Popen(["/home/mlab_ooni/bin/get_ipv4.sh"], stdout=subprocess.PIPE).communicate()[0]
    return output.strip()

def return_failure(msg):
    print "ERROR: " + msg
    exit(1)

def put_config(oonib_conf):
    part = get_bouncer_config_part(oonib_conf)
    put_parameters = {
        'city': 'foobar',
        'country': 'foobar',
        'fqdn': "nothing.google.com" + str(time.time()),
        'ip': '127.0.0.1',
        'port': '0',
        'site': 'mars',
        'tool_extra': part
    }
    send_put(json.dumps(put_parameters))
    
def send_put(json_body):
    # https://stackoverflow.com/questions/111945/is-there-any-way-to-do-http-put-in-python
    opener = urllib2.build_opener(urllib2.HTTPHandler)
    request = urllib2.Request(MLAB_SIMULATOR_URL, data=json_body)
    request.add_header('Content-Type', 'application/json')
    request.get_method = lambda: 'PUT'
    opener.open(request)

oonib_conf = '/home/mlab_ooni/oonib.conf'
if len(sys.argv) >= 2:
    oonib_conf = sys.argv[1]

put_config(oonib_conf)

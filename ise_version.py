#!/usr/bin/env python
"""
Get the ISE node version information.

Usage: ise_version.py

Requires the following environment variables:
  - ISE_HOSTNAME : the hostname or IP address of your ISE PAN node
  - ISE_REST_USERNAME : the ISE ERS admin or operator username
  - ISE_REST_PASSWORD : the ISE ERS admin or operator password
  - ISE_CERT_VERIFY : validate the ISE certificate (true/false)

Set the environment variables using the `export` command:
  export ISE_HOSTNAME='1.2.3.4'
  export ISE_REST_USERNAME='admin'
  export ISE_REST_PASSWORD='C1sco12345'
  export ISE_CERT_VERIFY=false

You may `source` the export lines from a text file for use:
  source ise.sh
"""

import requests
import json
import yaml
import os
import sys

# Silence any warnings about certificates
requests.packages.urllib3.disable_warnings()

# Load Environment Variables
env = { k : v for (k, v) in os.environ.items() }

# Fetch the ISE Version
url = 'https://'+env['ISE_HOSTNAME']+'/ers/config/op/systemconfig/iseversion'
r = requests.get(url,
                 auth=(env['ISE_REST_USERNAME'], env['ISE_REST_PASSWORD']),
                 headers={'Accept': 'application/json'},
                 verify=(False if env['ISE_CERT_VERIFY'][0:1].lower() in ['f','n'] else True)
                )

# Sample output:
#
# {
#   "OperationResult" : {
#     "resultValue" : [ {
#       "value" : "3.1.0.518",
#       "name" : "version"
#     }, {
#       "value" : "1",
#       "name" : "patch information"
#     } ]
#   }
# }
# 

values = r.json()['OperationResult']['resultValue']

version_info = {}
for item in values :
    version_info[item['name']] = item['value']

# Rename patch key
version_info['patch'] = version_info['patch information']
del version_info['patch information']

# Split version into sequence identifiers
( version_info['major'], 
  version_info['minor'], 
  version_info['maintenance'], 
  version_info['build']
) = version_info['version'].split('.')

# print(json.dumps(version_info, indent=2))
print(yaml.dump(version_info, indent=2))


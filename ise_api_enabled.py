#!/usr/bin/env python3
"""
Enable the ISE APIs using (synchronous) APIs!

Usage:

  ise_api_enabled.py

Requires setting the these environment variables using the `export` command:
  export ISE_PPAN='1.2.3.4'             # hostname or IP address of ISE PAN
  export ISE_REST_USERNAME='admin'      # ISE ERS admin or operator username
  export ISE_REST_PASSWORD='C1sco12345' # ISE ERS admin or operator password
  export ISE_VERIFY=false               # validate the ISE certificate

You may add these `export` lines to a text file, customize them, and load with `source`:
  source ise_environment.sh

"""
__author__ = "Thomas Howard"
__email__ = "thomas@cisco.com"
__license__ = "MIT - https://mit-license.org/"

import os
import requests
import sys

requests.packages.urllib3.disable_warnings() # Silence any requests package warnings about certificates


def ise_open_api_enable (session:requests.Session=None, ssl_verify:bool=True) :
    url = 'https://'+env['ISE_PPAN']+'/admin/API/apiService/update'
    data = '{ "papIsEnabled":true, "psnsIsEnabled":true }'
    r = session.post(url, data=data, verify=ssl_verify)
    if r.status_code == 200:
        print(f"✅ {r.status_code} ISE Open APIs Enabled")
    elif r.status_code == 500: # 500 if already enabled
        print(f"✅ {r.status_code} ISE Open APIs Enabled already")
    else :
        print(f"❌ {r.status_code} ISE Open APIs Disabled")


def ise_ers_api_enable (session:requests.Session=None, ssl_verify:bool=True) :
    url = 'https://'+env['ISE_PPAN']+'/admin/API/NetworkAccessConfig/ERS'
    data = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<ersConfig>
<id>1</id>
<isCSRFCheck>false</isCSRFCheck>
<isPapEnabled>true</isPapEnabled>
<isPsnsEnabled>true</isPsnsEnabled>
</ersConfig>
"""
    r = session.put(url, data=data, headers={'Content-Type': 'application/xml', 'Accept': 'application/xml'}, verify=ssl_verify)
    print(f"{'✅' if r.ok else '❌'} {r.status_code} ISE ERS APIs {'Enabled' if r.ok else 'Disabled'}")


if __name__ == "__main__":
    """
    Entrypoint for local script.
    """
    env_required_variables = ['ISE_PPAN', 'ISE_REST_USERNAME', 'ISE_REST_PASSWORD', 'ISE_VERIFY']
    env = { k : v for (k,v) in os.environ.items() } # Load environment variables
    for v in env_required_variables: 
        if env.get(v, None) == None:
            sys.exit(f"Missing environment variable {v}")

    ssl_verify = False if env['ISE_VERIFY'][0:1].lower() in ['f','n'] else True

    with requests.Session() as session:
      session = requests.Session()
      session.auth = auth=( env['ISE_REST_USERNAME'], env['ISE_REST_PASSWORD'] )
      session.headers.update({'Content-Type': 'application/json', 'Accept': 'application/json'})

      try:
          ise_open_api_enable(session, ssl_verify)
          ise_ers_api_enable(session, ssl_verify)
      except requests.exceptions.ConnectTimeout as e:
          sys.exit(f"⏳ Connection timeout - Verify Connectivity. {e}")
      except Exception as e:
          sys.exit(f"Exception: {e}")
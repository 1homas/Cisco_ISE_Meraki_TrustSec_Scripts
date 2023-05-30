#!/usr/bin/env python3
"""
Enable the ISE APIs
Author: Thomas Howard, thomas@cisco.com

Usage

  ise_api_enabled_async.py

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

import asyncio
import aiohttp
import os
import sys

# Globals
CONTENT_TYPE_JSON = 'application/json'
CONTENT_TYPE_XML = 'application/xml'
JSON_HEADERS = {'Accept':CONTENT_TYPE_JSON, 'Content-Type':CONTENT_TYPE_JSON}
XML_HEADERS = {'Accept':CONTENT_TYPE_XML, 'Content-Type':CONTENT_TYPE_XML}

# Limit TCP connection pool size to prevent connection refusals by ISE!
# 30 for ISE 2.6+; See https://cs.co/ise-scale for Concurrent ERS Connections.
# Testing with ISE 3.0 shows *no* performance gain for >5-10
TCP_CONNECTIONS_DEFAULT=10
TCP_CONNECTIONS_MAX=30
TCP_CONNECTIONS=5


async def ise_open_api_enable (session) :
    """
    """

    data = '{ "papIsEnabled":true, "psnsIsEnabled":true }'
    async with session.post('/admin/API/apiService/update', data=data) as response :
        # print(response.status)
        # print(await response.text())
        if (response.status == 200 or response.status == 500 ) :
            print("✅ ISE Open APIs Enabled")


async def ise_ers_api_enable (session) :
    """
    """

    session.headers['Content-Type'] = CONTENT_TYPE_XML
    session.headers['Accept'] = CONTENT_TYPE_XML
    data = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<ersConfig>
<id>1</id>
<isCSRFCheck>false</isCSRFCheck>
<isPapEnabled>true</isPapEnabled>
<isPsnsEnabled>true</isPsnsEnabled>
</ersConfig>
"""

    async with session.put('/admin/API/NetworkAccessConfig/ERS', data=data) as response :
        # print(response.status)
        # print(await response.text())
        if (response.status == 200) :
            print("✅ ISE ERS APIs Enabled")


async def main():

    # Load Environment Variables
    env = { k : v for (k, v) in os.environ.items() if k.startswith('ISE_') }

    # Create HTTP session
    ssl_verify = (False if env['ISE_CERT_VERIFY'][0:1].lower() in ['f','n'] else True)
    tcp_conn = aiohttp.TCPConnector(limit=TCP_CONNECTIONS, limit_per_host=TCP_CONNECTIONS, ssl=ssl_verify)
    auth = aiohttp.BasicAuth(login=env['ISE_REST_USERNAME'], password=env['ISE_REST_PASSWORD'])
    base_url = f"https://{env['ISE_HOSTNAME']}"
    session = aiohttp.ClientSession(base_url, auth=auth, connector=tcp_conn, headers=JSON_HEADERS)

    await ise_open_api_enable(session)
    await ise_ers_api_enable(session)
    await session.close()


if __name__ == "__main__":
    """
    Entrypoint for local script.
    """
    asyncio.run(main())
    sys.exit(0) # 0 is ok

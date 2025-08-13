#!/usr/bin/env python3
"""

Clear (delete) all ISE TrustSec data.

Examples:
    ise_trustsec_clear.py 
    ise_trustsec_clear.py -v
    ise_trustsec_clear.py -vvv
    ise_trustsec_clear.py -vvv -it

Requires setting the these environment variables using the `export` command:
  export ISE_PPAN='1.2.3.4'             # hostname or IP address of ISE PAN
  export ISE_REST_USERNAME='admin'      # ISE ERS admin or operator username
  export ISE_REST_PASSWORD='C1sco12345' # ISE ERS admin or operator password
  export ISE_VERIFY=false               # validate the ISE certificate

You may add these export lines to a text file and load with `source`:
  source ise.sh

"""
__author__ = "Thomas Howard"
__email__ = "thomas@cisco.com"
__license__ = "MIT - https://mit-license.org/"

import aiohttp
import asyncio
import argparse
import csv
import io
import json
import os
import sys
import time
import pandas as pd         # dataframes

# Globals
JSON_HEADERS = {'Accept':'application/json', 'Content-Type':'application/json'}
REST_PAGE_SIZE_DEFAULT=20
REST_PAGE_SIZE_MAX=100
REST_PAGE_SIZE=REST_PAGE_SIZE_MAX

# Limit TCP connection pool size to prevent connection refusals by ISE!
# 30 for ISE 2.6+; See https://cs.co/ise-scale for Concurrent ERS Connections.
# Testing with ISE 3.0 shows *no* performance gain for >5-10
TCP_CONNECTIONS_DEFAULT=10
TCP_CONNECTIONS_MAX=30
TCP_CONNECTIONS=5

SGT_RESERVED_NAMES = {
    'Unknown'           : 0,        # ISE & Meraki
    'TrustSec_Devices'  : 2,        # ISE
    'Infrastructure'    : 2,        # Meraki
    'Any'               : 65535,    # ISE
}

async def get_ise_resource (session, url) :
    async with session.get(url) as resp:
        json = await resp.json()
        # if args.verbose >= 3 : print(f"ⓘ get_ise_resource({url}): {json}")
        return json['SearchResult']['resources']


async def get_ise_resources (session, path) :
    """
    Fetch the resources from ISE.
    @session : the aiohttp session to reuse
    @path : the REST endpoint path
    """
    if args.verbose >= 3 : print(f"ⓘ get_ise_resources({path})")

    # Get the first page for the total resources
    response = await session.get(f"{path}?size={REST_PAGE_SIZE}")
    if response.status != 200:
        raise ValueError(f"Bad status: {response}")
    json = await response.json()
    total = json['SearchResult']['total']
    resources = json['SearchResult']['resources']
    if args.verbose >= 3 : print(f"ⓘ get_ise_resources({path}): Total: {total}")

    # Get all remaining resources if more than the REST page size
    if total > REST_PAGE_SIZE :
        pages = int(total / REST_PAGE_SIZE) + (1 if total % REST_PAGE_SIZE else 0)
        
        # Generate all paging URLs 
        urls = []
        for page in range(2, pages + 1): # already fetched first page above
            urls.append(f"{path}?size={REST_PAGE_SIZE}&page={page}")

        # Get all pages with asyncio!
        tasks = []
        [ tasks.append(asyncio.ensure_future(get_ise_resource(session, url))) for url in urls ]
        responses = await asyncio.gather(*tasks)
        [ resources.extend(response) for response in responses ]

    # remove ugly 'link' attribute to flatten data
    for r in resources:
        if type(r) == dict and r.get('link'): 
            del r['link']

    return resources


async def get_ise_resource_details (session, ers_name, path) :
    """
    Fetch the resources from ISE.
    @session : the aiohttp session to reuse
    @ers_name : the ERS object name in the JSON
    @path : the REST endpoint path
    """
    if args.verbose >= 3 : print(f"ⓘ get_ise_resource_details({ers_name}, {path})")

    # Get all resources for their UUIDs
    resources = await get_ise_resources(session, path)

    # Save UUIDs
    uuids = [r['id'] for r in resources]
    resources = [] # clear list for detailed data
    for uuid in uuids:
        async with session.get(f"{path}/{uuid}") as resp:
            json = await resp.json()
            resources.append(json[ers_name])

    # remove ugly 'link' attribute to flatten data
    for r in resources:
        if type(r) == dict and r.get('link'): 
            del r['link']

    return resources


async def delete_ise_resources (session, ers_name, path, resources) :
    """
    POST the resources to ISE.
    @session : the aiohttp session to reuse
    @ers_name : the ERS object name in the JSON
    @path : the REST endpoint path
    @resources : a list of resources identifiers (id or name)
    """
    if args.verbose >= 3 : print(f"ⓘ > delete_ise_resources({ers_name}, {path}, {len(df)})")

    for resource in resources :
        if args.verbose : print(f"delete resource: {path}/{resource}")
        async with session.delete(f"{path}/{resource}") as resp:
            if resp.ok : print(f"⌫ {resp.status} {resource}")
            # elif resp.status == 400 : print(f"ⓘ  {resp.status} {row['name']} {(await resp.json())['ERSResponse']['messages'][0]['title']}")
            else : print(f"❌ {resp.status} {(await resp.json())['ERSResponse']['messages'][0]['title']}")

    if args.verbose : print(f"ⓘ < delete_ise_resources({ers_name}, {path}) {len(resources)}")


async def get_ise_resource (session, url) :
    async with session.get(url) as resp:
        json = await resp.json()
        # if args.verbose : print(f'ⓘ get_ise_resource({url}): {json}')
        return json['SearchResult']['resources']


async def get_ise_resources (session, path) :
    """
    Fetch the resources from ISE.
    @session : the aiohttp session to reuse
    @path : the REST endpoint path
    """
    if args.verbose : print(f'ⓘ > get_ise_resources({path})')

    # Get the first page for the total resources
    response = await session.get(f'{path}?size={REST_PAGE_SIZE}')
    if response.status != 200:
        raise ValueError(f'Bad status: {response}')
    json = await response.json()
    total = json['SearchResult']['total']
    resources = json['SearchResult']['resources']
    if args.verbose : print(f'ⓘ  get_ise_resources({path}): Total: {total}')

    # Get all remaining resources if more than the REST page size
    if total > REST_PAGE_SIZE :
        pages = int(total / REST_PAGE_SIZE) + (1 if total % REST_PAGE_SIZE else 0)
        
        # Generate all paging URLs 
        urls = []
        for page in range(2, pages + 1): # already fetched first page above
            urls.append(f'{path}?size={REST_PAGE_SIZE}&page={page}')

        # Get all pages with asyncio!
        tasks = []
        [ tasks.append(asyncio.ensure_future(get_ise_resource(session, url))) for url in urls ]
        responses = await asyncio.gather(*tasks)
        [ resources.extend(response) for response in responses ]

    # remove ugly 'link' attribute to flatten data
    for r in resources:
        if type(r) == dict and r.get('link'): 
            del r['link']

    if args.verbose : print(f'ⓘ < get_ise_resources({path}) {len(resources)} resources')
    return resources



async def ise_trustsec_clear (session) :

    sgts = await get_ise_resources (session, '/ers/config/sgt')
    await delete_ise_resources(session, 'Sgt', '/ers/config/sgt', [sgt['id'] for sgt in sgts])
    sgacls = await get_ise_resources (session, '/ers/config/sgacl')
    await delete_ise_resources(session, 'Sgacl', '/ers/config/sgacl', [sgacl['id'] for sgacl in sgacls])
    cells = await get_ise_resources (session, '/ers/config/egressmatrixcell')
    await delete_ise_resources(session, 'EgressMatrixCell', '/ers/config/egressmatrixcell', [cell['id'] for cell in cells])


async def parse_cli_arguments () :
    """
    Parse the command line arguments
    """
    ARGS = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ARGS.add_argument('-t', '--timer', action='store_true', default=False, help='show response timer' )
    ARGS.add_argument('-v', '--verbose', action='store_true', default=False, help='Verbosity; multiple allowed')
    return ARGS.parse_args()


async def main ():
    """
    Entrypoint for packaged script.
    """

    global args     # promote to global scope for use in other functions
    args = await parse_cli_arguments()
    if args.verbose >= 3 : print(f"ⓘ Args: {args}")
    if args.verbose : print(f"ⓘ TCP_CONNECTIONS: {TCP_CONNECTIONS}")
    if args.verbose : print(f"ⓘ REST_PAGE_SIZE: {REST_PAGE_SIZE}")
    if args.verbose : print(f"ⓘ filename: {args.filename}")
    if args.timer :
        global start_time
        start_time = time.time()

    # Load Environment Variables
    global env
    env = { k : v for (k, v) in os.environ.items() if k.startswith('ISE_') }


    try :
        # Create HTTP session
        ssl_verify = (False if env['ISE_VERIFY'][0:1].lower() in ['f','n'] else True)
        tcp_conn = aiohttp.TCPConnector(limit=TCP_CONNECTIONS, limit_per_host=TCP_CONNECTIONS, ssl=ssl_verify)
        auth = aiohttp.BasicAuth(login=env['ISE_REST_USERNAME'], password=env['ISE_REST_PASSWORD'])
        base_url = f"https://{env['ISE_PPAN']}"
        session = aiohttp.ClientSession(base_url, auth=auth, connector=tcp_conn, headers=JSON_HEADERS)

        await ise_trustsec_clear(session)

    except aiohttp.ContentTypeError as e :
        print(f"\n❌ Error: {e.message}\n\n💡Enable the ISE REST APIs\n")
    except aiohttp.ClientConnectorError as e :  # cannot connect to host
        print(f"\n❌ Host unreachable: {e}\n", file=sys.stderr)
    except aiohttp.ClientError as e :           # base aiohttp Exception
        print(f"\n❌ Exception: {e}\n", file=sys.stderr)
    except:                                     # catch *all* exceptions
        print(f"\n❌ Exception: {e}\n", file=sys.stderr)
    finally:
        await session.close()

    if args.timer :
        duration = time.time() - start_time
        print(f"\n 🕒 {duration} seconds\n", file=sys.stderr)


if __name__ == '__main__':
    """
    Entrypoint for local script.
    """
    asyncio.run(main())

    sys.exit(0) # 0 is ok

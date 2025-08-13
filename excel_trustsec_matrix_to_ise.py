#!/usr/bin/env python3
"""

Show ISE TrustSec data.

Examples:
    excel_trustsec_matrix_to_ise.py 
    excel_trustsec_matrix_to_ise.py -v
    excel_trustsec_matrix_to_ise.py -f ise_trustsec_matrix_default.xlsx
    excel_trustsec_matrix_to_ise.py -vvv -it

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
import random
import sys
import time
import pandas as pd
from tabulate import tabulate

# Globals
DATA_DIR = './'
DEFAULT_TRUSTSEC_FILENAME = 'ise_trustsec_matrix.xlsx'

# REST Options
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

# CSV table for ISE REST API resource names and mappings
REST_ENDPOINT_URLS = """
'resource',         'object',           'url'
'sgt',              'Sgt',              '/ers/config/sgt'
'sgacl',            'Sgacl',            '/ers/config/sgacl'
'egressmatrixcell', 'EgressMatrixCell', '/ers/config/egressmatrixcell'
"""

# This hidden SGT is required for lookups with the default ANY-ANY SGACL.
SGT_ANY = {'id':'92bb1950-8c01-11e6-996c-525400b48521', 'name':'ANY', 'description':'ANY', 'value':65535, 'generationId':0, 'propogateToApic':False}


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
        if args.verbose >= 3 : print(f"delete resource: {path}/{resource}")
        async with session.delete(f"{path}/{resource}") as resp:
            if resp.ok : print(f"⌫ {resp.status} {resource}")
            # elif resp.status == 400 : print(f"ⓘ  {resp.status} {row['name']} {(await resp.json())['ERSResponse']['messages'][0]['title']}")
            else : print(f"❌ {resp.status} {(await resp.json())['ERSResponse']['messages'][0]['title']}")

    if args.verbose >= 3 : print(f"ⓘ < delete_ise_resources({ers_name}, {path}) {len(resources)}")



async def post_simple_ise_resources (session, ers_name, path, df) :
    """
    POST the resources to ISE.
    @session : the aiohttp session to reuse
    @ers_name : the ERS object name in the JSON
    @path : the REST endpoint path
    @df : the dataframe of resources to create
    """
    if args.verbose >= 3 : print(f"ⓘ > post_simple_ise_resources({ers_name}, {path}, {len(df)})")

    for row in df.to_dict('records'):
        if args.verbose >= 3 : print(f"row: {row}")
        resource = { ers_name : row }
        if args.verbose >= 3 : print(f"resource: {resource}")
        if args.verbose >= 3 : print(f"resource as json: {json.dumps(resource)}")
        async with session.post(f"{path}", data=json.dumps(resource)) as resp:
            if resp.ok : print(f"🌟 {resp.status} {row['name']}")
            elif resp.status == 400 : print(f"ⓘ  {resp.status} {row['name']} {(await resp.json())['ERSResponse']['messages'][0]['title']}")
            else : print(f"❌ {resp.status} {(await resp.json())['ERSResponse']['messages'][0]['title']}")

    # Get newly created resources
    resources = await get_ise_resources(session, path)
    resources = await get_ise_resource_details(session, ers_name, path)

    if args.verbose >= 3 : print(f"ⓘ < post_simple_ise_resources({ers_name}, {path}) {len(resources)}")

    return resources


async def excel_trustsec_matrix_to_ise (session, filename) :
    """
    Read the TrustSec Matrix, SGTs, and SGACLs from Excel and load into ISE.
    """
    
    #--------------------------------------------------------------------------
    # Read Excel Workbook with Worksheets ['Matrix', 'SGACLs']
    #--------------------------------------------------------------------------
    # df_sgts = pd.read_excel(filename, sheet_name='SGTs').fillna('')
    df_sgacls = pd.read_excel(filename, sheet_name='SGACLs').fillna('')
    df_matrix = pd.read_excel(filename, sheet_name='Matrix').fillna('')
    
    # print(f"\nSGTs:\n{df_sgts.to_markdown(index=False, tablefmt='simple_grid')}")
    if args.verbose >= 3 : print(f"\nSGACLs:\n{df_sgacls.to_markdown(index=False, tablefmt='simple_grid')}")
    if args.verbose >= 3 : print(f"\nMatrix:\n{df_matrix.to_markdown(index=False, tablefmt='simple_grid')}")

    #--------------------------------------------------------------------------
    # Configure SGTs from Matrix
    #--------------------------------------------------------------------------
    df_sgts = df_matrix[['SGT','Value','Description']].copy()
    df_sgts.rename(columns={'SGT':'name','Value':'value','Description':'description'}, inplace=True)

    # remove Reserved SGTs
    RESERVED_SGT_NAMES = ['Unknown', 'TrustSec_Devices']
    for name in RESERVED_SGT_NAMES :
        df_sgts.drop(df_sgts[df_sgts['name'] == name].index, inplace=True)

    # if args.verbose : print(f"ⓘ Creating {len(df_sgts)} SGTs ...")
    sgts = await post_simple_ise_resources (session, 'Sgt', '/ers/config/sgt', df_sgts)
    if args.verbose >= 3 : print(f"\nⓘ SGTs:\n{sgts}")

    #--------------------------------------------------------------------------
    # Configure SGACLs
    #--------------------------------------------------------------------------
    df_sgacls.drop(['generationId'], axis='columns', inplace=True)

    # remove Reserved SGACLs
    RESERVED_SGACL_NAMES = ['Deny IP', 'Deny_IP_Log', 'Permit IP', 'Permit_IP_Log']
    for name in RESERVED_SGACL_NAMES :
        df_sgacls.drop(df_sgacls[df_sgacls['name'] == name].index, inplace=True)

    sgacls = await post_simple_ise_resources (session, 'Sgacl', '/ers/config/sgacl', df_sgacls)
    if args.verbose >= 3 : print(f"\nⓘ SGACLs:\n{sgacls}")

    #--------------------------------------------------------------------------
    # Configure Matrix Cell JSON:
    # {
    #     "EgressMatrixCell": {
    #         "name": "ANY-ANY",
    #         "description": "Default egress rule",
    #         "sourceSgtId": "92bb1950-8c01-11e6-996c-525400b48521",
    #         "destinationSgtId": "92bb1950-8c01-11e6-996c-525400b48521",
    #         "matrixCellStatus": "ENABLED",
    #         "sgacls": [
    #           "92951ac0-8c01-11e6-996c-525400b48521"
    #         ],
    #         "defaultRule": "NONE"
    #     }
    # }
    #--------------------------------------------------------------------------
    df_sgts = pd.DataFrame(sgts)
    df_sgts.set_index('name', inplace=True)
    print(f"\nⓘ SGTs:\n{df_sgts[['value','description','generationId','propogateToApic']].to_markdown(tablefmt='simple_grid')}")

    df_sgacls = pd.DataFrame(sgacls)
    df_sgacls.set_index('name', inplace=True)
    # print(f"\nⓘ SGACLs:\n{df_sgacls.to_markdown(tablefmt='simple_grid')}")
    print(f"\nⓘ SGACLs:\n{df_sgacls.drop(['id'], axis='columns').to_markdown(tablefmt='simple_grid')}")
    
    resources = []
    for row in df_matrix.to_dict('records') :
        for col,val in row.items() :
            if args.verbose >= 3 : print(f"ⓘ row: {row} | col: {col} | val: {val}")
            if col not in ['SGT','Value','Description'] and val :
                resources.append(
                  {
                    "name": f"{row['SGT']}-{col}",              # <= 32 characters
                    "description": "",                          # <= 256 characters
                    "sourceSgtId": df_sgts['id'].at[row['SGT']],# UUID
                    "destinationSgtId": df_sgts['id'].at[col],  # UUID
                    "matrixCellStatus": "ENABLED",              # ['ENABLED' | 'DISABLED' | 'MONITOR']
                    "sgacls": [
                        df_sgacls['id'].at[val]                 # list of SGACL UUIDs
                    ],
                    "defaultRule": "NONE"                       # ['NONE','DENY IP','PERMIT IP']
                  }
                )
    df_resources = pd.DataFrame(resources)
    cells = await post_simple_ise_resources (session, 'EgressMatrixCell', '/ers/config/egressmatrixcell', df_resources)
    # df_cells = pd.DataFrame(cells)
    # print(f"\nCells:\n{df_cells.to_markdown(index=False, tablefmt='simple_grid')}")
    

async def parse_cli_arguments () :
    """
    Parse the command line arguments
    """
    ARGS = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ARGS.add_argument('-f', '--filename', action='store', type=str, help='TrustSec matrix filename', default=DEFAULT_TRUSTSEC_FILENAME)
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

        # await ise_trustsec_clear(session)
        sgts = await get_ise_resources (session, '/ers/config/sgt')
        await delete_ise_resources(session, 'Sgt', '/ers/config/sgt', [sgt['id'] for sgt in sgts])
        sgacls = await get_ise_resources (session, '/ers/config/sgacl')
        await delete_ise_resources(session, 'Sgacl', '/ers/config/sgacl', [sgacl['id'] for sgacl in sgacls])
        cells = await get_ise_resources (session, '/ers/config/egressmatrixcell')
        await delete_ise_resources(session, 'EgressMatrixCell', '/ers/config/egressmatrixcell', [cell['id'] for cell in cells])

        await excel_trustsec_matrix_to_ise(session, args.filename)

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

#!/usr/bin/env python3
"""

Show ISE TrustSec data.

Examples:
    ise_trustsec_export.py 
    ise_trustsec_export.py -v
    ise_trustsec_export.py -vvv
    ise_trustsec_export.py --filename my_prefix
    ise_trustsec_export.py -t -f 20250101_trustsec_backup

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
TRUSTSEC_BASE_FILENAME = 'ise_trustsec'

# Colors for matrix cells in Excel
CISCO_BLUE    = '#049fd9'
STATUS_BLUE   = '#64bbe3'
STATUS_GREEN  = '#6cc04a'
STATUS_ORANGE = '#ff7300'
STATUS_YELLOW = '#ffcc00'
LITE_GRAY     = '#F2F2F2'
LITE_GRAY2    = '#c6c7ca'
PALE_GRAY     = '#e8ebf1'
CELL_STATUS_RED    = '#CF2030'  # Status Red
CELL_COLOR_ALLOW   = STATUS_GREEN
CELL_COLOR_DENY    = '#EF7775'  # Status Red, 40% Lighter
CELL_COLOR_DEFAULT = LITE_GRAY  # default / empty
CELL_COLOR_CUSTOM  = STATUS_BLUE  # Cisco Blue

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

# This hidden SGT is required for lookups with the default ANY-ANY SGACL.
SGT_ANY = {'id':'92bb1950-8c01-11e6-996c-525400b48521', 'name':'ANY', 'description':'ANY', 'value':65535, 'generationId':0, 'propogateToApic':False}

SGT_ICONS = {
    'net'       : 0,
    'imac'      : 1,
    'cloud'     : 2,
    'user'      : 3,
    'mail'      : 4,
    'look'      : 5,
    'burn'      : 6,
    'structure' : 7,
    'iphone'    : 8,
    'folder'    : 9,
    'people'    : 10,
    'web'       : 11,
    'lock'      : 12,
    'clock'     : 13,
    'network'   : 14,
    'printer'   : 15,
    'database'  : 16,
    'talk'      : 17,
    'security'  : 18,
    'ring'      : 19,
    'lightning' : 20,
}

SGT_RESERVED_NAMES = {
    'Unknown'           : 0,        # ISE & Meraki
    'TrustSec_Devices'  : 2,        # ISE
    'Infrastructure'    : 2,        # Meraki
    'Any'               : 65535,    # ISE
}

SGT_RESERVED_NUMBERS = [0,1,2]+list(range(65519,65535))   # Reserved for Network Device internal use
SGT_VALID_NUMBERS = range(3,65519)

DEFAULT_SGTS = """
Icon,Name:String(32):Required,Value,Description:String(256)
0,BYOD,15,BYOD Security Group
0,PCI_Servers,14,PCI Servers Security Group
0,Auditors,9,Auditor Security Group
0,Contractors,5,Contractor Security Group
0,Developers,8,Developer Security Group
0,Development_Servers,12,Development Servers Security Group
0,Employees,4,Employee Security Group
0,Guests,6,Guest Security Group
0,Network_Services,3,Network Services Security Group
0,Point_of_Sale_Systems,10,Point of Sale Security Group
0,Production_Servers,11,Production Servers Security Group
0,Production_Users,7,Production User Security Group
0,Quarantined_Systems,255,Quarantine Security Group
0,Test_Servers,13,Test Servers Security Group
0,TrustSec_Devices,2,TrustSec Devices Security Group
0,Unknown,0,Unknown Security Group
"""

# ⚠ Notes on ISE `/ers/config/sgacl` API as of ISE 3.3
# - `readOnly` attribute is never returned
# - `readOnly` attribute cannot be set to `true` (HTTP/1.1 500)
# - `ipVersion` default is `IPV4` but attribute will not be returned if `IP_AGNOSTIC`
# - `aclcontent` may be anything - it is not validated
SGACL_IP_VALUES = ['IPV4','IPV6','IP_AGNOSTIC']

DEFAULT_SGACLS = """
name,description,ipVersion,aclcontent
Deny IP,Deny IP SGACL,IP_AGNOSTIC,deny ip
Deny_IP_Log,Deny IP with logging,IP_AGNOSTIC,deny ip log
Permit IP,Permit IP SGACL,IP_AGNOSTIC,permit ip
Permit_IP_Log,Permit IP with logging,IP_AGNOSTIC,permit ip log
"""

SGACL_BLOCKMALWARE = """
BlockMalware,Block Malware,IP_AGNOSTIC,"deny icmp
deny tcp dst eq 22
deny tcp dst eq 53
deny udp dst eq 53
deny udp dst eq 67
deny udp dst eq 68
deny udp dst eq 69
deny tcp dst eq 135
deny tcp dst eq 137
deny tcp dst eq 138
deny tcp dst eq 139
deny tcp dst eq 445
deny tcp dst eq 689
deny udp dst eq 1025
deny udp dst eq 1026
deny tcp dst eq 3389"
"""


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
    if args.verbose >= 4 : print(f'ⓘ get_ise_resources({path})')

    # Get the first page for the total resources
    response = await session.get(f'{path}?size={REST_PAGE_SIZE}')
    if response.status != 200:
        raise ValueError(f'Bad status: {response}')
    json = await response.json()
    total = json['SearchResult']['total']
    resources = json['SearchResult']['resources']
    if args.verbose : print(f'ⓘ get_ise_resources({path}): Total: {total}')

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

    return resources


async def get_ise_resource_details (session, ers_name, path) :
    """
    Fetch the resources from ISE.
    @session : the aiohttp session to reuse
    @ers_name : the ERS object name in the JSON
    @path : the REST endpoint path
    """
    if args.verbose >= 4 : print(f'ⓘ get_ise_resource_details({ers_name}, {path})')

    # Get all resources for their UUIDs
    resources = await get_ise_resources(session, path)

    # Save UUIDs
    uuids = [r['id'] for r in resources]
    resources = [] # clear list for detailed data
    for uuid in uuids:
        async with session.get(f'{path}/{uuid}') as resp:
            json = await resp.json()
            resources.append(json[ers_name])

    # remove ugly 'link' attribute to flatten data
    for r in resources:
        if type(r) == dict and r.get('link'): 
            del r['link']

    return resources


def create_trustsec_egress_policies_by_name (df_sgts, df_sgacls, matrix) :
    """
    Returns a dataframe of the TrustSec egress cell policies by names instead of UUIDs.
    """
    # print(f'\nTrustSec Matrix ({len(matrix)})\n')
    # matrix: ['id', 'name', 'description', 'sourceSgtId', 'destinationSgtId', 'matrixCellStatus', 'defaultRule', 'sgacls']
    df = pd.DataFrame(matrix)

    # assumes the df_sgts and df_sgacls have their index set on the id column
    df['SrcSGT'] = df['sourceSgtId'].map(lambda id: df_sgts.loc[id,'name'])
    df['DstSGT'] = df['destinationSgtId'].map(lambda id: df_sgts.loc[id,'name'])
    df['SGACLs'] = df['sgacls'].map(lambda l: [ df_sgacls.loc[id,'name'] for id in l ])
    # df['SGACLs'] = df['sgacls'].map(lambda l: ','.join([ df_sgacls.loc[id,'name'] for id in l ]) )

    # Re-order and drop columns
    df = df[['id', 'name', 'description', 'matrixCellStatus', 'SrcSGT', 'DstSGT', 'SGACLs', 'defaultRule',]]
    df = df.rename(columns={'id' : 'ID', 
                            'name' : 'Name', 
                            'description' : 'Description', 
                            'matrixCellStatus' : 'Status', 
                            'defaultRule' : 'DefaultRule'
                           }
                   )

    return df


def show (resources=None, format='dump', fh='-') :
    """
    Shows the resources in the specified format to the file handle.
    resources : 
    format : ['dump', 'line', 'pretty', 'table', 'csv', 'id', 'yaml']
    filehandle : Default: `sys.stdout`
    """
    if args.verbose : print(f"{len(resources)} resources of type ({type(resources[0])}): ")
    # 💡 Do not close sys.stdout or it may not be re-opened
    if fh == '-':
        fh = sys.stdout

    if format == 'dump':  # dump json
        # print(resources, end='\n', file=fh, flush=False)
        print(json.dumps(resources), file=fh)

    elif format == 'pretty':  # pretty-print
        print(json.dumps(resources, indent=2), file=fh)

    elif format == 'line':  # 1 line per object
        print('[')
        [print(json.dumps(r), end=',\n', file=fh) for r in resources]
        print(']')

    elif format == 'table':  # table
        print(f"\n{tabulate(resources, headers='keys', tablefmt='simple_grid')}", file=fh)

    elif format == 'id':  # list of ids
        ids = [[r['id']] for r in resources]  # single column table
        # print (f"ⓘ ids : {type(ids)} | {ids}")
        print(f"\n{tabulate(ids, tablefmt='plain')}", file=fh)

    elif format == 'csv':  # CSV
        headers = {}
        [headers.update(r) for r in resources]  # find all unique keys
        writer = csv.DictWriter(fh, headers.keys(), quoting=csv.QUOTE_MINIMAL)
        writer.writeheader()
        for row in resources:
            writer.writerow(row)

    elif format == 'yaml':  # YAML
        # [print(yaml.dump(r, indent=2, default_flow_style=False), file=fh) for r in resources]
        [print(yaml.dump(r, indent=2), file=fh) for r in resources]

    else:  # just in case something gets through the CLI parser
        print(MSG_CERTIFICATE_ERROR + f': {args.output}', file=sys.stderr)


async def ise_trustsec_export (session) :
    """
    Get and show the ISE TrustSec SGTs, SGACLs, and Matrix.
    """
    
    #--------------------------------------------------------------------------
    # Show on Terminal
    #--------------------------------------------------------------------------

    # Show SGTs
    sgts = await get_ise_resource_details(session, 'Sgt', '/ers/config/sgt')
    sgts.append(SGT_ANY)
    df_sgts = pd.DataFrame(sgts).fillna('')    # ['id', 'name', 'description', 'value', 'generationId', 'propogateToApic']
    df_sgts['generationId'] = df_sgts['generationId'].astype('int32')   # convert from text to int
    df_sgts.set_index('id', inplace=True) # required for name lookup for the matrix
    print(f"\nⓘ SGTs:\n{df_sgts.to_markdown(index=False, tablefmt='simple_grid')}\n")

    # Show SGACLs
    sgacls = await get_ise_resource_details(session, 'Sgacl', '/ers/config/sgacl')
    df_sgacls = pd.DataFrame(sgacls).fillna('')    # ['id', 'name', 'description', 'generationId', 'aclcontent']
    df_sgacls['generationId'] = df_sgacls['generationId'].astype('int32')   # convert from text to int
    df_sgacls.set_index('id', inplace=True) # required for name lookup for the matrix
    print(f"\nⓘ SGACLs:\n{df_sgacls.to_markdown(index=False, tablefmt='simple_grid')}\n")

    # Show Policies
    # ⚠ Raw policy data is a list of dicts with UUIDs for SGTs and SGACLs
    policies = await get_ise_resource_details(session, 'EgressMatrixCell', '/ers/config/egressmatrixcell')
    if args.verbose : print(f"\nⓘ Raw Policies with UUIDs:\n{policies}")

    df_policies = create_trustsec_egress_policies_by_name(df_sgts, df_sgacls, policies)
    df_policies['SGACLs'] = df_policies['SGACLs'].apply(lambda sgacls: ','.join(sgacls))
    print(f"\nⓘ Policies:\n{df_policies.to_markdown(index=False, tablefmt='simple_grid')}\n")

    df_matrix = df_sgts.drop(df_sgts[df_sgts['name'] == 'ANY'].index)   # do not show 'ANY' SGT
    df_matrix.sort_values(args.sort, inplace=True) # name or value
    df_matrix = df_matrix[['name', 'value', 'description']] # drop all other columns
    df_matrix.rename(columns={'name':'SGT','value':'Value','description':'Description'}, inplace=True)

    for column in df_matrix['SGT'] :
        df_matrix[column] = ""    # create empty matrix with default
    if args.verbose : print(f"\nⓘ Matrix after columns added:\n{df_matrix.to_markdown(index=False, tablefmt='simple_grid')}")
    
    # iterate over policies to fill in the matrix
    df_matrix.set_index('SGT', inplace=True)
    for row in df_policies.to_dict('records') :
        if row['SrcSGT'] == 'ANY' :
            pass    # do not include 'ANY'
        elif len(row['SGACLs']) > 0 :
            # use the SGACL(s)
            df_matrix.at[row['SrcSGT'], row['DstSGT']] = row['SGACLs']
        else :
            # use the default rule
            df_matrix.at[row['SrcSGT'], row['DstSGT']] = row['lastEntryRule']
    df_matrix.reset_index(names=['SGT'], inplace=True)   # keep the name column
    print(f"\nⓘ Matrix:\n{df_matrix.to_markdown(index=False, tablefmt='simple_grid')}\n")

    #--------------------------------------------------------------------------
    # Export dataframes to CSVs
    #--------------------------------------------------------------------------

    # Icon,Name:String(32):Required,Value,Description:String(256)
    df_sgts.insert(0, 'Icon', SGT_ICONS['security'])
    df_sgts = df_sgts.drop(df_sgts[df_sgts['name'] == 'ANY'].index)
    df_sgts.drop(['generationId', 'propogateToApic'], axis='columns') \
           .rename(columns={
                    'name' : 'Name:String(32):Required',
                    'description' : 'Description:String(256)',
                    'value' : 'Value',
                }) \
           .to_csv(DATA_DIR+args.filename+'_sgts.csv', index=False)

    # There is no CSV format for SGACLs so we will do the raw dataframe
    df_sgacls.to_csv(DATA_DIR+args.filename+'_sgacls.csv', index=False)

    #
    # ISE Policy Matrix CSV import/export header
    # EgressMatrixCells
    # - Source SGT:String(32):Required
    # - Destination SGT:String(32):Required
    # - SGACL Name:String(32):Required
    # - Rule Status:String(enabled|disabled|monitor):Required
    #
    # ['ID', 'Name', 'Description', 'Status', 'SrcSGT', 'DstSGT', 'SGACLs', 'DefaultRule']
    df_policies[['SrcSGT','DstSGT','SGACLs','Status',]] \
        .drop(df_policies[df_policies['SrcSGT'] == 'ANY'].index) \
        .rename(columns={
                'SrcSGT':'Source SGT:String(32):Required',
                'DstSGT':'Destination SGT:String(32):Required',
                'SGACLs':'SGACL Name:String(32):Required',
                'Status':'Rule Status:String(enabled|disabled|monitor):Required',
            }) \
        .to_csv(DATA_DIR+args.filename+'_matrix.csv', index=False)


    #--------------------------------------------------------------------------
    # Export dataframes to an Excel Workbook
    #--------------------------------------------------------------------------
    with pd.ExcelWriter(DATA_DIR+args.filename+'_matrix.xlsx', engine='xlsxwriter') as writer:

        df_matrix.to_excel(writer, sheet_name='Matrix', index=False)
        df_sgacls.to_excel(writer, sheet_name='SGACLs', index=False)
        df_sgts.to_excel(writer, sheet_name='SGTs', index=False)

        # 
        # Colorize the matrix sheet in Excel
        #
        
        # Apply a conditional format to the required cell range.
        (max_row, max_col) = df_matrix.shape
        workbook  = writer.book

        trustsec_cell_bg_allow   = workbook.add_format({'bg_color': CELL_COLOR_ALLOW})
        trustsec_cell_bg_deny    = workbook.add_format({'bg_color': CELL_COLOR_DENY})
        trustsec_cell_bg_default = workbook.add_format({'bg_color': CELL_COLOR_DEFAULT})
        trustsec_cell_bg_custom  = workbook.add_format({'bg_color': CELL_COLOR_CUSTOM})
        rotate_ccw               = workbook.add_format({'rotation': 45, 'border': 1})
        header                   = workbook.add_format({'align':'left', 'valign':'bottom'})
        reserved_sgts            = workbook.add_format({'bg_color': LITE_GRAY})
        
        worksheet = writer.sheets['Matrix']

        # Column widths
        for i,column in enumerate(df_matrix.columns, start=0) :
            if column == 'SGT' : 
                worksheet.set_column(i, i, \
                                    max(df_matrix['SGT'].apply(lambda x: len(x))), \
                                    workbook.add_format({'align':'left', 'valign':'bottom'}))
            elif column == 'Value' : 
                worksheet.set_column(i, i, 6, workbook.add_format({'align':'right', 'valign':'bottom'}))
            elif column == 'Description' : 
                worksheet.set_column(i, i, max(df_matrix['Description'].apply(lambda x: len(x)))/2, header)
            else : 
                worksheet.set_column(i, i, 12, header)
                worksheet.write(0, i, column, rotate_ccw)
 
        # With Row/Column notation, specify all cells in the range: (first_row, first_col, last_row, last_col)
        # SGT Reserved Values 0-2
        worksheet.conditional_format(1, 1, max_row, 1, 
                                        {
                                        'type':     'cell',
                                        'criteria': 'between',
                                        'minimum':  0,
                                        'maximum':  2,
                                        'format':   reserved_sgts
                                        })

        # SGT Reserved Values > 65519
        worksheet.conditional_format(1, 1, max_row, 1, 
                                        {
                                        'type':     'cell',
                                        'criteria': 'greater than',
                                        'minimum':  65519,
                                        'value':    'Reserved',
                                        'format':   reserved_sgts
                                        })

        # Empty cells
        worksheet.conditional_format(1, 3, max_row, max_col-1, 
                                        {
                                        'type':     'blanks',
                                        'format':   trustsec_cell_bg_default
                                        })

        # 'default' from Meraki
        worksheet.conditional_format(1, 3, max_row, max_col-1, 
                                        {
                                        'type':     'text',
                                        'criteria': 'begins with',
                                        'value':    'default',
                                        'format':   trustsec_cell_bg_default
                                        })

        # 'allow' from Meraki
        worksheet.conditional_format(1, 3, max_row, max_col-1,
                                        {
                                        'type':     'text',
                                        'criteria': 'begins with',
                                        'value':    'allow',
                                        'format':   trustsec_cell_bg_allow
                                        })

        # 'permit' default SGACLs from ISE
        worksheet.conditional_format(1, 3, max_row, max_col-1,
                                        {
                                        'type':     'text',
                                        'criteria': 'begins with',
                                        'value':    'permit',
                                        'format':   trustsec_cell_bg_allow
                                        })

        # 'deny' default SGACLs from ISE
        worksheet.conditional_format(1, 3, max_row, max_col-1,
                                        {
                                        'type':     'text',
                                        'criteria': 'begins with',
                                        'value':    'deny',
                                        'format':   trustsec_cell_bg_deny
                                        })

        # Custom SGACL Names
        worksheet.conditional_format(1, 3, max_row, max_col-1,
                                        {
                                        'type':     'no_blanks',
                                        'format':   trustsec_cell_bg_custom
                                        })

        # worksheet.select()      # tab highlighted
        worksheet.set_first_sheet() # First, leftmost, visible worksheet tab.
        worksheet.activate()    # initially visible in a multi-sheet workbook




async def parse_cli_arguments () :
    """
    Parse the command line arguments
    """
    ARGS = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ARGS.add_argument('-f', '--filename', required=False, help='filename', default=TRUSTSEC_BASE_FILENAME)
    # ARGS.add_argument('-o', '--output', choices=['dump', 'line', 'pretty', 'table', 'csv', 'id', 'yaml'], default='dump')
    ARGS.add_argument('-s', '--sort', choices=['name', 'value',], default='name', help='SGT sort key')
    ARGS.add_argument('-t', '--timer', action='store_true', default=False, help='show response timer')
    ARGS.add_argument('-v', '--verbose', action='store_true', default=False, help='Verbosity; multiple allowed')
    # ARGS.add_argument('--version', action='version', version=f'%(prog)s {VERSION}')
    return ARGS.parse_args()


async def main ():
    """
    Entrypoint for packaged script.
    """

    global args     # promote to global scope for use in other functions
    args = await parse_cli_arguments()
    if args.verbose >= 3 : print(f'ⓘ Args: {args}')
    if args.verbose : print(f'ⓘ TCP_CONNECTIONS: {TCP_CONNECTIONS}')
    if args.verbose : print(f'ⓘ REST_PAGE_SIZE: {REST_PAGE_SIZE}')
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

        await ise_trustsec_export(session)

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
        print(f'\n 🕒 {duration} seconds\n', file=sys.stderr)


if __name__ == '__main__':
    """
    Entrypoint for local script.
    """
    asyncio.run(main())

    sys.exit(0) # 0 is ok

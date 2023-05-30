#!/usr/bin/env python3
#------------------------------------------------------------------------------
# @author: Thomas Howard
# @email: thomas@cisco.com
#------------------------------------------------------------------------------
import argparse
import os
import meraki
import sys
import time
from tabulate import tabulate
import pandas as pd
import yaml
import xlsxwriter

# Globals
USAGE = """

Show ISE TrustSec data.

Examples:
    meraki_api_enabled.py 

Requires setting the these environment variables using the `export` command:
    export MERAKI_DASHBOARD_API_KEY='abcdef1234567890abcdef1234567890abcdef12'
    export MERAKI_ORG_NAME=example_org
    export MERAKI_NET_NAME=example_net

You may add these export lines to a text file and load with `source`:
  source meraki.sh

"""

MERAKI_DASHBOARD_BASE_URI = 'https://api.meraki.com/api/v1'


def parse_cli_arguments () :
    """
    Parse the command line arguments
    """
    ARGS = argparse.ArgumentParser(
            description=USAGE,
            formatter_class=argparse.RawDescriptionHelpFormatter,   # keep my format
            )
    ARGS.add_argument('-f', '--format', choices=['plain','simple','grid','simple_grid','pretty','presto'], default='simple_grid', help='table format' )
    ARGS.add_argument('-t', '--timer', action='store_true', default=False, help='show response timer' )
    ARGS.add_argument('-v', '--verbose', action='store_true', default=False, help='Verbosity; multiple allowed')
    # ARGS.add_argument('--version', action='version', version=f'%(prog)s {VERSION}')
    return ARGS.parse_args()



def meraki_api_enabled () :
    """
    Get and show the ISE TrustSec SGTs, SGACLs, and Matrix.
    """

    # MERAKI_DASHBOARD_API_KEY environment variable is used automatically  
    dashboard = meraki.DashboardAPI(
        output_log=False,
	    print_console=False,
        # suppress_logging=True,
    )

    global org_id
    if env['MERAKI_ORG_ID']:
        org_id = env['MERAKI_ORG_ID']
    else :
        org_id = dashboard.organizations.getOrganizations()[0]['id']


    orgs = dashboard.organizations.getOrganizations()
    df_orgs = pd.DataFrame(orgs)
    print(f'\nⓘ Organizations ({len(df_orgs)})\n')
    print(f"{df_orgs.drop(['id','url','licensing','cloud'], axis='columns').to_markdown(index=False, tablefmt=args.format)}")

    networks = dashboard.organizations.getOrganizationNetworks(org_id, total_pages='all')
    df_networks = pd.DataFrame(networks)
    print(f'\nⓘ Networks ({len(df_networks)})\n')
    print(f"{df_networks.drop(['id','organizationId','enrollmentString','notes','productTypes','timeZone','url'], axis='columns').to_markdown(index=False, tablefmt=args.format)}")

    devices = dashboard.networks.getNetworkDevices(networks[0]['id'])
    df_devices = pd.DataFrame(devices)
    print(f'\nⓘ Devices ({len(df_devices)})\n')
    print(df_devices.drop(['serial','networkId','mac','lanIp','tags','lat','lng','address','url','floorPlanId','switchProfileId'], axis='columns').to_markdown(index=False, tablefmt=args.format))

    print()


def main ():
    """
    Entrypoint for packaged script.
    """
    
    global args     # promote to global scope for use in other functions
    args = parse_cli_arguments()
    if args.verbose >= 3 : print(f'ⓘ Args: {args}')
    if args.timer :
        global start_time
        start_time = time.time()

    # Load Environment Variables
    global env
    env = { k : v for (k, v) in os.environ.items() if k.startswith('MERAKI_') }
    # if args.verbose >= 4 : print(f'ⓘ env: {env}')

    meraki_api_enabled()

    if args.timer :
        duration = time.time() - start_time
        print(f'\n 🕒 {duration} seconds\n', file=sys.stderr)


if __name__ == '__main__':
    """
    Entrypoint for local script.
    """
    main()

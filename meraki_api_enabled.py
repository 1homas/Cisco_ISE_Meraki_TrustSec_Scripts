#!/usr/bin/env python3
"""

Show ISE TrustSec data.

Examples:
    meraki_api_enabled.py 
    meraki_api_enabled.py --timer
    meraki_api_enabled.py --format pretty

Requires setting the these environment variables using the `export` command:
    export MERAKI_DASHBOARD_API_KEY='abcdef1234567890abcdef1234567890abcdef12'
    export MERAKI_ORG_NAME=example_org
    export MERAKI_NET_NAME=example_net

You may add these export lines to a text file and load with `source`:
  source meraki.sh

"""
__author__ = "Thomas Howard"
__email__ = "thomas@cisco.com"
__license__ = "MIT - https://mit-license.org/"

import argparse
import meraki
import os
import pandas as pd
import sys
from tabulate import tabulate
import time


MERAKI_DASHBOARD_BASE_URI = 'https://api.meraki.com/api/v1'

def meraki_api_enabled (org_id:str=None,format:str='simple') :
    """
    Get and show the ISE TrustSec SGTs, SGACLs, and Matrix.
    """

    # 💡 MERAKI_DASHBOARD_API_KEY environment variable is used automatically!
    dashboard = meraki.DashboardAPI(output_log=False, print_console=False)
    org_id = dashboard.organizations.getOrganizations()[0]['id']

    orgs = dashboard.organizations.getOrganizations()
    df_orgs = pd.DataFrame(orgs)
    print(f"\nⓘ Organizations ({len(df_orgs)})\n")
    print(f"{df_orgs.drop(['id','url','licensing','cloud'], axis='columns').to_markdown(index=False, tablefmt=format)}")

    networks = dashboard.organizations.getOrganizationNetworks(org_id, total_pages='all')
    df_networks = pd.DataFrame(networks)
    print(f"\nⓘ Networks ({len(df_networks)})\n")
    print(f"{df_networks.drop(['id','organizationId','enrollmentString','notes','productTypes','timeZone','url'], axis='columns').to_markdown(index=False, tablefmt=format)}")

    devices = dashboard.networks.getNetworkDevices(networks[0]['id'])
    df_devices = pd.DataFrame(devices)
    print(f"\nⓘ Devices ({len(df_devices)})\n")
    print(df_devices.drop(['serial','networkId','mac','lanIp','tags','lat','lng','address','url','floorPlanId','switchProfileId'], axis='columns').to_markdown(index=False, tablefmt=format))


if __name__ == '__main__':
    """
    Entrypoint for local script.
    """
    argp = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter) # keep my format
    argp.add_argument('-f', '--format', choices=['plain','simple','grid','simple_grid','pretty','presto'], default='simple_grid', help='table format' )
    argp.add_argument('-t', '--timer', action='store_true', default=False, help='show response timer' )
    argp.add_argument('-v', '--verbose', action='store_true', default=False, help='Verbosity; multiple allowed')
    args = argp.parse_args()

    if args.timer: start_time = time.time()

    env = {k:v for (k,v) in os.environ.items() if k.startswith('MERAKI_')} # Load environment variables
    if env.get('MERAKI_DASHBOARD_API_KEY', None) == None:
        sys.exit("Missing MERAKI_DASHBOARD_API_KEY environment variable!")
    meraki_api_enabled(format=args.format)

    if args.timer : print(f"\n 🕒 {time.time() - start_time} seconds\n", file=sys.stderr)

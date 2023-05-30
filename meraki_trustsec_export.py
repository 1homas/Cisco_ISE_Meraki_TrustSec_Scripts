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
    meraki_trustsec_export.py 
    meraki_trustsec_export.py -f pretty
    meraki_trustsec_export.py -vt
    meraki_trustsec_export.py -vvv

Requires setting the these environment variables using the `export` command:
    export MERAKI_DASHBOARD_API_KEY='abcdef1234567890abcdef1234567890abcdef12'
    export MERAKI_ORG_NAME=example_org
    export MERAKI_NET_NAME=example_net

You may add these export lines to a text file and load with `source`:
  source meraki.sh

"""

MERAKI_DASHBOARD_BASE_URI = 'https://api.meraki.com/api/v1'
DATA_DIR = './'
MERAKI_BASE_FILENAME = 'meraki_trustsec'

# Colors for matrix cells in Excel
CISCO_BLUE    = '#049fd9'
STATUS_BLUE   = '#64bbe3'
STATUS_GREEN  = '#6cc04a'
STATUS_ORANGE = '#ff7300'
STATUS_YELLOW = '#ffcc00'
LITE_GRAY     = '#F2F2F2'
PALE_GRAY     = '#e8ebf1'
CELL_STATUS_RED    = '#CF2030'  # Status Red
CELL_COLOR_ALLOW   = STATUS_GREEN
CELL_COLOR_DENY    = '#EF7775'  # Status Red, 40% Lighter
CELL_COLOR_DEFAULT = LITE_GRAY  # default / empty
CELL_COLOR_CUSTOM  = STATUS_BLUE  # Cisco Blue

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



def meraki_trustsec_export () :
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

    ap_overview = dashboard.organizations.getOrganizationAdaptivePolicyOverview(org_id)


    networks = dashboard.organizations.getOrganizationNetworks(org_id, total_pages='all')
    df_networks = pd.DataFrame(networks)

    
    devices = dashboard.networks.getNetworkDevices(networks[0]['id'])
    df_devices = pd.DataFrame(devices)


    ap_settings = dashboard.organizations.getOrganizationAdaptivePolicySettings(org_id)
    df_settings = pd.DataFrame(ap_settings)
    # df_settings['rules'] = df_acls['rules'].apply(lambda acl: '\n'.join([f"{ace['policy']} {ace['protocol']} {ace['srcPort']} {ace['dstPort']}" for ace in acl]))


    # ['groupId', 'name', 'sgt', 'description', 'policyObjects', 'isDefaultGroup', 'requiredIpMappings', 'createdAt', 'updatedAt']]
    ap_groups = dashboard.organizations.getOrganizationAdaptivePolicyGroups(org_id)
    df_groups = pd.DataFrame(ap_groups)

    # ['name', 'description', 'rules', 'aclId', 'createdAt', 'updatedAt', 'ipVersion']
    ap_acls = dashboard.organizations.getOrganizationAdaptivePolicyAcls(org_id)
    df_acls = pd.DataFrame(ap_acls)
    
    # Create a 'Rules' column from existing 'rules' column converting SGACL rules to multi-line text
    # 'rules' contains a list of dicts: [{'policy':'', 'protocol':'', 'srcPort':'', 'dstPort'}:'', ...]
    df_acls['Rules'] = df_acls['rules'].apply(lambda acl: '\n'.join([f"{ace['policy']} {ace['protocol']} {ace['srcPort']} {ace['dstPort']}" for ace in acl]))

    # Re-order and drop columns
    # df_acls.rename(columns={ 'name':'Name', 'description':'Description', 'aclId':'SGACL_ID', 'ipVersion':'IP_Version', }, inplace=True)
    # df_acls = df_acls[['SGACL_ID','Name','Description', 'Rules', 'IP_Version']]
    df_acls = df_acls[['aclId','name','description', 'Rules', 'ipVersion']]


    # ['adaptivePolicyId', 'sourceGroup', 'destinationGroup', 'acls', 'lastEntryRule', 'createdAt', 'updatedAt']
    ap_policies = dashboard.organizations.getOrganizationAdaptivePolicyPolicies(org_id)
    df_policies = pd.DataFrame(ap_policies)

    # extract string from dict
    df_policies['src_name'] = df_policies['sourceGroup'].apply(lambda x: x['name'])
    df_policies['src_num']  = df_policies['sourceGroup'].apply(lambda x: x['sgt'])
    df_policies['dst_name'] = df_policies['destinationGroup'].apply(lambda x: x['name'])
    df_policies['dst_num']  = df_policies['destinationGroup'].apply(lambda x: x['sgt'])

    # convert SGACLs from list of dicts to list of names
    df_policies['acl_names'] = df_policies['acls'].apply(lambda sgacls: ','.join([ sgacl['name'] for sgacl in sgacls ]))

    # reorder and drop columns
    df_policies = df_policies[['adaptivePolicyId', 'src_name', 'src_num', 'dst_name', 'dst_num', 'acl_names', 'lastEntryRule']]
    df_policies.rename(columns={ 'src_name':'SrcSGT', 'src_num':'Src#', 'dst_name':'DstSGT', 'dst_num':'Dst#', 'acl_names':'SGACLs' }, inplace=True)

    #--------------------------------------------------------------------------
    # Create the TrustSec Matrix from Meraki data
    #--------------------------------------------------------------------------

    df_matrix = df_groups[['name','sgt','description']].sort_values('sgt')
    df_matrix.rename(columns={'name':'SGT','sgt':'Value','description':'Description'}, inplace=True)
    for column in df_matrix['SGT'] :
        df_matrix[column] = ""    # create empty matrix with default
    
    # iterate over policies to fill in the matrix
    df_matrix.set_index('SGT', inplace=True)
    for row in df_policies.to_dict('records') :
        if len(row['SGACLs']) > 0 :
            # use the SGACL(s)
            df_matrix.at[row['SrcSGT'], row['DstSGT']] = row['SGACLs']
        else :
            # use the default rule
            df_matrix.at[row['SrcSGT'], row['DstSGT']] = row['lastEntryRule']
    df_matrix.reset_index(names=['SGT'], inplace=True)   # keep the name column

    #--------------------------------------------------------------------------
    # Show on Terminal
    #--------------------------------------------------------------------------

    # print(f"{df_orgs.drop(['url'], axis='columns').to_markdown(index=False, tablefmt=args.format)}")

    print(f'\nAdaptive Policy Overview\n')
    print(yaml.dump(ap_overview, indent=2))

    print(f'\nNetworks({len(df_networks)})\n')
    print(f"{df_networks.drop(['id','organizationId','enrollmentString','notes','productTypes','timeZone','url'], axis='columns').to_markdown(index=False, tablefmt=args.format)}")

    print(f'\nDevices ({len(df_devices)})\n')
    print(df_devices.drop(['serial','networkId','lat','lng','address','url','floorPlanId','switchProfileId'], axis='columns').to_markdown(index=False, tablefmt=args.format))

    print(f'\nSettings ({len(df_settings)})\n')
    print(df_settings.to_markdown(index=False, tablefmt=args.format))

    print(f'\nAdaptive Policy Groups ({len(df_groups)})\n')
    print(df_groups.drop(['groupId','description','requiredIpMappings','createdAt','updatedAt'], axis='columns').to_markdown(index=False, tablefmt=args.format))

    print(f'\nAdaptive Policy ACLs({len(df_acls)})\n')
    print(df_acls.drop(['aclId'], axis='columns').to_markdown(index=False, tablefmt=args.format))

    print(f'\nAdaptive Policy Policies ({len(ap_policies)})\n')
    print(df_policies.drop(['adaptivePolicyId'], axis='columns').to_markdown(index=False, tablefmt=args.format))

    print(f'\nTrustSec Matrix ({len(df_matrix)} x {len(df_matrix)})\n')
    print(df_matrix.drop(['Description'], axis='columns').to_markdown(index=False, tablefmt=args.format))

    print() # extra line


    #--------------------------------------------------------------------------
    # Export dataframes to CSVs
    #--------------------------------------------------------------------------
    df_groups.to_csv(DATA_DIR+MERAKI_BASE_FILENAME+'_groups.csv', index=False)
    df_acls.to_csv(DATA_DIR+MERAKI_BASE_FILENAME+'_acls.csv', index=False)
    df_matrix.to_csv(DATA_DIR+MERAKI_BASE_FILENAME+'_matrix.csv', index=False)


    #--------------------------------------------------------------------------
    # Export dataframes to an Excel Workbook
    #--------------------------------------------------------------------------
    with pd.ExcelWriter(DATA_DIR+MERAKI_BASE_FILENAME+'_matrix.xlsx', engine='xlsxwriter') as writer:

        df_matrix.to_excel(writer, sheet_name='Matrix', index=False)
        df_acls.to_excel(writer, sheet_name='SGACLs', index=False)
        df_policies.to_excel(writer, sheet_name='Policies', index=False)
        df_groups.to_excel(writer, sheet_name='SGTs', index=False)
        df_settings.to_excel(writer, sheet_name='Enabled', index=False)
        df_networks \
            .drop(['enrollmentString','notes','productTypes','timeZone','url'], axis='columns') \
            .to_excel(writer, sheet_name='Networks', index=False)
        df_devices \
            .drop(['lat','lng','address','url','floorPlanId','switchProfileId'], axis='columns') \
            .to_excel(writer, sheet_name='Devices', index=False)

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
        sgt_header               = workbook.add_format({'rotation': 45, 'align':'left', 'border':1, 'valign':'bottom'})
        header                   = workbook.add_format({'align':'left', 'valign':'bottom'})
        reserved_sgts            = workbook.add_format({'bg_color': LITE_GRAY})

        worksheet = writer.sheets['Matrix']

        # Column widths
        for i,column in enumerate(df_matrix.columns, start=0) :
            if column == 'SGT' : 
                worksheet.set_column(i, i, max(df_matrix['SGT'].apply(lambda x: len(x))), header)
            elif column == 'Value' : 
                worksheet.set_column(i, i, 6, workbook.add_format({'align':'right', 'valign':'bottom'}))
            elif column == 'Description' : 
                worksheet.set_column(i, i, min(20, max(df_matrix['Description'].apply(lambda x: len(x)))), header)
            else : 
                # worksheet.set_column(i, i, 12, sgt_header)
                worksheet.write(0, i, column, sgt_header)

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

    meraki_trustsec_export()

    if args.timer :
        duration = time.time() - start_time
        print(f'\n 🕒 {duration} seconds\n', file=sys.stderr)


if __name__ == '__main__':
    """
    Entrypoint for local script.
    """
    main()

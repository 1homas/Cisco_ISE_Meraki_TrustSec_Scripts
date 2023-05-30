# Cisco_ISE_Meraki_TrustSec_Scripts

Scripts and CSV templates for converting Cisco Identity Services Engine (ISE) TrustSec components and matrix to Cisco Meraki Adaptive Policy.

These scripts assume the use of Cisco ISE and Meraki REST APIs using Python.

## Quick Start

1.  Clone this repository:  

    ```sh
    git clone https://github.com/1homas/Cisco_ISE_Meraki_TrustSec_Scripts.git
    cd Cisco_ISE_Meraki_TrustSec_Scripts
    ```

2.  Create your Python environment:  

    ```sh
    python -m ensurepip --upgrade
    pip3   install --upgrade pipenv     # use pipenv for a virtual development environment
    pipenv install --python 3.11        # use Python 3.9 or later
    pipenv install -r requirements.txt  # install required Python packages (`pip freeze > requirements.txt`)
    pipenv shell
    ```

3.  Export your ISE credentials into your terminal environment

    ```sh
    export ISE_HOSTNAME=ise.securitydemo.net    # ISE PAN for configuration
    export ISE_USERNAME=admin
    export ISE_PASSWORD=ISEisC00L
    export ISE_VERIFY=False
    export ISE_DEBUG=False

    export MERAKI_KEY='abcdef1234567890abcdef1234567890abcdef12'
    export MERAKI_ORG_NAME=example.org
    export MERAKI_NET_NAME=Lab
    ```

    > 💡 Add one or more spaces before the `export` commands to prevent these commands with your secrets from being saved to your shell history

    You may also edit and source these variables from a file in your `~/.secrets` directory :

    ```sh
    source ~/.secrets/ise.sh
    source ~/.secrets/meraki.sh
    ```

4.  Verify ISE and Meraki API connectivity:

    ```sh
    ise_api_enabled.py
    meraki_api_enabled.py
    ```

5.  Run an script:  

    ```sh
    ise_version.py
    ise_trustsec_export.py
    meraki_trustsec_export.py
    ```

## Examples

### ise_api_enabled.py

Enable the ISE ERS and OpenAPIs.

`ise_api_enabled.py` :

```sh
✅ ISE Open APIs Enabled
✅ ISE ERS APIs Enabled
```

### ise_version.py

Returns the ISE version

Example output:
```sh
> ise_version.py

build: '383'
maintenance: '0'
major: '3'
minor: '3'
patch: '0'
version: 3.3.0.383
```

### ise_trustsec_export.py

Exports the ISE TrustSec configurations using ISE REST APIs to your terminal as tables and to local files in the directory prefixed with `ise_trustsec` by default:

- `ise_trustsec_matrix.xlsx` : a Microsoft Excel workbook with tabs for the matrix, SGACLs, and SGTs.
- `ise_trustsec_matrix.csv` : a CSV export of the TrustSec matrix, compatible with the ISE CSV import/export.
- `ise_trustsec_sgacls.csv` : a CSV export of the SGACLs. ISE does not support CSV import/export of the SGACLs however it is very nice to have a text dump of the SGACLs!
- `ise_trustsec_sgts.csv` : a CSV export of the TrustSec SGTs, compatible with the ISE CSV import/export.

You may change the default `ise_trustsec` prefix using the `-f/--filename {prefix}` option.

```sh
> ise_trustsec_export.py

ⓘ SGTs:
┌──────────────────┬─────────────────────────────────┬─────────┬────────────────┬───────────────────┐
│ name             │ description                     │   value │   generationId │ propogateToApic   │
├──────────────────┼─────────────────────────────────┼─────────┼────────────────┼───────────────────┤
│ TrustSec_Devices │ TrustSec Devices Security Group │       2 │             82 │ False             │
├──────────────────┼─────────────────────────────────┼─────────┼────────────────┼───────────────────┤
│ Unknown          │ Unknown Security Group          │       0 │             82 │ False             │
├──────────────────┼─────────────────────────────────┼─────────┼────────────────┼───────────────────┤
│ ANY              │ ANY                             │   65535 │              0 │ False             │
└──────────────────┴─────────────────────────────────┴─────────┴────────────────┴───────────────────┘

ⓘ SGACLs:
┌───────────────┬────────────────────────┬────────────────┬───────────────┐
│ name          │ description            │   generationId │ aclcontent    │
├───────────────┼────────────────────────┼────────────────┼───────────────┤
│ Deny IP       │ Deny IP SGACL          │              0 │ deny ip       │
├───────────────┼────────────────────────┼────────────────┼───────────────┤
│ Deny_IP_Log   │ Deny IP with logging   │              0 │ deny ip log   │
├───────────────┼────────────────────────┼────────────────┼───────────────┤
│ Permit IP     │ Permit IP SGACL        │              0 │ permit ip     │
├───────────────┼────────────────────────┼────────────────┼───────────────┤
│ Permit_IP_Log │ Permit IP with logging │              0 │ permit ip log │
└───────────────┴────────────────────────┴────────────────┴───────────────┘

ⓘ Policies:
┌─────────┬─────────────────────┬──────────┬──────────┬──────────┬──────────┬───────────────┐
│ Name    │ Description         │ Status   │ SrcSGT   │ DstSGT   │ SGACLs   │ DefaultRule   │
├─────────┼─────────────────────┼──────────┼──────────┼──────────┼──────────┼───────────────┤
│ ANY-ANY │ Default egress rule │ ENABLED  │ ANY      │ ANY      │ Deny IP  │ DENY_IP       │
└─────────┴─────────────────────┴──────────┴──────────┴──────────┴──────────┴───────────────┘

ⓘ Matrix:
┌──────────────────┬─────────┬─────────────────────────────────┬────────────────────┬───────────┐
│ SGT              │   Value │ Description                     │ TrustSec_Devices   │ Unknown   │
├──────────────────┼─────────┼─────────────────────────────────┼────────────────────┼───────────┤
│ TrustSec_Devices │       2 │ TrustSec Devices Security Group │                    │           │
├──────────────────┼─────────┼─────────────────────────────────┼────────────────────┼───────────┤
│ Unknown          │       0 │ Unknown Security Group          │                    │           │
└──────────────────┴─────────┴─────────────────────────────────┴────────────────────┴───────────┘
```

### ise_trustsec_clear.py

Deletes *all* SGTs, SGACLs, and Egress Matrix Cells from the ISE deployment.
You will see errors when it tries to delete reserved SGTs (`Unknown`, `TrustSec_Devices`) and SGACLs (`Deny IP`, `Deny_IP_Log`,`Permit IP`, `Permit_IP_Log`).

```sh
> ise_trustsec_clear.py
⌫ 204 da9ad00d-0b9f-42b9-bbac-80979a04edf8
⌫ 204 7b311821-b0f6-4c61-93af-94a47b6f688d
⌫ 204 aba5dbe0-eee2-4aa4-b539-b02684721b04
⌫ 204 4fa15703-0c02-428c-8a2d-8f5d0020be6e
⌫ 204 98323647-073f-4e3f-bb89-2f8d0fdf1c20
⌫ 204 3ea6d69c-c023-45bd-9fe7-3d2034b7663f
⌫ 204 c9f61c26-7313-407d-ae16-539a7c44854d
⌫ 204 f6448013-2682-4e7b-b42e-0598d5ff6d06
⌫ 204 6bcef4ef-589c-4fa0-9f36-494aa0d996f7
⌫ 204 8bbeebbc-6a12-40af-b49a-77aa8b93c434
⌫ 204 2e2183c7-a1ed-4395-8016-84757347044f
⌫ 204 35b586a2-bf38-4af4-bc3b-d753e789e5b3
⌫ 204 45fcd70a-3139-4775-8e93-4f4abd7af958
⌫ 204 a5fe8a07-2c7e-478e-a69a-eb36b14c6ff9
❌ 500 Security group TrustSec_Devices is currently in use. References to this security group must be removed before it can be deleted.
❌ 400 Deletion of security group Unknown is forbidden and has been blocked!
❌ 500 Deletion of security group ACL Deny IP is forbidden and has been blocked (read only object).
❌ 500 Deletion of security group ACL Deny_IP_Log is forbidden and has been blocked (read only object).
❌ 500 Deletion of security group ACL Permit IP is forbidden and has been blocked (read only object).
❌ 500 Deletion of security group ACL Permit_IP_Log is forbidden and has been blocked (read only object).
❌ 400 can not delete default egress policy matrix rule .
```

### excel_trustsec_matrix_to_ise.py

Load a TrustSec matrix from an Excel workbook into ISE using REST APIs. The default Excel workbook name is `ise_trustsec_matrix.xlsx` which is the default from `ise_trustsec_export.py`. The default ISE TrustSec matrix is provided in `ise_trustsec_matrix_default.xlsx`.

Load the default ISE TrustSec matrix from `ise_trustsec_matrix_default.xlsx`:

```sh
> excel_trustsec_matrix_to_ise.py ise_trustsec_matrix_default.xlsx
⌫ 204 0eb228da-7a4b-414c-a738-9d5df68ecb66
⌫ 204 e12aa794-f212-42b6-a1b6-dea31dd299aa
⌫ 204 3b765a1b-32ec-457a-8a10-89e8c36fb738
⌫ 204 65a78800-6172-4113-8474-7e89a7785f2f
⌫ 204 422c32e3-a576-4a42-b82c-eabfb638f1b0
⌫ 204 53935ce8-55c7-4632-927b-bcd046e0e23c
⌫ 204 7abdd089-60bc-42c6-a434-742c7233e7f2
⌫ 204 2a2e2b43-814e-499b-b5d1-9d2266cb8eb3
⌫ 204 a8007749-2d95-4f77-9a4e-62e09628f413
⌫ 204 a5b0aa3a-3da4-4288-82b2-5ee6c1913afb
⌫ 204 a044f345-73bd-4f66-aab3-e3b5d9f151fd
⌫ 204 3d97773f-d1f7-42cc-aa0d-cc82ae34fb77
⌫ 204 f89b0543-16d0-405c-9c0e-0d043b148e4c
⌫ 204 337811b5-554b-485b-a87a-3c2770e9d7ab
❌ 500 Security group TrustSec_Devices is currently in use. References to this security group must be removed before it can be deleted.
❌ 400 Deletion of security group Unknown is forbidden and has been blocked!
❌ 500 Deletion of security group ACL Deny IP is forbidden and has been blocked (read only object).
❌ 500 Deletion of security group ACL Deny_IP_Log is forbidden and has been blocked (read only object).
❌ 500 Deletion of security group ACL Permit IP is forbidden and has been blocked (read only object).
❌ 500 Deletion of security group ACL Permit_IP_Log is forbidden and has been blocked (read only object).
❌ 400 can not delete default egress policy matrix rule .
🌟 201 Auditors
🌟 201 BYOD
🌟 201 Contractors
🌟 201 Developers
🌟 201 Development_Servers
🌟 201 Employees
🌟 201 Guests
🌟 201 Network_Services
🌟 201 PCI_Servers
🌟 201 Point_of_Sale_Systems
🌟 201 Production_Servers
🌟 201 Production_Users
🌟 201 Quarantined_Systems
🌟 201 Test_Servers

ⓘ SGTs:
┌───────────────────────┬─────────┬────────────────────────────────────┬────────────────┬───────────────────┐
│ name                  │   value │ description                        │   generationId │ propogateToApic   │
├───────────────────────┼─────────┼────────────────────────────────────┼────────────────┼───────────────────┤
│ Auditors              │       9 │ Auditor Security Group             │              0 │ False             │
├───────────────────────┼─────────┼────────────────────────────────────┼────────────────┼───────────────────┤
│ BYOD                  │      15 │ BYOD Security Group                │              0 │ False             │
├───────────────────────┼─────────┼────────────────────────────────────┼────────────────┼───────────────────┤
│ Contractors           │       5 │ Contractor Security Group          │              0 │ False             │
├───────────────────────┼─────────┼────────────────────────────────────┼────────────────┼───────────────────┤
│ Developers            │       8 │ Developer Security Group           │              0 │ False             │
├───────────────────────┼─────────┼────────────────────────────────────┼────────────────┼───────────────────┤
│ Development_Servers   │      12 │ Development Servers Security Group │              0 │ False             │
├───────────────────────┼─────────┼────────────────────────────────────┼────────────────┼───────────────────┤
│ Employees             │       4 │ Employee Security Group            │              0 │ False             │
├───────────────────────┼─────────┼────────────────────────────────────┼────────────────┼───────────────────┤
│ Guests                │       6 │ Guest Security Group               │              0 │ False             │
├───────────────────────┼─────────┼────────────────────────────────────┼────────────────┼───────────────────┤
│ Network_Services      │       3 │ Network Services Security Group    │              0 │ False             │
├───────────────────────┼─────────┼────────────────────────────────────┼────────────────┼───────────────────┤
│ PCI_Servers           │      14 │ PCI Servers Security Group         │              0 │ False             │
├───────────────────────┼─────────┼────────────────────────────────────┼────────────────┼───────────────────┤
│ Point_of_Sale_Systems │      10 │ Point of Sale Security Group       │              0 │ False             │
├───────────────────────┼─────────┼────────────────────────────────────┼────────────────┼───────────────────┤
│ Production_Servers    │      11 │ Production Servers Security Group  │              0 │ False             │
├───────────────────────┼─────────┼────────────────────────────────────┼────────────────┼───────────────────┤
│ Production_Users      │       7 │ Production User Security Group     │              0 │ False             │
├───────────────────────┼─────────┼────────────────────────────────────┼────────────────┼───────────────────┤
│ Quarantined_Systems   │     255 │ Quarantine Security Group          │              0 │ False             │
├───────────────────────┼─────────┼────────────────────────────────────┼────────────────┼───────────────────┤
│ Test_Servers          │      13 │ Test Servers Security Group        │              0 │ False             │
├───────────────────────┼─────────┼────────────────────────────────────┼────────────────┼───────────────────┤
│ TrustSec_Devices      │       2 │ TrustSec Devices Security Group    │             82 │ False             │
├───────────────────────┼─────────┼────────────────────────────────────┼────────────────┼───────────────────┤
│ Unknown               │       0 │ Unknown Security Group             │             82 │ False             │
└───────────────────────┴─────────┴────────────────────────────────────┴────────────────┴───────────────────┘

ⓘ SGACLs:
┌───────────────┬────────────────────────┬────────────────┬───────────────┐
│ name          │ description            │   generationId │ aclcontent    │
├───────────────┼────────────────────────┼────────────────┼───────────────┤
│ Deny IP       │ Deny IP SGACL          │              0 │ deny ip       │
├───────────────┼────────────────────────┼────────────────┼───────────────┤
│ Deny_IP_Log   │ Deny IP with logging   │              0 │ deny ip log   │
├───────────────┼────────────────────────┼────────────────┼───────────────┤
│ Permit IP     │ Permit IP SGACL        │              0 │ permit ip     │
├───────────────┼────────────────────────┼────────────────┼───────────────┤
│ Permit_IP_Log │ Permit IP with logging │              0 │ permit ip log │
└───────────────┴────────────────────────┴────────────────┴───────────────┘```
```

### meraki_api_enabled.py

```sh
> meraki_api_enabled.py

ⓘ Organizations (1)

┌────────┬───────────────────┬─────────────────┐
│ name   │ api               │ management      │
├────────┼───────────────────┼─────────────────┤
│ 1homas │ {'enabled': True} │ {'details': []} │
└────────┴───────────────────┴─────────────────┘

ⓘ Networks (3)

┌───────────────┬────────┬───────────────────────────┐
│ name          │ tags   │ isBoundToConfigTemplate   │
├───────────────┼────────┼───────────────────────────┤
│ Lab-MX68      │ []     │ False                     │
├───────────────┼────────┼───────────────────────────┤
│ hobo-employee │ []     │ False                     │
├───────────────┼────────┼───────────────────────────┤
│ hobo-thomas   │ []     │ False                     │
└───────────────┴────────┴───────────────────────────┘

ⓘ Devices (2)

┌─────────────┬────────────┬─────────────────┐
│ name        │ model      │ firmware        │
├─────────────┼────────────┼─────────────────┤
│ lab-mr46-1  │ MR46       │ wireless-29-5-1 │
├─────────────┼────────────┼─────────────────┤
│ lab-ms390-1 │ MS390-48UX │ cs-15-21-1      │
└─────────────┴────────────┴─────────────────┘
```


### meraki_trustsec_export.py

```sh
> meraki_trustsec_export.py

Adaptive Policy Overview

counts:
  allowPolicies: 1
  customAcls: 6
  customGroups: 6
  denyPolicies: 19
  groups: 8
  policies: 25
  policyObjects: 0
limits:
  aclsInAPolicy: 7
  groups: 100
  policyObjects: 8000
  rulesInAnAcl: 16


Networks(3)

┌───────────────┬────────┬───────────────────────────┐
│ name          │ tags   │ isBoundToConfigTemplate   │
├───────────────┼────────┼───────────────────────────┤
│ Lab-MX68      │ []     │ False                     │
├───────────────┼────────┼───────────────────────────┤
│ hobo-employee │ []     │ False                     │
├───────────────┼────────┼───────────────────────────┤
│ hobo-thomas   │ []     │ False                     │
└───────────────┴────────┴───────────────────────────┘

Devices (2)

┌───────────────────┬──────────────┬────────┬─────────────┬────────────┬─────────────────┐
│ mac               │ lanIp        │ tags   │ name        │ model      │ firmware        │
├───────────────────┼──────────────┼────────┼─────────────┼────────────┼─────────────────┤
│ 2c:3f:0b:56:e3:6c │ 10.80.60.150 │ []     │ lab-mr46-1  │ MR46       │ wireless-29-5-1 │
├───────────────────┼──────────────┼────────┼─────────────┼────────────┼─────────────────┤
│ 2c:3f:0b:16:75:80 │ 10.80.60.152 │ []     │ lab-ms390-1 │ MS390-48UX │ cs-15-21-1      │
└───────────────────┴──────────────┴────────┴─────────────┴────────────┴─────────────────┘

Settings (1)

┌──────────────────────┐
│ enabledNetworks      │
├──────────────────────┤
│ L_627126248111361804 │
└──────────────────────┘

Adaptive Policy Groups (8)

┌────────────────┬───────┬─────────────────┬──────────────────┐
│ name           │   sgt │ policyObjects   │ isDefaultGroup   │
├────────────────┼───────┼─────────────────┼──────────────────┤
│ Unknown        │     0 │ []              │ True             │
├────────────────┼───────┼─────────────────┼──────────────────┤
│ Infrastructure │     2 │ []              │ True             │
├────────────────┼───────┼─────────────────┼──────────────────┤
│ Employee       │     3 │ []              │ False            │
├────────────────┼───────┼─────────────────┼──────────────────┤
│ Guest          │     4 │ []              │ False            │
├────────────────┼───────┼─────────────────┼──────────────────┤
│ IOT            │     5 │ []              │ False            │
├────────────────┼───────┼─────────────────┼──────────────────┤
│ NetServices    │     6 │ []              │ False            │
├────────────────┼───────┼─────────────────┼──────────────────┤
│ VoIP           │     7 │ []              │ False            │
├────────────────┼───────┼─────────────────┼──────────────────┤
│ Camera         │     8 │ []              │ False            │
└────────────────┴───────┴─────────────────┴──────────────────┘

Adaptive Policy ACLs(6)

┌──────────────┬─────────────────┬────────────────────┬─────────────┐
│ name         │ description     │ Rules              │ ipVersion   │
├──────────────┼─────────────────┼────────────────────┼─────────────┤
│ BlockMalware │                 │ deny icmp any any  │ any         │
│              │                 │ deny tcp any 22    │             │
│              │                 │ deny udp any 53    │             │
│              │                 │ deny udp any 67    │             │
│              │                 │ deny udp any 68    │             │
│              │                 │ deny udp any 69    │             │
│              │                 │ deny tcp any 135   │             │
│              │                 │ deny tcp any 137   │             │
│              │                 │ deny tcp any 138   │             │
│              │                 │ deny tcp any 139   │             │
│              │                 │ deny tcp any 445   │             │
│              │                 │ deny tcp any 689   │             │
│              │                 │ deny udp any 1025  │             │
│              │                 │ deny udp any 1026  │             │
│              │                 │ deny tcp any 3389  │             │
│              │                 │ allow any any any  │             │
├──────────────┼─────────────────┼────────────────────┼─────────────┤
│ Deny IP      │ Deny IP SGACL   │ deny any any any   │ any         │
├──────────────┼─────────────────┼────────────────────┼─────────────┤
│ NetServices  │                 │ deny icmp any any  │ any         │
│              │                 │ deny tcp any 21    │             │
│              │                 │ allow tcp any 53   │             │
│              │                 │ allow udp any 53   │             │
│              │                 │ allow udp any 67   │             │
│              │                 │ allow udp any 68   │             │
│              │                 │ allow udp any 123  │             │
│              │                 │ allow udp any 514  │             │
│              │                 │ allow udp any 6514 │             │
│              │                 │ deny any any any   │             │
├──────────────┼─────────────────┼────────────────────┼─────────────┤
│ Permit IP    │ Permit IP SGACL │ allow any any any  │ any         │
├──────────────┼─────────────────┼────────────────────┼─────────────┤
│ Video        │                 │ allow tcp any 80   │ any         │
│              │                 │ allow tcp any 443  │             │
│              │                 │ allow tcp any 554  │             │
│              │                 │ allow udp any 554  │             │
├──────────────┼─────────────────┼────────────────────┼─────────────┤
│ VOIP         │                 │ allow tcp any 2000 │ any         │
│              │                 │ allow udp any 2000 │             │
│              │                 │ allow tcp any 5060 │             │
│              │                 │ allow udp any 5060 │             │
│              │                 │ allow tcp any 5061 │             │
│              │                 │ allow udp any 5061 │             │
└──────────────┴─────────────────┴────────────────────┴─────────────┘

Adaptive Policy Policies (25)

┌──────────┬────────┬────────────────┬────────┬──────────────┬─────────────────┐
│ SrcSGT   │   Src# │ DstSGT         │   Dst# │ SGACLs       │ lastEntryRule   │
├──────────┼────────┼────────────────┼────────┼──────────────┼─────────────────┤
│ Camera   │      8 │ Infrastructure │      2 │              │ deny            │
├──────────┼────────┼────────────────┼────────┼──────────────┼─────────────────┤
│ Camera   │      8 │ Unknown        │      0 │              │ deny            │
├──────────┼────────┼────────────────┼────────┼──────────────┼─────────────────┤
│ Camera   │      8 │ VoIP           │      7 │              │ deny            │
├──────────┼────────┼────────────────┼────────┼──────────────┼─────────────────┤
│ Camera   │      8 │ NetServices    │      6 │ NetServices  │ default         │
├──────────┼────────┼────────────────┼────────┼──────────────┼─────────────────┤
│ Camera   │      8 │ Guest          │      4 │              │ deny            │
├──────────┼────────┼────────────────┼────────┼──────────────┼─────────────────┤
│ Camera   │      8 │ IOT            │      5 │              │ deny            │
├──────────┼────────┼────────────────┼────────┼──────────────┼─────────────────┤
│ Camera   │      8 │ Camera         │      8 │ Video        │ default         │
├──────────┼────────┼────────────────┼────────┼──────────────┼─────────────────┤
│ Camera   │      8 │ Employee       │      3 │              │ deny            │
├──────────┼────────┼────────────────┼────────┼──────────────┼─────────────────┤
│ Employee │      3 │ Employee       │      3 │ BlockMalware │ default         │
├──────────┼────────┼────────────────┼────────┼──────────────┼─────────────────┤
│ Employee │      3 │ NetServices    │      6 │ NetServices  │ default         │
├──────────┼────────┼────────────────┼────────┼──────────────┼─────────────────┤
│ Employee │      3 │ Infrastructure │      2 │              │ deny            │
├──────────┼────────┼────────────────┼────────┼──────────────┼─────────────────┤
│ Employee │      3 │ Unknown        │      0 │              │ deny            │
├──────────┼────────┼────────────────┼────────┼──────────────┼─────────────────┤
│ Employee │      3 │ VoIP           │      7 │              │ deny            │
├──────────┼────────┼────────────────┼────────┼──────────────┼─────────────────┤
│ Employee │      3 │ Guest          │      4 │              │ deny            │
├──────────┼────────┼────────────────┼────────┼──────────────┼─────────────────┤
│ Employee │      3 │ IOT            │      5 │              │ deny            │
├──────────┼────────┼────────────────┼────────┼──────────────┼─────────────────┤
│ Employee │      3 │ Camera         │      8 │              │ deny            │
├──────────┼────────┼────────────────┼────────┼──────────────┼─────────────────┤
│ Guest    │      4 │ Guest          │      4 │              │ deny            │
├──────────┼────────┼────────────────┼────────┼──────────────┼─────────────────┤
│ Guest    │      4 │ NetServices    │      6 │ NetServices  │ default         │
├──────────┼────────┼────────────────┼────────┼──────────────┼─────────────────┤
│ Guest    │      4 │ Infrastructure │      2 │              │ deny            │
├──────────┼────────┼────────────────┼────────┼──────────────┼─────────────────┤
│ Guest    │      4 │ Unknown        │      0 │              │ deny            │
├──────────┼────────┼────────────────┼────────┼──────────────┼─────────────────┤
│ Guest    │      4 │ VoIP           │      7 │              │ deny            │
├──────────┼────────┼────────────────┼────────┼──────────────┼─────────────────┤
│ Guest    │      4 │ Employee       │      3 │              │ deny            │
├──────────┼────────┼────────────────┼────────┼──────────────┼─────────────────┤
│ Guest    │      4 │ IOT            │      5 │              │ deny            │
├──────────┼────────┼────────────────┼────────┼──────────────┼─────────────────┤
│ Guest    │      4 │ Camera         │      8 │              │ deny            │
├──────────┼────────┼────────────────┼────────┼──────────────┼─────────────────┤
│ IOT      │      5 │ IOT            │      5 │              │ allow           │
└──────────┴────────┴────────────────┴────────┴──────────────┴─────────────────┘

TrustSec Matrix (8 x 8)

┌────────────────┬─────────┬───────────┬──────────────────┬──────────────┬─────────┬───────┬───────────────┬────────┬──────────┐
│ SGT            │   Value │ Unknown   │ Infrastructure   │ Employee     │ Guest   │ IOT   │ NetServices   │ VoIP   │ Camera   │
├────────────────┼─────────┼───────────┼──────────────────┼──────────────┼─────────┼───────┼───────────────┼────────┼──────────┤
│ Unknown        │       0 │           │                  │              │         │       │               │        │          │
├────────────────┼─────────┼───────────┼──────────────────┼──────────────┼─────────┼───────┼───────────────┼────────┼──────────┤
│ Infrastructure │       2 │           │                  │              │         │       │               │        │          │
├────────────────┼─────────┼───────────┼──────────────────┼──────────────┼─────────┼───────┼───────────────┼────────┼──────────┤
│ Employee       │       3 │ deny      │ deny             │ BlockMalware │ deny    │ deny  │ NetServices   │ deny   │ deny     │
├────────────────┼─────────┼───────────┼──────────────────┼──────────────┼─────────┼───────┼───────────────┼────────┼──────────┤
│ Guest          │       4 │ deny      │ deny             │ deny         │ deny    │ deny  │ NetServices   │ deny   │ deny     │
├────────────────┼─────────┼───────────┼──────────────────┼──────────────┼─────────┼───────┼───────────────┼────────┼──────────┤
│ IOT            │       5 │           │                  │              │         │ allow │               │        │          │
├────────────────┼─────────┼───────────┼──────────────────┼──────────────┼─────────┼───────┼───────────────┼────────┼──────────┤
│ NetServices    │       6 │           │                  │              │         │       │               │        │          │
├────────────────┼─────────┼───────────┼──────────────────┼──────────────┼─────────┼───────┼───────────────┼────────┼──────────┤
│ VoIP           │       7 │           │                  │              │         │       │               │        │          │
├────────────────┼─────────┼───────────┼──────────────────┼──────────────┼─────────┼───────┼───────────────┼────────┼──────────┤
│ Camera         │       8 │ deny      │ deny             │ deny         │ deny    │ deny  │ NetServices   │ deny   │ Video    │
└────────────────┴─────────┴───────────┴──────────────────┴──────────────┴─────────┴───────┴───────────────┴────────┴──────────┘

```


## Resources

- [Cisco Meraki Dashboard API](https://developer.cisco.com/meraki/api-v1/)
- [Cisco Identity Services Engine (ISE) REST APIs](https://cs.co/ise-api)

## License

This repository is licensed under the [MIT License](https://choosealicense.com/licenses/mit/).

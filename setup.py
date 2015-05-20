#!/usr/bin/env python

from distutils.core import setup

setup(name='netapp_ontap_api',
        version='0.1',
        description='API wrapper for NetApp OnTAP API that understands '
            'between cluster mode and non-cluster mode'
        author='Jason Y. Lee',
        author_email='jylee@cs.ucr.edu',
        url='https://github.com/allyunion/netapp_ontap_api',
        packages=['netapp_ontap_api'],
    )

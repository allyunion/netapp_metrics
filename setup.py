#!/usr/bin/env python

from distutils.core import setup

setup(
        name='netapp_ontap_api',
        version='0.1',
        description='NetApp OnTAP API wrapper',
        long_description='API wrapper for NetApp OnTAP API that understands '
            'between cluster mode (C-mode) and non-cluster (7-mode) mode'
        url='https://github.com/allyunion/netapp_ontap_api',
        author='Jason Y. Lee',
        author_email='jylee@cs.ucr.edu',
        license='GPLv2',
        classifiers=[
            'Development Status :: 4 - Beta',
            'Intended Audience :: Developers',
            'Topic :: Software Development :: Libraries',
            'License :: OSI Approved :: GNU General Public License v2',
            'Programming Language :: Python :: 2',
            'Programming Language :: Python :: 2.7',
            'Programming Language :: Python :: 3',
            'Programming Language :: Python :: 3.2',
            'Programming Language :: Python :: 3.3',
            'Programming Language :: Python :: 3.4',
        ],
        keywords='netapp ontap api wrapper development',
        py_modules= ['netapp_ontap_api', 'netapp_ontap_api.NetAppMetrics'],
    )

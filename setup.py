#!/usr/bin/env python

from setuptools import setup, find_packages

setup(
        name='netapp_metrics',
        version='0.1.1',
        description='NetApp OnTAP API wrapper',
        long_description='API wrapper for NetApp OnTAP API that understands '
            'between cluster mode (C-mode) and non-cluster (7-mode) mode',
        url='https://github.com/allyunion/netapp_metrics',
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
        keywords='netapp ontap api metrics wrapper development',
        packages=find_packages(exclude=['contrib', 'docs', 'tests*']),
    )

#!/usr/bin/env python
# coding=utf-8
#
# (c) 2013, Jose Riguera Lopez, <jose.riguera@springer.com>
# (c) 2015, Jason Y. Lee <jylee@cs.ucr.edu>
#
# This plugin/program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as published
# by the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import sys
import time
import re
import unicodedata
import os
import getopt
import datetime

from collections import namedtuple as NamedTuple
from string import Template

NETAPP_LIB_IMPORTED = False
modulepaths = sys.path + ['/opt', '/usr/local', os.getcwd()]

try:
    import NaServer
    NETAPP_LIB_IMPORTED = True
except ImportError:
    for path in modulepaths:
        if not os.path.isdir(path):
            path = os.path.dirname(path)
        if os.path.isdir(path):
            for root, dirs, files in os.walk(path)
                if 'NaServer.py' in files:
                    if root not in sys.path:
                        sys.path.append(root)
                        try:
                            import NaServer
                            NETAPP_LIB_IMPORTED = True
                            break
                        except ImportError:
                            pass


if NETAPP_LIB_IMPORTED:
    NaServer  # workaround for pyflakes issue #13
else:
    raise ImportError('Unable to locate NetApp OnTAP API library in various '
        'paths and subdirectories: %s' % modulepaths)

class NetAppMetrics:

    def __init__(self, device, user, password, timeout=None, vserver='', max_records=999):
        self.vserver = None
        self.device = None
        self.clustered = False
        self.generation = '0'
        self.major = '0'
        self.minor = '0'
        self.perf_max_records = max_records
        self._connect(device, user, password, timeout)
        self._set_vserver(vserver)
        self._get_version()

    def _connect(self, device, user, password, timeout=None, method='HTTP'):
        self.server = NaServer.NaServer(device, 1, 15)
        self.server.set_transport_type(method)
        self.server.set_style('LOGIN')
        self.server.set_admin_user(user, password)
        if timeout is not None:
            self.server.set_timeout(timeout)
        self.device = device

    def _set_vserver(self, vserver=''):
        self.server.set_vserver(vserver)
        self.vserver = vserver

    def _get_version(self):
        cmd = NaServer.NaElement('system-get-version')
        res = self._invoke_elem(cmd)
        if res.results_errno():
            raise ValueError(
                "system-get-version error: %s" % res.results_reason())
        else:
            self.clustered = False
            clustered = res.child_get_string("is-clustered")
            if clustered == "true":
                self.clustered = True
            version_tuple = res.child_get("version-tuple")
            if version_tuple:
                version_tuple = version_tuple.child_get("system-version-tuple")
                self.generation = version_tuple.child_get_string("generation")
                self.major = version_tuple.child_get_string("major")
                self.minor = version_tuple.child_get_string("minor")
            else:
                version = res.child_get_string("version")
                if version:
                    version_tuple = re.search(r'(\d+)\.(\d+)\.(\d+)', version)
                    self.generation = version_tuple.group(1)
                    self.major = version_tuple.group(2)
                    self.minor = version_tuple.group(3)
            return (self.generation, self.major, self.minor)

    def get_objects(self):
        cmd = NaServer.NaElement('perf-object-list-info')
        res = self._invoke_elem(cmd)
        objects = {}
        if res.results_errno():
            raise ValueError(
                "perf-object-list-info error: %s" % res.results_reason())
        else:
            for inst in res.child_get("objects").children_get():
                inst_name = inst.child_get_string("name")
                inst_desc = inst.child_get_string("description")
                inst_priv = inst.child_get_string("privilege-level")
                objects[inst_name] = (inst_desc, inst_priv)
        return objects

    def get_info(self, kind):
        cmd = NaServer.NaElement("perf-object-counter-list-info")
        cmd.child_add_string("objectname", kind)
        res = self.server._invoke_elem(cmd)
        counters = {}
        if res.results_errno():
            reason = res.results_reason()
            msg = "perf-object-counter-list-info cannot collect '%s': %s"
            raise ValueError(msg % (kind, reason))
        for counter in res.child_get("counters").children_get():
            name = counter.child_get_string("name")
            desc = counter.child_get_string("desc")
            unit = ''
            if counter.child_get_string("unit"):
                unit = counter.child_get_string("unit")
            properties = ''
            if counter.child_get_string("properties"):
                properties = counter.child_get_string("properties")
            base = ''
            if counter.child_get_string("base-counter"):
                base = counter.child_get_string("base-counter")
            priv = counter.child_get_string("privilege-level")
            labels = []
            if counter.child_get("labels"):
                clabels = counter.child_get("labels")
                if clabels.child_get_string("label-info"):
                    tlabels = clabels.child_get_string("label-info")
                    labels = [l.strip() for l in tlabels.split(',')]
            counters[name] = (unit, properties, base, priv, desc, labels)
        return counters

    def _invoke(self, cmd):
        '''Expose underlying NetApp API for invoking'''
        return self.server.invoke(cmd)

    def _invoke_elem(self, cmd):
        '''Expose underlying NetApp API for element invoking'''
        if isinstance(cmd, NaServer.NaElement):
            return self.server.invoke_elem(cmd)
        raise TypeError('Provided cmd is not of type NaElement')

    def _decode_elements2dict(self, head, filter=None):
        '''This function is a function that can take the results from
           an invoke call from the NetApp API and break it down to a
           json-styled Python dict object.'''
        if filter is not None and (
                hasattr(
                    filter, "__getitem__") or hasattr(filter, "__iter__")):
            if hasattr(filter, "strip"):
                filter = [filter]
        elif filter is None:
            pass
        else:
            raise TypeError('filter (%s) is of an unknown type!' % filter)

        if head.has_children() == 1:
            if sum([item.has_children() for item in head.children_get()]) == 0:
                if filter is not None:
                    return {
                        head.element['name']: {
                            item.element['name']: item.element['content']
                            for item in head.children_get()
                            if item.element['name'] in filter
                        }
                    }
                else:
                    return {
                        head.element['name']: {
                            item.element['name']: item.element['content']
                            for item in head.children_get()
                        }
                    }
            elif sum(
                [
                    item.has_children()
                    for item in head.children_get()
                    ]) == len(head.children_get()):
                return [
                    self._decode_elements2dict(item, filter)
                    for item in head.children_get()
                ]
            else:
                ans = {}
                for item in head.children_get():
                    if item.has_children() == 1:
                        ans[item.element['name']] = \
                          self._decode_elements2dict(item, filter)
                    else:
                        ans[item.element['name']] = item.element['content']
                return ans
        else:
            return head.element

    def get_lun_info(self, filter=None):
        cmd = NaServer.NaElement('lun-list-info')
        if self.clustered:
            cmd = NaServer.NaElement('lun-get-iter')
            cmd.child_add_string("max-records", "999")
        res = self._invoke_elem(cmd)
        if res.results_errno():
            raise ValueError('lun-info error: %s' % res.results_reason())
        answers = self._decode_elements2dict(res, filter)
        if self.clustered:
            return [item['lun-info'] for item in answers['attributes-list']]
        return [item['lun-info'] for item in answers['luns']]

    def get_vol_space_info(self, filter=None):
        cmd = NaServer.NaElement('volume-get-iter')
        if self.clustered:
            cmd.child_add_string("max-records", "999")
        else:
            cmd = NaServer.NaElement('volume-list-info')

        res = self._invoke_elem(cmd)
        if res.results_errno():
            raise ValueError(
                'vol-space-info error: %s' % res.results_reason())

        answers = self._decode_elements2dict(res, filter)
        ret = []

        if self.clustered:
            for i in answers['attributes-list']:
                ans = {}
                for j in i:
                    if not hasattr(j, 'iteritems'):
                        j = j[0]
                    for key, item in j.iteritems():
                        ans[key] = item
                ret.append(ans)
            return ret
        else:
            return answers[0]

    def get_aggr_info(self, filter=None):
        cmd = NaServer.NaElement('aggr-get-iter')
        if self.clustered:
            cmd.child_add_string("max-records", "999")
        else:
            cmd = NaServer.NaElement('aggr-list-info')

        res = self._invoke_elem(cmd)

        if res.results_errno():
            raise ValueError('aggr-info error: %s' % res.results_reason())

        answers = self._decode_elements2dict(res, filter)

        if not self.clustered:
            return answers[0]

        return answers['attributes-list']

    def __sevenm_instances(self, kind, filter=''):
        instances_list = []
        cmd = NaServer.NaElement("perf-object-instance-list-info-iter-start")
        cmd.child_add_string("objectname", kind)
        res = self.server._invoke_elem(cmd)
        if res.results_errno():
            reason = res.results_reason()
            msg = (
                    "perf-object-instance-list-info-iter-start"
                    " cannot collect '%s': %s"
                  )
            raise ValueError(msg % (kind, reason))
        next_tag = res.child_get_string("tag")
        counter = self.perf_max_records
        while counter == self.perf_max_records:
            cmd = NaServer.NaElement(
                "perf-object-instance-list-info-iter-next"
            )
            cmd.child_add_string("tag", next_tag)
            cmd.child_add_string("maximum", self.perf_max_records)
            res = self.server._invoke_elem(cmd)
            if res.results_errno():
                reason = res.results_reason()
                msg = ("perf-object-instance-list-info-iter-next"
                       " cannot collect '%s': %s")
                raise ValueError(msg % (kind, reason))
            counter = res.child_get_string("records")
            instances = res.child_get("instances")
            if instances:
                for inst in instances.children_get():
                    name = inst.child_get_string("name")
                    instances_list.append(name)
        cmd = NaServer.NaElement("perf-object-instance-list-info-iter-end")
        cmd.child_add_string("tag", next_tag)
        res = self.server._invoke_elem(cmd)
        if res.results_errno():
            reason = res.results_reason()
            msg = (
                    "perf-object-instance-list-info-iter-end"
                    " cannot collect '%s': %s"
            )
            raise ValueError(msg % (kind, reason))

        # filter
        return instances_list

    def __clusterm_instances(self, kind, filter=''):
        counter = self.perf_max_records
        next_tag = ''
        instances_list = []
        while counter == self.perf_max_records:
            cmd = NaServer.NaElement("perf-object-instance-list-info-iter")
            cmd.child_add_string("objectname", kind)
            if filter:
                cmd.child_add_string("filter-data", filter)
            if next_tag:
                cmd.child_add_string("tag", next_tag)
            cmd.child_add_string("max-records", self.perf_max_records)
            res = self.server._invoke_elem(cmd)
            if res.results_errno():
                reason = res.results_reason()
                msg = (
                    "perf-object-instance-list-info-iter"
                    " cannot collect '%s': %s"
                )
                raise ValueError(msg % (kind, reason))
            next_tag = res.child_get_string("next-tag")
            counter = res.child_get_string("num-records")
            for inst in res.child_get("attributes-list").children_get():
                name = inst.child_get_string("uuid")
                instances_list.append(name)
        return instances_list

    def get_instances(self, kind, filter=''):
        if self.clustered:
            return self.__clusterm_instances(kind, filter)
        else:
            return self.__sevenm_instances(kind, filter)

    def __collect_instances(self, response):
        metrics = {}
        times = {}
        for instance in response.child_get("instances").children_get():
            instance_data = {}
            counters_list = instance.child_get("counters").children_get()
            for counter in counters_list:
                raw_metricname = counter.child_get_string("name")
                raw_metricname = unicodedata.normalize('NFKD', raw_metricname)
                metric = raw_metricname.encode('ascii', 'ignore')
                instance_data[metric] = counter.child_get_string("value")
            # get a instance name
            if instance.child_get_string("uuid"):
                name = instance.child_get_string("uuid")
            else:
                name = instance.child_get_string("name")
            name = unicodedata.normalize('NFKD', name)
            # Optimize please!!!!!
            name = name.encode('ascii', 'ignore')
            name = name.replace('.', '_').strip('_')
            name = name.replace('/', '.').strip('.')
            name = re.sub(r'[^a-zA-Z0-9._]', '_', name)
            # name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
            metrics[name] = instance_data
            # Keep track of how long has passed since we checked last
            times[name] = time.time()
        instance_time = None
        if response.child_get_string("timestamp"):
            instance_time = float(response.child_get_string("timestamp"))
        return metrics, times, instance_time

    def __sevenm_metrics(self, kind, instances, metrics):
        values = {}
        times = {}
        cmd = NaServer.NaElement("perf-object-get-instances-iter-start")
        cmd.child_add_string("objectname", kind)
        counters = NaServer.NaElement("counters")
        for metric in metrics:
            counters.child_add_string("counter", metric)
        cmd.child_add(counters)
        insts = NaServer.NaElement("instances")
        for inst in instances:
            insts.child_add_string("instance", inst)
        cmd.child_add(insts)
        res = self.server._invoke_elem(cmd)
        if res.results_errno():
            reason = res.results_reason()
            msg = (
                    "perf-object-get-instances-iter-start"
                    " cannot collect '%s': %s"
            )
            raise ValueError(msg % (kind, reason))
        next_tag = res.child_get_string("tag")
        instance_time = float(res.child_get_string("timestamp"))
        counter = self.perf_max_records
        while counter == self.perf_max_records:
            cmd = NaServer.NaElement("perf-object-get-instances-iter-next")
            cmd.child_add_string("tag", next_tag)
            cmd.child_add_string("maximum", self.perf_max_records)
            res = self.server._invoke_elem(cmd)
            if res.results_errno():
                reason = res.results_reason()
                msg = (
                        "perf-object-get-instances-iter-next"
                        " cannot collect '%s': %s"
                )
                raise ValueError(msg % (kind, reason))
            counter = res.child_get_string("records")
            partial_values, partial_times, partial_inst_t \
                = self.__collect_instances(res)
            # Mix them with the previous records of the same instance
            # WARNING, BUG with same instance and time!!!!!!!!!
            for instance, values in values.iteritems():
                if instance in partial_values:
                    values.update(partial_values[instance])
                    del partial_values[instance]
            values.update(partial_values)
            times.update(partial_times)
        cmd = NaServer.NaElement("perf-object-instance-list-info-iter-end")
        cmd.child_add_string("tag", next_tag)
        res = self.server._invoke_elem(cmd)
        if res.results_errno():
            reason = res.results_reason()
            msg = (
                    "perf-object-instance-list-info-iter-end"
                    " cannot collect '%s': %s"
            )
            raise ValueError(msg % (kind, reason))
        return values, times, instance_time

    def __clusterm_metrics(self, kind, instances, metrics):
        cmd = NaServer.NaElement("perf-object-get-instances")
        inst = NaServer.NaElement("instance-uuids")
        for instance in instances:
            inst.child_add_string("instance-uuid", instance)
        cmd.child_add(inst)
        cmd.child_add_string("objectname", kind)
        counters = NaServer.NaElement("counters")
        for metric in metrics:
            counters.child_add_string("counter", metric)
        cmd.child_add(counters)
        res = self.server._invoke_elem(cmd)
        if res.results_errno():
            reason = res.results_reason()
            msg = "perf-object-get-instances cannot collect '%s': %s"
            raise ValueError(msg % (kind, reason))
        return self.__collect_instances(res)

    def get_metrics(self, kind, instances, metrics=[]):
        if self.clustered:
            return self.__clusterm_metrics(kind, instances, metrics)
        else:
            return self.__sevenm_metrics(kind, instances, metrics)


# EOF

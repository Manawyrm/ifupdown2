# Copyright (C) 2017, 2018 Cumulus Networks, Inc. all rights reserved
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; version 2.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301, USA.
#
# https://www.gnu.org/licenses/gpl-2.0-standalone.html
#
# Author:
#       Julien Fortin, julien@cumulusnetworks.com
#
# sysfs -- contains all sysfs related operation
#

import os

try:
    from ifupdown2.lib.io import IO
    from ifupdown2.lib.base_objects import Cache
    from ifupdown2.nlmanager.nlpacket import Link
except ImportError:
    from lib.io import IO
    from lib.base_objects import Cache
    from nlmanager.nlpacket import Link


class Sysfs(IO, Cache):

    __bond_netlink_to_sysfs_attr_map = {
        Link.IFLA_BOND_MODE: "mode",
        Link.IFLA_BOND_MIIMON: "miimon",
        Link.IFLA_BOND_USE_CARRIER: "use_carrier",
        Link.IFLA_BOND_AD_LACP_RATE: "lacp_rate",
        Link.IFLA_BOND_XMIT_HASH_POLICY: "xmit_hash_policy",
        Link.IFLA_BOND_MIN_LINKS: "min_links",
        Link.IFLA_BOND_NUM_PEER_NOTIF: "num_grat_arp",
        Link.IFLA_BOND_AD_ACTOR_SYSTEM: "ad_actor_system",
        Link.IFLA_BOND_AD_ACTOR_SYS_PRIO: "ad_actor_sys_prio",
        Link.IFLA_BOND_AD_LACP_BYPASS: "lacp_bypass",
        Link.IFLA_BOND_UPDELAY: "updelay",
        Link.IFLA_BOND_DOWNDELAY: "downdelay",
    }

    def __init__(self):
        IO.__init__(self)
        Cache.__init__(self)

    #
    # MTU
    #

    def link_set_mtu(self, ifname, mtu_str, mtu_int):
        if self.cache.get_link_mtu(ifname) != mtu_int:
            if self.write_to_file('/sys/class/net/%s/mtu' % ifname, mtu_str):
                self.cache.override_link_mtu(ifname, mtu_int)

    def link_set_mtu_dry_run(self, ifname, mtu_str, mtu_int):
        # we can remove the cache check in DRYRUN mode
        self.write_to_file('/sys/class/net/%s/mtu' % ifname, mtu_str)

    #
    # ALIAS
    #

    def link_set_alias(self, ifname, alias):
        cached_alias = self.cache.get_link_alias(ifname)

        if cached_alias == alias:
            return

        if not alias:
            alias = "\n"

        if self.write_to_file("/sys/class/net/%s/ifalias" % ifname, alias):
            pass # self.cache.override_link_mtu(ifname, mtu_int)

    def link_set_alias_dry_run(self, ifname, alias):
        # we can remove the cache check in DRYRUN mode
        if not alias:
            alias = ""
        self.write_to_file("/sys/class/net/%s/ifalias" % ifname, alias)

    #
    # BOND
    #

    def bond_remove_slave(self, bond_name, slave_name):
        if self.cache.is_link_enslaved_to(slave_name, bond_name):
            if self.write_to_file("/sys/class/net/%s/bonding/slaves" % bond_name, "-%s" % slave_name):
                # success we can manually update our cache to make sure we stay up-to-date
                self.cache.override_unslave_link(master=bond_name, slave=slave_name)

    def bond_remove_slave_dry_run(self, bond_name, slave_name):
        self.write_to_file("/sys/class/net/%s/bonding/slaves" % bond_name, "-%s" % slave_name)

    ###

    def bond_create(self, bond_name):
        if self.cache.bond_exists(bond_name):
            return
        self.write_to_file("/sys/class/net/bonding_masters", "+%s" % bond_name)

    def bond_create_dry_run(self, bond_name):
        self.write_to_file("/sys/class/net/bonding_masters", "+%s" % bond_name)

    ###

    def bond_set_attrs_nl(self, bond_name, ifla_info_data):
        """
        bond_set_attrs_nl doesn't need a _dry_run handler because each
        entry in ifla_info_data was checked against the cache already.
        Here write_to_file already has a dry_run handler.
        :param bond_name:
        :param ifla_info_data:
        :return:
        """
        bond_attr_name = 'None'  # for log purpose (in case an exception raised)

        for nl_attr, value in ifla_info_data.items():
            try:
                bond_attr_name = self.__bond_netlink_to_sysfs_attr_map[nl_attr]
                file_path = "/sys/class/net/%s/bonding/%s" % (bond_name, bond_attr_name)
                if os.path.exists(file_path):
                    self.write_to_file(file_path, str(value))
            except Exception as e:
                self.logger.warning("%s: %s %s: %s" % (bond_name, bond_attr_name, value, str(e)))
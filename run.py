#!/usr/bin/env python3
import os
import time
import json
import subprocess

"""
Ceph on zfs: https://kernelpanik.net/running-ceph-on-zfs/
"""


containers = {
    "mon": "10.27.161.134",
    "osd-0": "10.27.161.123",
    "osd-1": "10.27.161.170",
    "osd-2": "10.27.161.252"}
netmask = "255.255.255.0"
gateway = "10.27.161.1"
nameservers = [gateway, "8.8.8.8"]

# attach_devs = {"osd-0": ["/dev/loop0"],
#                "osd-1": ["/dev/loop1"],
#                "osd-2": ["/dev/loop2"]}

key = "/home/koder/.ssh/id_rsa"
known_hosts = "/home/koder/.ssh/known_hosts"
image = "ubuntu_16_04"

attach_devs = {}

cloud_init = """#cloud-config
ssh_authorized_keys:
  - {}
"""

ssh_key = open(key + ".pub", "rb").read().decode('utf-8')

def run(cmd, input_data=None, nolog=False):
    if not nolog:
        print(cmd)

    proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stdin=subprocess.PIPE)
    if input_data is not None:
        input_data = input_data.encode("utf-8")
    out, _ = proc.communicate(input_data)
    assert proc.wait() == 0
    return out.decode("utf8")


def cleanup_cloud():
    run("lxc stop " + " ".join(containers))
    run("lxc delete " + " ".join(containers))


def create_cloud():
    for name in containers:
        run("lxc init {} {}".format(image, name))
        run("lxc config set {} security.privileged true".format(name))
        run("lxc config set {} user.user-data -".format(name),
            cloud_init.format(ssh_key))
        run("lxc start {}".format(name))

    has_ip = dict.fromkeys(containers, False)
    while True:
        for cfg in json.loads(run("lxc list --format json")):
            if cfg['name'] in has_ip:
                for addr_info in cfg['state']['network']['eth0']['addresses']:
                    if addr_info['family'] == 'inet' and addr_info.get('address'):
                        has_ip[cfg['name']] = True

        if all(has_ip.values()):
            break

        time.sleep(1)

    for name, ip in containers.items():
        run("lxc exec {} -- ifdown eth0".format(name))

        sed_cmd = 's/127.0.0.1 localhost/127.0.0.1 localhost {}/g'.format(name)
        run("lxc exec {} -- sed -i -e '{}' /etc/hosts".format(name, sed_cmd))

        sed_cmd = 's/auto eth0/#auto eth0/g'
        run("lxc exec {} -- sed -i -e '{}' /etc/network/interfaces.d/50-cloud-init.cfg".format(name, sed_cmd))

        sed_cmd = 's/iface eth0 inet dhcp/#iface eth0 inet dhcp/g'
        run("lxc exec {} -- sed -i -e '{}' /etc/network/interfaces.d/50-cloud-init.cfg".format(name, sed_cmd))

        run("lxc exec {} -- ifconfig eth0 {} netmask {}".format(name, ip, netmask))
        run("lxc exec {} -- ip route add default via {}".format(name, gateway))

        for nameserver in nameservers:
            run("lxc exec {} -- sed -i '$inameserver {}' /etc/resolv.conf".format(name, nameserver))

    for name in containers:
        run("lxc exec {} -- rm /var/lib/apt/lists/lock".format(name))
        run("lxc exec {} -- apt-get update".format(name))
        run("lxc exec {} -- apt-get -y install python2.7".format(name))
        run("lxc exec {} -- ln -s /usr/bin/python2.7 /usr/bin/python".format(name))
        run("lxc exec {} -- cp /home/ubuntu/.ssh/authorized_keys /root/.ssh/".format(name))

        for dev, letter in zip(attach_devs.get(name, []), "defghijklmno"):
            run("lxc config device add {} {} unix-block path={}".format(name, os.path.basename(dev), dev))
            run("lxc exec {} -- ln -s {} /dev/sd{}".format(name, dev, letter))

    for ip_name in (list(containers.keys()) + list(containers.values())):
        run('ssh-keygen -f "{}" -R {}'.format(known_hosts, ip_name))

    for name in containers:
        run('ssh-keyscan -H "{}" >>{}'.format(name, known_hosts))


cleanup_cloud()
create_cloud()

# ceph-lxc

Set of scripts and ansible config files to start ceph cluster in [lxd](https://www.ubuntu.com/cloud/lxd).

How-to use:
* Install and configure [LXD](https://www.stgraber.org/2016/03/11/lxd-2-0-blog-post-series-012/).
  LXD better works on ZFS filesystem, but ZFS have
  some limitations (no direct/async io for journals, max object name size - 256 bytes, etc).
  Atm only ZFS is supported by this scripts directly. XFS would requires some code changes.
* Download ubuntu 16.04 x64 LXD image
* Checkout [ceph-ansible](https://github.com/ceph/ceph-ansible). Edit 'ansible_files/ansible.cfg' to
  set 'roles_path' and 'action_plugins' accordingly to ceph-ansible folder.
* Update run.py with to set you required containers and network settings to 'containers' variable.
  ceph-ansible requires that all ceph cluster nodes be resolvable via names. I'm using static names
  resolution vis /etc/hosts. By default LXD doesn't preserve container ip across restart, so run.py
  start container, wait till if finish network configuration, stop dhclient and update network
  settings to hardcoded values. You can avoid this by settings ip for container to None in run.py
  In other case update network settings in run.py.
* Create containers with 'python run.py'. By default it will try to remove existing containers first.
* Update public_network variable in ansible_files/group_vars/all
* Update ansible_files/hosts accordingly to you cluster
* Run ansible-playbook -i hosts site.yml. In case of failure rerun it with -vvvv and inspect output

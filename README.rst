This is the RPM packaging for the 3rd-party `facetimehd kernel module for
MacBook Pros <https://github.com/patjak/bcwc_pcie/>`_.

Binary RPMs at https://ktdreyer.fedorapeople.org/macbook/

Using this repo
===============

To enable this Yum repository on your Fedora system, put the ``macbook.repo``
file into ``/etc/yum.repos.d``, like so::

    curl https://ktdreyer.fedorapeople.org/macbook/macbook.repo | sudo tee /etc/yum.repos.d/macbook.repo

Installing for your running kernel version
==========================================

To install the kmod packages for the specific kernel version you're running,
run this DNF command as root::

    dnf install kmod-wl-$(uname -r) kmod-facetimehd-$(uname -r)

What kernel versions are available?
===================================

I use a script ("``updates.py``") to build for the latest kernel in Fedora's
`updates-testing repository
<https://bodhi.fedoraproject.org/updates/?packages=kernel>`_.

To install the very latest kernel from Fedora's updates-testing repository, run
this command as root::

   dnf -y update --enablerepo=\*-testing

(... and if there is a newer kernel available, DNF will install it.)

Refreshing the cache
====================

I update this repository quite often, and sometimes DNF's local metadata cache
will become stale. To tell DNF to refresh its cache for this repo's data::

    dnf --disablerepo='*' --enablerepo=ktdreyer-macbook makecache --refresh

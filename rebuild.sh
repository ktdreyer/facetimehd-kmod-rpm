#!/bin/bash
set -ex

# Rebuild kmod packages for a new kernel.

# Set whatever kernel you want here:
KERNEL=4.11.11-300.fc26.x86_64

# From mock-rpmfusion-free package:
MOCKCFG=fedora-26-x86_64-rpmfusion_free

mkdir -p $KERNEL
cd $KERNEL

DNFDOWNLOAD="dnf download --disablerepo=rhpkg --disablerepo=ktdreyer --enablerepo=updates-testing"
[ -f kernel-${KERNEL}.rpm ] || $DNFDOWNLOAD kernel-${KERNEL}
[ -f kernel-core-${KERNEL}.rpm ] || $DNFDOWNLOAD kernel-core-${KERNEL}
[ -f kernel-devel-${KERNEL}.rpm ] || $DNFDOWNLOAD kernel-devel-${KERNEL}
[ -f kernel-modules-${KERNEL}.rpm ] || $DNFDOWNLOAD kernel-modules-${KERNEL}

mock -r $MOCKCFG init

mock -r $MOCKCFG install \
  kernel-core-${KERNEL}.rpm \
  kernel-devel-${KERNEL}.rpm \
  kernel-modules-${KERNEL}.rpm \
  kernel-${KERNEL}.rpm

pkgs=(facetimehd-kmod-0-1.20161214git0712f39.fc25.src.rpm)
pkgs+=(../wl-kmod/wl-kmod-6.30.223.271-13.fc27.src.rpm)
for pkg in ${pkgs[@]}; do
  mock -r $MOCKCFG --no-clean rebuild \
    ../${pkg} --define "kernels $KERNEL"
  cp /var/lib/mock/fedora-26-x86_64/result/*.x86_64.rpm .
done

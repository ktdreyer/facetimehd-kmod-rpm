#!/bin/bash
set -ex

# Rebuild kmod packages for a new kernel.

# Set whatever kernel you want here:
KERNEL=4.8.15-300.fc25.x86_64

# From mock-rpmfusion-free package:
MOCKCFG=fedora-25-x86_64-rpmfusion_free

mkdir -p $KERNEL
cd $KERNEL

YUMDOWNLOADER="yumdownloader --disablerepo=rhpkg --disablerepo=ktdreyer"
[ -f kernel-${KERNEL}.rpm ] || $YUMDOWNLOADER kernel
[ -f kernel-core-${KERNEL}.rpm ] || $YUMDOWNLOADER kernel-core
[ -f kernel-devel-${KERNEL}.rpm ] || $YUMDOWNLOADER kernel-devel
[ -f kernel-modules-${KERNEL}.rpm ] || $YUMDOWNLOADER kernel-modules

mock -r $MOCKCFG init

mock -r $MOCKCFG install \
  kernel-core-${KERNEL} \
  kernel-devel-${KERNEL} \
  kernel-modules-${KERNEL} \
  kernel-${KERNEL}

pkgs=(facetimehd-kmod-0-1.20161214git0712f39.fc25.src.rpm)
#pkgs+=(../wl-kmod/wl-kmod-6.30.223.271-7.fc23.src.rpm)
for pkg in ${pkgs[@]}; do
  mock -r $MOCKCFG --no-clean rebuild \
    ../${pkg} --define "kernels $KERNEL"
  cp /var/lib/mock/fedora-25-x86_64/result/*.x86_64.rpm .
done

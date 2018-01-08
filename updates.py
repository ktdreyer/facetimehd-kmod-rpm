#!/usr/bin/python

import errno
from glob import glob
import os
import re
import shutil
import subprocess
from bodhi.client.bindings import BodhiClient


# Discover the latest kernel versions in Bodhi and rebuild some kmod SRPMs
# against those versions.


def get_fedora_releases(client):
    """
    Return a set of active Fedora releases.

    For example: set(["25", "26"])

    :param client:  BodhiClient
    """
    # return set(['26'])  # XXX debugging!
    allreleases = client.get_releases().releases
    releases = set()
    for release in allreleases:
        # Even though we're operating on "dist-tags" here, note it's really a
        # Bodhi representation: "f"- something, not the more commonly-known RPM
        # disttag macro ("fc"-something).
        if release.state == 'current' and release.dist_tag.startswith('f'):
            releases.add(release.version)
    return releases


def get_latest_kernel(client, release):
    """
    Get the NVR of the latest testing or stable kernel for a Fedora release.
    """
    kwargs = {
        'packages': ['kernel'],
        'releases': ['f' + release],
        'content_type': 'rpm',
        'rows_per_page': 1,
    }
    result = client.query(status='testing', **kwargs)
    if not result.updates:
        result = client.query(status='stable', **kwargs)
    nvr = result.updates[0].builds[0].nvr
    return nvr


def kernel_filenames(nvr):
    """
    Return a set of .rpm filenames we will need in order to build a kmod pkg.
    """
    vr = nvr[7:]
    filenames = set([
        'kernel-%s.x86_64.rpm',
        'kernel-core-%s.x86_64.rpm',
        'kernel-devel-%s.x86_64.rpm',
        'kernel-modules-%s.x86_64.rpm',
    ])
    return set([f % vr for f in filenames])


def download_kernel(nvr):
    """
    Download the relevant kernel RPMs for this name-version-release

    Place the files into a version-release subdirectory.
    Skip downloading if a file already exists.
    """
    vr = nvr[7:]
    try:
        os.makedirs(vr)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise
    for filename in kernel_filenames(nvr):
        cmd = ('koji', 'download-build', '-a', 'x86_64', '--rpm', filename)
        if not os.path.exists(os.path.join(vr, filename)):
            print(' '.join(cmd))
            subprocess.check_call(cmd, cwd=vr)


def rpm_name(srpm, vr):
    """
    Return the .rpm file name,
    :param srpm: an SRPM file name
    :param   vr: a kernel version-release.
    """
    pkg = os.path.basename(srpm)
    (name, kmod, rest) = pkg.split('-', 2)
    m = re.search('fc\d\d$', vr)
    distarch = m.group(0)
    rest = re.sub('fc\d\d\.src\.rpm', distarch, rest)
    return 'kmod-{name}-{vr}.x86_64-{rest}.x86_64.rpm'.format(name=name,
                                                              vr=vr,
                                                              rest=rest)


def mock_build(release, nvr):
    """
    mockbuild all our packages for this Fedora release and kernel nvr.

    Skips SRPMs that are already built for this kernel nvr.

    :returns: list of all built packages (SRPMs). If we skipped all SRPMs,
              this list will be empty.
    """
    vr = nvr[7:]

    packages = ['facetimehd-kmod-0-1.20161214git0712f39.fc28.src.rpm']
    packages += ['../wl-kmod/wl-kmod-6.30.223.271-13.fc27.src.rpm']

    # Only rebuild packages that we have not yet built.
    to_build = []
    for srpm in packages:
        rpm = rpm_name(srpm, vr)
        filename = os.path.join(vr, rpm)
        if os.path.exists(filename):
            # print(' RPM %s already exists' % filename)
            continue
        to_build.append(srpm)

    if not to_build:
        return []

    # Initialize a clean mock chroot
    mockcfg = 'fedora-%s-x86_64-rpmfusion_free' % release
    # Before I ran "clean" here, I would get stale old --define kernels values.
    # Not sure why running "clean" here fixes it. It may have been an older
    # stray syntax error when I invoked mock a while back?
    # Commenting this out to see if the problem ever resurfaces.
    # cmd = ('mock', '-r', mockcfg, 'clean')
    # print(' '.join(cmd))
    # subprocess.check_call(cmd)
    cmd = ('mock', '-r', mockcfg, 'init')
    print(' '.join(cmd))
    subprocess.check_call(cmd)

    # Install our exact kernel pkgs
    cmd = ['mock', '-r', mockcfg, 'install'] + list(kernel_filenames(nvr))
    print(' '.join(cmd))
    subprocess.check_call(cmd, cwd=vr)

    # Rebuild our packages
    built = []
    for srpm in to_build:
        cmd = ('mock', '-r', mockcfg,
               '--no-clean',
               'rebuild', srpm,
               '--define=kernels %s.x86_64' % vr)
        print(' '.join(cmd))
        subprocess.check_call(cmd)
        rpm = rpm_name(srpm, vr)
        output = os.path.join('/var/lib/mock',
                              'fedora-%s-x86_64' % release,
                              'result', rpm)
        built.append(rpm)
        print('saving %s' % output)
        shutil.copy(output, vr)
    return built


def generate_repo(release, nvr):
    """
    Generate a Yum repo with the kmod RPMs from this kernel NVR directory.
    """
    vr = nvr[7:]
    repo = 'f' + release
    try:
        os.makedirs(repo)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise
    for filename in glob(vr + '/kmod-*.rpm'):
        basename = os.path.basename(filename)
        if not os.path.exists(os.path.join(repo, basename)):
            print('copying %s to %s repo' % (os.path.basename(filename), repo))
            shutil.copy(filename, repo)
    subprocess.check_call(['createrepo', '.'], cwd=repo)


def publish_repo(release):
    """
    Publish a repository to fedorapeople.org.
    """
    DESTINATION = 'fedorapeople.org:public_html/macbook/'
    repo = 'f' + release
    subprocess.check_call(['rsync', '-aP', repo, DESTINATION])


client = BodhiClient(debug=True)
releases = get_fedora_releases(client)
for release in releases:
    print('querying kernel pkg in Fedora %s...' % release)
    kernel = get_latest_kernel(client, release)
    print('f%s: %s' % (release, kernel))
    download_kernel(kernel)
    builds = mock_build(release, kernel)
    if not builds:
        print('skipped all builds for %s' % kernel)
        continue
    generate_repo(release, kernel)
    publish_repo(release)

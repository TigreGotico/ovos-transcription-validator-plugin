#!/usr/bin/env python3
import os

from setuptools import setup

URL = "https://github.com/TigreGotico/ovos-transcription-validator-plugin"
PLUGIN_CLAZZ = "TranscriptionValidatorPlugin"
PKG = "ovos_transcription_validator"

# semi-standardized from github url
AUTHOR, REPO = URL.split(".com/")[-1].split("/")
BASEDIR = os.path.abspath(os.path.dirname(__file__))
PKGDIR = os.path.join(BASEDIR, PKG)
UTTERANCE_ENTRY_POINT = f'{REPO.lower()}={PKG}:{PLUGIN_CLAZZ}'


def get_version():
    """ Find the version of the package"""
    version_file = f'{BASEDIR}/ovos_transcription_validator/version.py'
    major, minor, build, alpha = (None, None, None, None)
    with open(version_file) as f:
        for line in f:
            if 'VERSION_MAJOR' in line:
                major = line.split('=')[1].strip()
            elif 'VERSION_MINOR' in line:
                minor = line.split('=')[1].strip()
            elif 'VERSION_BUILD' in line:
                build = line.split('=')[1].strip()
            elif 'VERSION_ALPHA' in line:
                alpha = line.split('=')[1].strip()

            if ((major and minor and build and alpha) or
                    '# END_VERSION_BLOCK' in line):
                break
    version = f"{major}.{minor}.{build}"
    if alpha and int(alpha) > 0:
        version += f"a{alpha}"
    return version


def find_resource_files():
    resource_base_dirs = ("locale", "res",)  # Removed "ui"
    package_data = list()
    for res in resource_base_dirs:
        if os.path.isdir(os.path.join(PKGDIR, res)):
            for directory, _, files in os.walk(os.path.join(PKGDIR, res)):
                for f in files:
                    path = os.path.relpath(os.path.join(directory, f), PKGDIR)
                    package_data.append(path)
    return package_data


def required(requirements_file):
    """ Read requirements file and remove comments and empty lines. """
    with open(os.path.join(BASEDIR, requirements_file), 'r') as f:
        requirements = f.read().splitlines()
        if 'MYCROFT_LOOSE_REQUIREMENTS' in os.environ:
            print('USING LOOSE REQUIREMENTS!')
            requirements = [r.replace('==', '>=').replace('~=', '>=') for r in requirements]
        return [pkg for pkg in requirements
                if pkg.strip() and not pkg.startswith("#")]


with open(os.path.join(BASEDIR, "README.md"), "r") as f:
    long_description = f.read()

setup(
    name=REPO,
    description='OpenVoiceOS Transcription Validator Plugin',
    long_description=long_description,
    long_description_content_type="text/markdown",
    version=get_version(),
    author=AUTHOR,
    author_email='jarbasai@mailfence.com',
    url=URL,
    license='apache-2.0',
    packages=[PKG],
    package_data={PKG: find_resource_files()},
    install_requires=required("requirements.txt"),
    include_package_data=True,
    zip_safe=True,
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Text Processing :: Linguistic',
        'License :: OSI Approved :: Apache Software License'
    ],
    entry_points={
        'neon.plugin.text': UTTERANCE_ENTRY_POINT
    }
)

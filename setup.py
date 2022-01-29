#!/usr/bin/python3
import os
import setuptools
import setuptools.command.build_py

setuptools.setup(
    name='MooTube',
    version='1.3',
    description='MooTube',
    keywords='youtube',
    author='Jake Day',
    url='https://github.com/ninebysix/MooTube',
    python_requires='>=3.8',
    install_requires=[
        'pillow',
        'youtube-search-python',
        'ytmusicapi',
        'python-mpv'
    ],
    include_package_data=True,
    data_files=[
        ('/usr/share/icons/hicolor/scalable/apps', ['mootube/assets/mootube.png']),
        ('/usr/share/applications', ['mootube/assets/mootube.desktop'])
    ],
    package_data={
        "": ["assets/*"]
    },
    packages=setuptools.find_packages(),
    entry_points={
        'console_scripts': [
            'mootube=mootube',
        ],
    },
)

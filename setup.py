import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="pyems",
    version="0.0.1",
    author="Miguel Angel Munoz",
    author_email="miguelangeljmd@gmail.com",
    description="Energy Management System Toolkit for Smart Buildings.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/pypa/sampleproject",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
        "Development Status :: 2 - Pre-Alpha",
    ],
    python_requires='>=3.7',
    install_requires=[
        'DateTime>=4.3'
        'pytz>=2019.1'
        'numpy>=1.16.4'
        'pandas>=0.24.2'
        'influxdb>=5.2.2'
        'matplotlib>=3.1.0'
        'Pyomo>=5.6.2'
        'fbprophet>=0.5'
        'pysolar>=0.8'
        # 'A>=1,<2',
    ]
)
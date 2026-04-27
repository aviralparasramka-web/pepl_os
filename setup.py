from setuptools import setup, find_packages

with open("requirements.txt") as f:
    install_requires = f.read().strip().split("\n")

# get version from __version__ variable in pepl_os/__init__.py
from pepl_os import __version__ as version

setup(
    name="pepl_os",
    version=version,
    description="PEPL Operating System — Custom ERP for Parasramka Engineering Pvt. Ltd.",
    author="Parasramka Engineering Pvt. Ltd.",
    author_email="aviral.parasramka@gmail.com",
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=install_requires,
)

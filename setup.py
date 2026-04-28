"""Setup script for google-search — 临时方案，用于解决 hatchling src 布局打包问题"""
from setuptools import find_packages, setup

setup(
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=["playwright>=1.40.0", "pyyaml>=6.0", "click>=8.1.0"],
    entry_points={
        "console_scripts": ["google-search=google_search.cli:main"],
    },
    python_requires=">=3.10",
)

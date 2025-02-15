"""Create the initial package directory structure."""

from setuptools import find_packages, setup

setup(
    name="mmio_parser",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "pydantic>=2.6.0",
        "pydantic-settings>=2.7.1",
        "click>=8.0.0",
        "rich>=13.9.4",
    ],
    extras_require={
        "dev": [
            "mypy>=1.14.1",
            "pyright>=1.1.392.post0",
            "pylance>=0.22.0",
            "ruff>=0.9.2",
            "pre-commit>=3.6.0",
            "pytest>=8.3.4",
        ]
    },
    python_requires=">=3.10",
    include_package_data=True,
    data_files=[("input/mmio", []), ("output/verilog", [])],
)

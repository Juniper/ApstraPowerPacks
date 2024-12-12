from setuptools import setup, find_packages

setup(
    name="apstra-task-audit",
    version="0.1.0",
    packages=find_packages(where="src") + ["config"],  # Add config package
    package_dir={
        "": "src",
        "config": "config"  # Map config package to config directory
    },
    package_data={
        "config": ["*.yml"],  # Include YAML files in config directory
    },
    install_requires=[
        "redis==5.0.1",
        "click==8.1.7",
        "python-dotenv==1.0.0",
        "pyyaml==6.0.1",
        "requests==2.31.0",
        "pysnmp==4.4.12",
        "syslog-rfc5424-formatter>=1.2.1",  # Added for syslog output
    ],
    entry_points={
        "console_scripts": [
            "apstra-task-audit=src.main:main",
        ],
    },
    python_requires=">=3.7",  # Add if you want to specify minimum Python version
)
from setuptools import find_namespace_packages, setup


setup(
    name="cli-anything-solidworks",
    version="0.1.0",
    description="CLI-Anything harness for controlling SOLIDWORKS through its COM API.",
    packages=find_namespace_packages(include=["cli_anything.*"]),
    include_package_data=True,
    package_data={"cli_anything.solidworks": ["skills/*.md"]},
    install_requires=[
        "click>=8.0.0",
        "prompt-toolkit>=3.0.0",
        "pywin32>=306; platform_system == 'Windows'",
    ],
    entry_points={
        "console_scripts": [
            "cli-anything-solidworks=cli_anything.solidworks.solidworks_cli:main",
        ],
    },
    python_requires=">=3.10",
)

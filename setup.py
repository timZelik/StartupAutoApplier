from setuptools import setup, find_packages

setup(
    name="startup-job-automator",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "playwright>=1.42.0",
        "python-dotenv>=1.0.1",
        "pydantic>=2.5.0,<3.0.0",
        "fastapi>=0.110.0",
        "uvicorn>=0.27.0",
        "httpx>=0.27.0",
        "python-multipart>=0.0.9",
        "loguru>=0.7.2",
    ],
    entry_points={
        "console_scripts": [
            "startup-automator=automation.cli:main",
        ],
    },
)

from setuptools import setup, find_packages

setup(
    name='DevelopmentPackages',
    version='0.0.2.5',
    packages=["DevelopmentPackages"],
    install_requires=[
          'PyQt6',
          "threading",
          "queue",
          "ast",
          "asyncio"
      ],
    zip_safe = False
)
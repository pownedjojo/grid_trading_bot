from setuptools import setup, find_packages

setup(
    name='grid_trading_bot',
    version='1.0',
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'grid_trading_bot=run_bot:main',
        ],
    },
)
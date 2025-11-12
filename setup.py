from setuptools import setup, find_packages

setup(
    name='steamspy_scraper',
    version='0.1.0',
    packages=find_packages(),
    install_requires=['aiohttp', 'nest_asyncio', 'tqdm', 'pandas', 'seaborn', 'matplotlib'],
    entry_points={
        'console_scripts': [
            'scrape = scrapers.scraping:main',
        ],
    },
)
from setuptools import setup, find_packages
setup(
    name = 'qdex',
    version = '0.1',
    packages = ['qdex'],

    install_requires = [
        'pokedex',
        'forrin',
        'sqlalchemy>=0.7.0b3',
        'pyyaml>=3.0',
        'PySide>=1.0',
    ],

    include_package_data = True,

    zip_safe = False,

    entry_points = {
            'console_scripts': [
                    'qdex = qdex:main',
                ],
            'babel.extractors': [
                    'forrin-yaml = qdex.yaml:extractMessages',
                ]
        },

    message_extractors = {
            'qdex': [
                    ('**.py', 'forrin', None),
                    ('**.yaml', 'forrin-yaml', None),
                ],
        },
)

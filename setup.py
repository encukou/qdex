from setuptools import setup, find_packages
setup(
    name = 'qdex',
    version = '0.1',
    packages = ['qdex'],

    install_requires = [
        'pokedex',
        'forrin',
        'PySide>=1.0',
    ],

    include_package_data = True,

    zip_safe = False,

    entry_points = {
            'console_scripts': [
                    'qdex = qdex:main',
                ],
        },

    message_extractors = {
            'qdex': [
                    ('**.py', 'forrin', None),
                ],
        },
)

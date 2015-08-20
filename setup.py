from setuptools import setup

setup(
    name='jenkinsstatus',
    version='0.1.1',
    py_modules=['jenkinsstatus'],
    install_requires=[
        'Click',
        'termcolor',
        'requests',
        'tabulate',
    ],
    entry_points='''
        [console_scripts]
        jenkinsstatus=jenkinsstatus:cli
    ''',
)

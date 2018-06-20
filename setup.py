from setuptools import setup

setup(name='datalabframework',
      version='0.1.1',
      install_requires=[
        'requests',
        'pyyaml'
      ],
      description='Scaffolding Data Science with Python Notebooks',
      url='http://github.com/natbusa/datalabframework',
      author='Natalino Busa',
      author_email='natalino.busa@gmail.com',
      license='MIT',
      packages=['datalabframework'],
      zip_safe=False)

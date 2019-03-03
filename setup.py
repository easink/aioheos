from setuptools import setup

# http://stackoverflow.com/questions/6357361/alternative-to-execfile-in-python-3
exec(compile(open('aioheos/version.py', 'rb').read(), 'aioheos/version.py', 'exec'))

setup(name='aioheos',
      version=__version__,
      description='Denon HEOS',
      url='http://github.com/easink/aioheos',
      author='Andreas Rydbrink',
      author_email='andreas.rydbrink@gmail.com',
      license='MIT',
      packages=['aioheos'],
      long_description=open('README.md').read(),
      install_requires=[
          'lxml',
          'aiohttp',
      ],
      classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
      ],
      zip_safe=False)

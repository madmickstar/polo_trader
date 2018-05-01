from setuptools import setup
setup(name='polo_trader',
      version='0.0.1',
      description='Polo trader is a tool for automating trades on the Poloniex Exchange for Python 2.7',
      url='https://github.com/madmickstar/polo_trader/',
      author='madmickstar',
      license='MIT',
      packages=['polo_trader'],
      install_requires=['requests', 'pytz', 'tzlocal'],
      zip_safe=False)

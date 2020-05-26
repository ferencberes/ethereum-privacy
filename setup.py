from distutils.core import setup

setup(name='ethprivacy',
      version='0.1',
      description="Profiling and Deanonymizing Ethereum Users",
      url='',
      author='Ferenc Beres',
      author_email='fberes@info.ilab.sztaki.hu',
      packages=['ethprivacy'],
      install_requires=[
          'numpy',
          'pandas',
          'networkx',
          'karateclub',
          'tqdm',
          'matplotlib',
          'seaborn',
      ],
      zip_safe=False
)
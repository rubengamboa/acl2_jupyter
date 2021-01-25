from distutils.core import setup
setup(
  name = 'acl2_jupyter',
  packages = ['acl2_jupyter'],
  version = '0.3',
  license='bsd-3-clause',
  description = 'Jupyter Kernel for ACL2',
  author = 'Ruben Gamboa',
  author_email = 'ruben@uwyo.edu',
  url = 'https://github.com/rubengamboa/acl2_jupyter',
  download_url = 'https://github.com/rubengamboa/acl2_jupyter/archive/v0_3.zip',
  keywords = ['ACL2', 'theorem proving', 'verification'],
  install_requires = ['acl2_bridge'],
  classifiers=[
    'Development Status :: 3 - Alpha',
    'Intended Audience :: Education',
    'Topic :: Education',
    'License :: OSI Approved :: BSD License',
    'Programming Language :: Python :: 3.8',
  ],
)

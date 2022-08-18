from distutils.core import setup
setup(
  name = 'acl2_jupyter',
  packages = ['acl2_jupyter'],
  version = '1.0',
  license='bsd-3-clause',
  description = 'Jupyter Kernel for ACL2',
  long_description = """This package allows you to connect an ACL2 process running with the ACL2 Bridge to a Jupyter notebook server.""",
  long_description_content_type = "text/markdown",
  author = 'Ruben Gamboa',
  author_email = 'ruben@uwyo.edu',
  url = 'https://github.com/rubengamboa/acl2_jupyter',
  download_url = 'https://github.com/rubengamboa/acl2_jupyter/archive/v1_0.zip',
  keywords = ['ACL2', 'theorem proving', 'verification'],
  install_requires = ['acl2_bridge'],
  classifiers=[
    'Development Status :: 5 - Production/Stable',
    'Intended Audience :: Education',
    'Topic :: Education',
    'License :: OSI Approved :: BSD License',
    'Programming Language :: Python :: 3.8',
  ],
)

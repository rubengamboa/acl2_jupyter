# Acl2_jupyter - Jupyter Kernel for ACL2

With Acl2_jupyter, you can creater [ACL2](https://www.cs.utexas.edu/users/moore/acl2/) notebooks from Jupyter. The notebooks will access an ACL2 server running an [ACL2::Bridge](https://www.cs.utexas.edu/users/moore/acl2/manuals/current/manual/index.html?topic=ACL2____BRIDGE). 
Note that you must have an ACL2 server and a Jupyter notebook server running for this package to be useful.

## Usage

To download this package, simply fork this github repo or use Pypy via pip;

    $ pip install acl2_jupyter

Then create a kernel configuration file in the Jupyter server, e.g., your Jupyter server may look for kernels in `/usr/local/share/jupyter/kernels`, in which case create the file `/usr/local/share/jupyter/kernels/acl2/acl2_kernel.py` with these contents:

    {
     "argv": ["python3", "-m", "acl2_jupyter.acl2_kernel", "-f", "{connection_file}"],
     "display_name": "ACL2",
     "language": "acl2",
     "codemirror_mode":"Common Lisp"
    }

Then you should be able to start up a new ACL2 Jupyter notebook.

## LICENSE

This package is released with the same license as ACL2, the BSD 3-Clause license.

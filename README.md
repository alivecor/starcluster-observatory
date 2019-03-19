## starcluster-observatory is a web-based job and resource manager for StarCluster.


Requires: [dantreiman's fork of StarCluster](https://github.com/dantreiman/StarCluster)


This package is not meant to be distributed alone.  It is installed automatically on your master node by the 'observatory'
plugin provided by [StarCluster](https://github.com/dantreiman/StarCluster).

User in conjunction with the JupyterHub plugin, the observatory plugin adds two pages to the JupyterHub
navigation bar: Jobs and Nodes.  These pages will only be added if the current user is whitelisted as a JupyterHub admin.


The nodes page shows a list of the EC2 instances belonging to the current cluster, and allows users to start or terminate
instances from JupyterHub.

![Image of Nodes Page](docs/images/nodes_page.png?raw=true)

The jobs page displays running and pending SGE jobs, and allows users to inspect or cancel them from JupyterHub.

![Image of Jobs Page](docs/images/jobs_page.png?raw=true)


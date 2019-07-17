"""Static AWS Constants"""


# Cost per hour of on-demand instances by type
ondemand_instance_cost = {
    # General Purpose
    't2.nano':     0.0058,
    't2.micro':    0.0116,
    't2.small':    0.023,
    't2.medium':   0.0464,
    't2.large':    0.0928,
    't2.xlarge':   0.1856,
    # Compute Optimized
    'c4.large':    0.1,
    'c4.xlarge':   0.199,
    'c4.2xlarge':  0.398,
    'c4.4xlarge':  0.796,
    'c4.8xlarge':  1.591,
    'c5.large': 0.085,
    'c5.xlarge': 0.17,
    'c5.2xlarge': 0.34,
    'c5.4xlarge': 0.68,
    'c5.9xlarge': 1.53,
    'c5.18xlarge': 3.06,
    'c5.24xlarge': 4.08,
    # Memory Optimized
    'm4.16xlarge': 3.20,
    # GPU Compute
    'p2.xlarge':   0.9,
    'p2.8xlarge':  7.2,
    'p2.16xlarge': 14.4,
    'p3.2xlarge':  3.06,
    'p3.8xlarge':  12.24,
    'p3.16xlarge': 24.48,
    'g3.4xlarge':  1.14,
    'g3.8xlarge':  2.28,
    'g3.16xlarge': 4.56,
    # Memory Optimized
    'x1.16xlarge': 6.669,
    'x1.32xlarge': 13.338,
}


GENERAL_PURPOSE = 'General'
CPU = 'CPU'
GPU = 'GPU'
MEMORY = 'Memory'

# Display name for different instance types.
instance_types = {
    # General Purpose
    't2.nano': GENERAL_PURPOSE,
    't2.micro': GENERAL_PURPOSE,
    't2.small': GENERAL_PURPOSE,
    't2.medium': GENERAL_PURPOSE,
    't2.large': GENERAL_PURPOSE,
    't2.xlarge': GENERAL_PURPOSE,
    # Compute Optimized
    'c4.large': CPU,
    'c4.xlarge': CPU,
    'c4.2xlarge': CPU,
    'c4.4xlarge': CPU,
    'c4.8xlarge': CPU,
    'c5.large': CPU,
    'c5.xlarge': CPU,
    'c5.2xlarge': CPU,
    'c5.4xlarge': CPU,
    'c5.9xlarge': CPU,
    'c5.18xlarge': CPU,
    'c5.24xlarge': CPU,
    # GPU Compute
    'p2.xlarge': GPU,
    'p2.8xlarge': GPU,
    'p2.16xlarge': GPU,
    'p3.2xlarge': GPU,
    'p3.8xlarge': GPU,
    'p3.16xlarge': GPU,
    'g3.4xlarge': GPU,
    'g3.8xlarge': GPU,
    'g3.16xlarge': GPU,
    # Memory Optimized
    'm4.16xlarge': MEMORY,
    'x1.16xlarge': MEMORY,
    'x1.32xlarge': MEMORY,
}
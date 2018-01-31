"""Static AWS Constants"""


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


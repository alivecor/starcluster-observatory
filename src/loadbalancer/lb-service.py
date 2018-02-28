#!/usr/bin/python3
import argparse


import load_balancer


parser = argparse.ArgumentParser(description='Run a load-balancer service on the starcluster API.')
parser.add_argument('--api_server_host', default='127.0.0.1', type=str, help='IP address of the backend.')
parser.add_argument('--api_server_port', default=6361, type=int, help='Port to use to connect to API server.')
parser.add_argument('--cpu_type', default='c4.large', type=str, help='Default instance type for cpu jobs.')
parser.add_argument('--gpu_type', default='p3.2xlarge', type=str, help='Default instance type for gpu jobs.')
parser.add_argument('--idle_timeout', default=45, type=int, help='Shut down nodes if idle longer than this (minutes).')
parser.add_argument('--polling_interval', default=5, type=int, help='Polling interval for load balancer (minutes).')
parser.add_argument('--max_capacity', default=16, type=int, help='Maximum number of nodes to allow.')

args = parser.parse_args()


lb = load_balancer.LoadBalancer(args.api_server_host,
                                args.api_server_port,
                                args.max_capacity,
                                cpu_type=args.cpu_type,
                                gpu_type=args.gpu_type,
                                idle_timeout=args.idle_timeout * 60,
                                polling_interval=args.polling_interval * 60)


if __name__ == '__main__':
    print('Load balancer starting polling', flush=True)
    lb.start_polling()

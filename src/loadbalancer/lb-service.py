#!/usr/bin/python3
import argparse


import load_balancer


parser = argparse.ArgumentParser(description='Run a load-balancer service on the starcluster API.')
parser.add_argument('--api_server_host', default='127.0.0.1', type=str, help='IP address of the backend.')
parser.add_argument('--api_server_port', default=6361, type=int, help='Port to use to connect to API server.')
parser.add_argument('--polling_interval', default=5, type=int, help='Polling interval for load balancer (minutes).')
parser.add_argument('--max_capacity', default=16, type=int, help='Maximum number of nodes to allow.')

args = parser.parse_args()


lb = load_balancer.LoadBalancer(args.api_server_host,
                                args.api_server_port,
                                args.max_capacity,
                                polling_interval=args.polling_interval * 60)


if __name__ == '__main__':
    print('Load balancer starting polling', flush=True)
    lb.start_polling()

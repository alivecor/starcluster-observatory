import argparse
import time


parser = argparse.ArgumentParser(description='Do nothing for a specified number of seconds.', allow_abbrev=True)
parser.add_argument('--seconds', default=120.0, type=int, help='Number of seconds.')

args = parser.parse_args()


print('Sleeping for %d seconds' % args.seconds)
for s in range(args.seconds):
    time.sleep(1)
print('Done')

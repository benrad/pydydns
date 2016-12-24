# PyDyDNS

A simple script to update a Route53 record to point to one's public IP. I use this to keep a Raspberry Pi in my house accessible from the public internet.

I considered creating this as a Lambda+API Gateway function that's hit with a key and client IP, but containing the functionality in one place ended up being simpler.

## Setup

0. You'll need a domain managed by Route53 with a subdomain to keep pointed to your IP.

1. Create an IAM user and get an access key. IAM user should have AmazonRoute53FullAccess policy.

2. Add credentials and domain to config file. See sample config. (You can also `pip install awscli` and run `aws configure` to have boto3 use your stored credentials.)

3. Add a `cron` job to run `python dydns.py` at whatever interval you'd like.
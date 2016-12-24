import ConfigParser
import requests
import boto3

config = ConfigParser.ConfigParser()
config.read('./config.txt')
AWS_KEY_ID = config.get('auth', 'aws_access_key_id')
AWS_SECRET_KEY = config.get('auth', 'aws_secret_access_key')
TARGET_DOMAIN = config.get('target', 'target_domain')


def get_ip():
	r = requests.get('http://httpbin.org/ip')
	if r.status_code != 200:
		raise Exception('Non-200 response, aborting')
	return r.json()['origin']


def update_record(client, zone_id, domain_name, ip_address, ttl=300):
	change_batch = {
		'Comment': 'Dynamic DNS pointer', 
		'Changes': [
				{
					'Action': 'UPSERT', 
					'ResourceRecordSet': {
						'ResourceRecords': [
							{
								'Value': ip_address
							}
						],
					'Type': 'A',
					'Name': domain_name, 
					'TTL': ttl
				}
			}
		]
	}
	
	client.change_resource_record_sets(HostedZoneId=zone_id, ChangeBatch=change_batch)


def get_id_for_domain(client, domain_name):
	zones = client.list_hosted_zones()
	try:
		record = filter(lambda zone:zone['Name'].rstrip('.') in domain_name, zones['HostedZones'])[0]
	except IndexError:
		raise Exception('No record found for domain name {0}'.format(domain_name))
	return record['Id'].strip('/hostedzone/')


def main():
	r53 = boto3.client('route53', aws_access_key_id=AWS_KEY_ID, aws_secret_access_key=AWS_SECRET_KEY)
	my_ip = get_ip()
	zone_id = get_id_for_domain(r53, TARGET_DOMAIN)
	update_record(r53, zone_id, TARGET_DOMAIN, my_ip)


if __name__ == '__main__':
	main()

import ConfigParser
import logging
import datetime
import requests
import boto3

config = ConfigParser.ConfigParser()
config.read('./config.txt')
AWS_KEY_ID = config.get('auth', 'aws_access_key_id')
AWS_SECRET_KEY = config.get('auth', 'aws_secret_access_key')
TARGET_DOMAIN = config.get('target', 'target_domain')
LOG_FILE = 'dydns-{0}.log'.format(datetime.date.today())

logger = logging.getLogger(__name__)
formatter = logging.Formatter('%(levelname)s %(asctime)s: %(message)s')
loghandler = logging.FileHandler(LOG_FILE)
loghandler.setFormatter(formatter)
logger.addHandler(loghandler)
logger.setLevel(logging.DEBUG)


class route53(object):

    def __init__(self, access_key_id, secret_key):
        self._client = boto3.client('route53', aws_access_key_id=access_key_id, aws_secret_access_key=secret_key)
        self._zones = None
        self._records_cache = {}


    @property
    def zones(self):
        if not self._zones:
            self._zones = self._client.list_hosted_zones()['HostedZones']
        return self._zones

    
    def _list_resource_record_sets(self, hosted_zone_id):
        if hosted_zone_id in self._records_cache:
            return self._records_cache[hosted_zone_id]
        else:
            record = self._client.list_resource_record_sets(HostedZoneId=hosted_zone_id)['ResourceRecordSets']
            self._records_cache[hosted_zone_id] = record
            return record


    def _get_hostedzone_for_domain(self, domain_name):
        try:
            return filter(lambda zone:zone['Name'].rstrip('.') in domain_name, self.zones)[0]
        except IndexError:
            raise Exception('No record found for domain name {0}'.format(domain_name))


    def _get_domain_record(self, domain_name):
        zone_id = self._get_zone_id_from_info(self._get_hostedzone_for_domain(domain_name))
        record_sets = self._list_resource_record_sets(zone_id)
        matches = [record for record in record_sets if record['Name'].rstrip('.') == domain_name and record['Type'] == 'A']
        if len(matches) > 1:
            raise Exception('Ambiguous value for domain name {0}; aborting.'.format(domain_name))
        try:
            return matches[0]
        except IndexError:
            raise Exception('No record found for domain {0}'.format(domain_name))


    def _record_is_current(self, domain_name, current_ip):
        record = self._get_domain_record(domain_name)
        record_target = record['ResourceRecords'][0]['Value']
        return record_target == current_ip


    # could be a @staticmethod
    def _get_zone_id_from_info(self, zone_info):
        return zone_info['Id'].strip('/hostedzone/')


    def try_update_record(self, domain_name, ip_address, ttl=300):
        """Checks whether current domain record points to IP address and repoints if not.
        Returns True if an update was necessary, False if the record was already correctly pointed.
        """
        if self._record_is_current(domain_name, ip_address):
            return False
        zone_id = self._get_zone_id_from_info(self._get_hostedzone_for_domain(domain_name))
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
        
        self._client.change_resource_record_sets(HostedZoneId=zone_id, ChangeBatch=change_batch)
        return True


def get_ip():
    r = requests.get('http://httpbin.org/ip')
    if r.status_code != 200:
        raise Exception('Non-200 response, aborting. Status code: {0}'.format(r.status_code))
    return r.json()['origin']


def main():
    try:
        r53 = route53(AWS_KEY_ID, AWS_SECRET_KEY)
        my_ip = get_ip()
        if r53.try_update_record(TARGET_DOMAIN, my_ip):
            logger.info('Updated domain {0} to IP {1}'.format(TARGET_DOMAIN, my_ip))
        else:
            logger.info('No change made. Domain {0} remains pointed to IP {1}'.format(TARGET_DOMAIN, my_ip))
    except Exception as e:
        logger.debug("Failed to update with exception: {0}".format(e.message))


if __name__ == '__main__':
    main()

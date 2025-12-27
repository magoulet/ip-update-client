#!/usr/bin/env python

import boto3
import pickle
import requests
from requests.auth import HTTPBasicAuth
import yaml


def currentIP():

    url = 'http://ipinfo.io/json'
    params = {}

    try:
        y = requests.get(url=url, params=params)

        return y.json()['ip']
    except Exception as e:
        print("Failed to determine current IP address")
        raise SystemExit(e)


def telegramNotification(cfg, body):

    url = 'https://api.telegram.org/bot{0}/{1}'.format(cfg['token'],
                                                       cfg['method'])
    params = {
        'chat_id': cfg['chat_id'],
        'parse_mode': 'Markdown',
        'text': body
    }

    response = requests.post(url=url,
                             params=params)

    return response.text


def send_mailgun_notification(cfg, body):
    """
    Send notification using Mailgun API
    
    Args:
        cfg (dict): Configuration dictionary containing Mailgun settings
        body (str): Message body to send
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Extract Mailgun configuration
        mailgun_cfg = cfg.get('mailgun', {})
        api_key = mailgun_cfg.get('api_key')
        domain = mailgun_cfg.get('domain')
        sender = mailgun_cfg.get('sender_email')
        recipient = mailgun_cfg.get('recipient_email')
        subject = mailgun_cfg.get('subject')

        # Verify all required configuration is present
        if not all([api_key, domain, sender, recipient, subject]):
            print("Error: Missing required Mailgun configuration")
            return False

        # Prepare the API request
        url = f"https://api.mailgun.net/v3/{domain}/messages"
        auth = ("api", api_key)
        data = {
            "from": sender,
            "to": recipient,
            "subject": subject,
            "text": body
        }

        # Send the request
        response = requests.post(url, auth=auth, data=data)

        # Check if the request was successful
        if response.status_code == 200:
            print("Notification sent successfully")
            return True
        else:
            print(f"Failed to send notification. Status code: {response.status_code}")
            print(f"Response: {response.text}")
            return False

    except Exception as e:
        print(f"Error sending notification: {str(e)}")
        return False

def send_ntfy_notification(cfg, body):
    """
    Send notification using ntfy
    
    Args:
        cfg (dict): Configuration dictionary containing Mailgun settings
        body (str): Message body to send
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Extract ntfy configuration
        ntfy_cfg = cfg.get('ntfy', {})
        hostname = ntfy_cfg.get('hostname')
        token = ntfy_cfg.get('token')
        topic = ntfy_cfg.get('topic')

        # Verify all required configuration is present
        if not all([token, topic]):
            print("Error: Missing required ntfy configuration")
            return False

        # Prepare the API request
        url = f"{hostname}/{topic}"
        headers = {
            "Title": "IP Address Update",
            "Authorization": f"Bearer {token}"
        }
        data = body

        # Send the request
        response = requests.post(url, headers=headers, data=data)

        # Check if the request was successful
        if response.status_code == 200:
            print("Notification sent successfully")
            return True
        else:
            print(f"Failed to send notification. Status code: {response.status_code}")
            print(f"Response: {response.text}")
            return False

    except Exception as e:
        print(f"Error sending notification: {str(e)}")
        return False


def openDnsUpdate(cfg):
    url = 'https://updates.opendns.com/nic/update'
    params = {
        'hostname': cfg['label']
    }
    try:
        y = requests.post(url=url,
                          params=params,
                          auth=HTTPBasicAuth(cfg['username'],
                                             cfg['password'])
                          )
        print('openDNS ({}):'.format(cfg['label']), y.text)
        return y.text
    except Exception:
        print('Failed to update OpenDNS IP')


def awsRoute53Update(cfg, ipAddr):
    client = boto3.client('route53', aws_access_key_id=cfg['awsAccessKeyId'],
                          aws_secret_access_key=cfg['awsSecretAccessKey'])
    y = client.change_resource_record_sets(
        HostedZoneId=cfg['hosted_zone_id'],
        ChangeBatch={
            'Comment': 'Update from ipUpdateClient',
            'Changes': [
                {
                    'Action': 'UPSERT',
                    'ResourceRecordSet': {
                        'Name': cfg['label'],
                        'Type': 'A',
                        'TTL': cfg['TTL'],
                        'ResourceRecords': [
                            {
                                'Value': ipAddr
                            },
                            ],
                        }
                },
                ]
        }
    )

    print('AWS Route 53 ({}): {}, {}'.
          format(cfg['label'],
                 y['ResponseMetadata']['HTTPStatusCode'],
                 y['ChangeInfo']['Status']))

def fetch_all_record_data(zone_id, token):
    url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    records_dict = {}
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        records = response.json().get("result", [])
        
        # Only keep "A" type records
        for record in records:
            if record['type'] == 'A':
                records_dict[record['name']] = {
                    'record_id': record['id'],
                    'ttl': record['ttl'],
                    'proxied': record['proxied'],
                    'type': record['type']
                }
    else:
        print("Failed to fetch DNS records for zone:", zone_id)
        print(response.status_code, response.text)
    
    return records_dict

def cloudflare_update(cfg, ipAddr):
    cloudflare_config = cfg['cloudflare']

    # Iterate over each domain in cloudflare config
    for domain, domain_data in cloudflare_config.items():
        API_TOKEN = domain_data['api_token']
        ZONE_ID = domain_data['zone_id']
        records = domain_data['records']

        # Fetch all "A" type records once for the current zone
        all_record_data = fetch_all_record_data(ZONE_ID, API_TOKEN)

        for record_name in records:
            # Attempt to fill in missing information from the fetched data
            api_data = all_record_data.get(record_name, {})
            
            record_id = api_data.get('record_id')
            if not record_id:
                print(f"Could not find record ID for {record_name}. Skipping.")
                continue  # Skip updating if record ID can't be found

            record_ttl = api_data.get('ttl')
            record_proxied = api_data.get('proxied')
            record_type = api_data.get('type', 'A')  # Default to 'A' if not found

            # Update only if the record is of type 'A'
            if record_type != 'A':
                print(f"Skipping record {record_name} because it is not of type 'A'.")
                continue

            url = f"https://api.cloudflare.com/client/v4/zones/{ZONE_ID}/dns_records/{record_id}"
            headers = {
                "Authorization": f"Bearer {API_TOKEN}",
                "Content-Type": "application/json"
            }
            data = {
                "type": record_type,
                "name": record_name,
                "content": ipAddr,
                "ttl": record_ttl,
                "proxied": record_proxied
            }

            response = requests.put(url, headers=headers, json=data)

            # Check the result of the API call
            if response.status_code == 200:
                print(f"DNS record {record_name} updated successfully in zone {domain}.")
            else:
                print(f"Failed to update DNS record {record_name} in zone {domain}.")
                print(response.status_code, response.text)

if __name__ == "__main__":

    cfg = yaml.load(open('config.yml'), Loader=yaml.FullLoader)

    currIpAddr = currentIP()

    try:
        with open('prevIpAddr.pickle', 'rb') as file:
            prevIpAddr = pickle.load(file)
    except Exception:
        prevIpAddr = None

    if currIpAddr != prevIpAddr:
        openDnsUpdate(cfg['openDNS'])
        # awsRoute53Update(cfg['awsRoute53']['magoulet.com'], currIpAddr)
        cloudflare_update(cfg, currIpAddr)

        body = 'ipUpdateClient: IP has changed. '\
               'Current IP is: {}, previous IP '\
               'was: {}'.format(currIpAddr, prevIpAddr)
        print(body)

        notification_method = cfg.get('notifications', {}).get('method','').lower()

        if notification_method == 'telegram':
            telegramNotification(cfg['telegram'], body)
        elif notification_method == 'mailgun':
            send_mailgun_notification(cfg, body)
        elif notification_method == 'ntfy':
            send_ntfy_notification(cfg, body)
        else:
            print(f"Error: Unknown notification method '{notification_method}'")

        with open('prevIpAddr.pickle', 'wb') as file:
            pickle.dump(currIpAddr, file)
    else:
        print('No IP update required')

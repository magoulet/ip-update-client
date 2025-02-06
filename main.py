#!/usr/bin/env python

import boto3
import pickle
import requests
from requests.auth import HTTPBasicAuth
import yaml


def currentIP():

    url = 'http://ifconfig.me/all.json'
    params = {
    }

    y = requests.get(url=url, params=params).json()

    return y['ip_addr']


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
        awsRoute53Update(cfg['awsRoute53']['magoulet.com'], currIpAddr)
        body = 'ipUpdateClient: IP has changed. '\
               'Current IP is: {}, previous IP '\
               'was: {}'.format(currIpAddr, prevIpAddr)
        print(body)

        notification_method = cfg.get('notifications', {}).get('method','').lower()

        if notification_method == 'telegram':
            telegramNotification(cfg['telegram'], body)
        elif notification_method == 'mailgun':
            send_mailgun_notification(cfg, body)
        else:
            print(f"Error: Unknown notificaiton method '{notification_method}'")

        with open('prevIpAddr.pickle', 'wb') as file:
            pickle.dump(currIpAddr, file)
    else:
        print('No IP update required')

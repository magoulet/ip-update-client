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


def googleDomainUpdate(cfg):
    url = 'https://{}:{}@domains.google.com/nic/update'.\
        format(cfg['username'], cfg['password'])
    params = {
        'hostname': cfg['label']
    }

    try:
        y = requests.post(url=url,
                          params=params
                          )
        print('Google Domains ({}): '.format(cfg['label']), y.text)
        return y.text
    except Exception:
        print('Failed to update Google Domains IP')


def awsRoute53Update(cfg, ipAddr):
    client = boto3.client('route53', aws_access_key_id=cfg['awsAccessKeyId'],
                          aws_secret_access_key=cfg['awsSecretAccessKey'])
    response = client.change_resource_record_sets(
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

    print('DNS record status: {}'.format(response['ChangeInfo']['Status']))
    print('DNS record response code: {}'.
          format(response['ResponseMetadata']['HTTPStatusCode']))


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
        googleDomainUpdate(cfg['googleDomain']['magoulet.net'])
        googleDomainUpdate(cfg['googleDomain']['www.magoulet.net'])
        awsRoute53Update(cfg['awsRoute53']['magoulet.com'], currIpAddr)
        body = 'ipUpdateClient: IP has changed. '\
               'Current IP is: {}, previous IP '\
               'was: {}'.format(currIpAddr, prevIpAddr)
        print(body)
        # telegramNotification(cfg['telegram'], body)

        with open('prevIpAddr.pickle', 'wb') as file:
            pickle.dump(currIpAddr, file)
    else:
        print('No IP update required')

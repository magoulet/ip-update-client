# IP Update Client

The IP Update Client is a Python script intended for users with dynamic IPs. It updates various downstream services whenever the user's IP address changes. The script retrieves the current IP address, compares it with the previously recorded IP address, and updates the configured services accordingly.

## Table of Contents
- [Introduction](#introduction)
- [Requirements](#requirements)
- [Configuration](#configuration)
- [Retrieving Current IP](#retrieving-current-ip)
- [Service Updates](#service-updates)
  - [OpenDNS](#opendns-update)
  - [Google Domains](#google-domains-update)
  - [AWS Route 53](#aws-route-53-update)
- [Notification](#notification)
- [Conclusion](#conclusion)

## Introduction

The IP Update Client script is designed for users whose IP addresses change dynamically. It automates the process of updating downstream services that rely on the IP address. The script retrieves the current IP address, compares it with the previous IP address, and updates the necessary services if a change is detected.

## Requirements

To run the IP Update Client, ensure the following libraries are installed:
- `boto3` - The Amazon Web Services (AWS) SDK for Python.
- `pickle` - Library for serializing Python objects.
- `requests` - Library for making HTTP requests.
- `requests.auth` - Module to handle HTTP basic authentication.
- `yaml` - Library for working with YAML configuration files.

Make sure to install these libraries before using the IP Update Client script.

## Configuration

The IP Update Client requires a configuration file named `config.yml`. This file contains the necessary settings for each service to be updated. Copy `config_example.yml` to `config.yml` and modify values as needed.


## Retrieving Current IP

The `currentIP` function retrieves the current public IP address by sending an HTTP request to `ifconfig.me`. The IP address is extracted from the JSON response and returned.

## Service Updates

The IP Update Client script updates various services when the IP address changes. It compares the current IP address with the previously recorded IP address to determine if an update is required.

### OpenDNS Update

The `openDnsUpdate` function updates the IP address for the OpenDNS service. It sends an HTTP POST request to the OpenDNS update API with the necessary parameters and authentication. The response from the API is printed to the console.

### Google Domains Update

The `googleDomainUpdate` function updates the IP address for the Google Domains service. It sends an HTTP POST request to the Google Domains update API with the necessary parameters and authentication. The response from the API is printed to the console.

### AWS Route 53 Update

The `awsRoute53Update` function updates the IP address for the AWS Route 53 service. It uses the Boto3 library to interact with the AWS Route 53 API. The `change_resource_record_sets` method is called to update the IP address in the specified hosted zone. The response from the API is printed to the console.

## Notification

The `telegramNotification` function sends a notification message via the Telegram API. It formats the message body and sends an HTTP POST request to the Telegram API with the necessary parameters. The response from the API is returned.

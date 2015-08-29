#!/usr/bin/env python

from config import xero_config

from xero import Xero
from xero.auth import PublicCredentials, PrivateCredentials

# Connect to Xero
credentials = PrivateCredentials(xero_config['consumer_key'], xero_config['private_key'])
xero = Xero(credentials)

# Get userids matching user email
userids = {}
#users = xero.users.all()
#print(users)
employees = xero.payrollAPI.employees.all()
print(employees)

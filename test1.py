#!/usr/bin/env python3

from __future__ import unicode_literals

from datetime import datetime
from config import xero_config

from xero import Xero
from xero.auth import PrivateCredentials

# Connect to Xero
credentials = PrivateCredentials(xero_config['consumer_key'], xero_config['private_key'])
xero = Xero(credentials)

# Get userids matching user email
#userids = {}
#users = xero.users.all()
#print(users)
#employees = xero.payrollAPI.employees.all()
#print(employees)
#print(xero.manualjournals.all())
#print(xero.linkedtransactions.all())
#print(xero.journals.filter(Journal_SourceID='8a428893-8812-4286-99e7-1e5a3a20fd54'))

def get_accounts():
    print(xero.accounts.all())

def get_journals():
    # journal 1-6442
    journals = []
    for i in range(1, 6500, 100):
        journals.extend(xero.journals.filter(offset=i))
    
    print(journals)

def get_payments():
    print(xero.payments.all())

get_accounts()

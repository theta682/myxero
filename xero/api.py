from __future__ import unicode_literals
from .manager import Manager
from .filesmanager import FilesManager
from .constants import XERO_PAYROLL_URL


class Xero(object):
    """An ORM-like interface to the Xero API"""

    OBJECT_LIST = (
        "Attachments",
        "Accounts",
        "BankTransactions",
        "BankTransfers",
        "BrandingThemes",
        "ContactGroups",
        "Contacts",
        "CreditNotes",
        "Currencies",
        "Employees",
        "ExpenseClaims",
        "Invoices",
        "Items",
        "Journals",
        "LinkedTransactions",
        "ManualJournals",
        "Organisations",
        "Overpayments",
        "Payments",
        "Prepayments",
        "Receipts",
        "RepeatingInvoices",
        "Reports",
        "TaxRates",
        "TrackingCategories",
        "Users",
    )

    def __init__(self, credentials, unit_price_4dps=False):
        # Iterate through the list of objects we support, for
        # each of them create an attribute on our self that is
        # the lowercase name of the object and attach it to an
        # instance of a Manager object to operate on it
        for name in self.OBJECT_LIST:
            setattr(self, name.lower(), Manager(name, credentials, unit_price_4dps))

        setattr(self, "filesAPI", Files(credentials))

        setattr(self, "payrollAPI", Payroll(credentials))


class Files(object):
    """An ORM-like interface to the Xero Files API"""

    OBJECT_LIST = (
        "Associations",
        "Files",
        "Folders",
        "Inbox",
    )

    def __init__(self, credentials):
        # Iterate through the list of objects we support, for
        # each of them create an attribute on our self that is
        # the lowercase name of the object and attach it to an
        # instance of a Manager object to operate on it
        for name in self.OBJECT_LIST:
            setattr(self, name.lower(), FilesManager(name, credentials))


class Payroll(object):
    """An ORM-like interface to the Xero Files API"""

    OBJECT_LIST = (
        "Employees",
        "LeaveApplications",
        "PayItems",
        "PayrollCalendars",
        "PayRuns",
        "Payslip",
        "Settings",
        "SuperFunds",
        "SuperFundProducts",
        "Timesheets",
        "Worklocations",
    )

    def __init__(self, credentials):
        # Iterate through the list of objects we support, for
        # each of them create an attribute on our self that is
        # the lowercase name of the object and attach it to an
        # instance of a Manager object to operate on it
        for name in self.OBJECT_LIST:
            setattr(self, name.lower(), Manager(name, credentials, api_url=XERO_PAYROLL_URL))

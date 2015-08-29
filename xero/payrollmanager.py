from __future__ import unicode_literals

import requests
import six
import json

from xml.dom.minidom import parseString
from xml.etree.ElementTree import tostring, SubElement, Element
from datetime import datetime
from dateutil.parser import parse
from decimal import Decimal
from six.moves.urllib.parse import parse_qs

from .constants import XERO_PAYROLL_URL
from .exceptions import *
from .utils import parse_date, json_load_object_hook


OBJECT_NAMES = {
    "Employees": "Employee",
    "LeaveApplications": "LeaveApplication",
    "PayItems": "PayItem",
    "PayrollCalendars": "PayrollCalendar",
    "PayRuns": "PayRun",
    "Payslip": "Payslip",
    "Settings": "Setting",
    "SuperFunds": "SuperFund",
    "SuperFundProducts": "SuperFundProduct",
    "Timesheets": "Timesheet",
    "Worklocations": "Worklocation",
}

def isplural(word):
    return word in OBJECT_NAMES.keys()

def singular(word):
    return OBJECT_NAMES.get(word)

class PayrollManager(object):
    DECORATED_METHODS = (
        'get',
        'save',
        'filter',
        'all',
        'put',
        'get_attachments',
        'get_attachment_data',
        'put_attachment_data',
    )
    DATETIME_FIELDS = (
        'UpdatedDateUTC',
        'Updated',
        'FullyPaidOnDate',
        'DateTimeUTC',
        'CreatedDateUTC'
    )
    DATE_FIELDS = (
        'DueDate',
        'Date',
        'PaymentDate',
        'StartDate',
        'EndDate',
        'PeriodLockDate',
        'DateOfBirth',
        'OpeningBalanceDate',
        'PaymentDueDate',
        'ReportingDate',
        'TerminationDate',
    )
    BOOLEAN_FIELDS = (
        'IsSupplier',
        'IsCustomer',
        'IsDemoCompany',
        'PaysTax',
        'IsAuthorisedToApproveTimesheets',
        'IsAuthorisedToApproveLeave',
        'HasHELPDebt',
        'AustralianResidentForTaxPurposes',
        'TaxFreeThresholdClaimed',
        'HasSFSSDebt',
        'EligibleToReceiveLeaveLoading',
        'IsExemptFromTax',
        'IsExemptFromSuper',
        'SentToContact',
        'IsSubscriber',
        'HasAttachments',
        'IsPrimary',
    )
    DECIMAL_FIELDS = (
        'Hours',
        'NumberOfUnit',
    )
    INTEGER_FIELDS = (
        'FinancialYearEndDay',
        'FinancialYearEndMonth',
    )
    NO_SEND_FIELDS = (
        'UpdatedDateUTC',
    )
    OPERATOR_MAPPINGS = {
        'gt': '>',
        'lt': '<',
        'lte': '<=',
        'gte': '>=',
        'ne': '!='
    }

    def __init__(self, name, credentials, unit_price_4dps=False):
        self.credentials = credentials
        self.name = name
        self.base_url = credentials.base_url + XERO_PAYROLL_URL
        self.extra_params = {"unitdp": 4} if unit_price_4dps else {}
        self.singular = singular(name)

        for method_name in self.DECORATED_METHODS:
            method = getattr(self, '_%s' % method_name)
            setattr(self, method_name, self._get_data(method))

    def dict_to_xml(self, root_elm, data):
        for key in data.keys():
            # Xero will complain if we send back these fields.
            if key in self.NO_SEND_FIELDS:
                continue

            sub_data = data[key]
            elm = SubElement(root_elm, key)

            # Key references a dict. Unroll the dict
            # as it's own XML node with subnodes
            if isinstance(sub_data, dict):
                self.dict_to_xml(elm, sub_data)

            # Key references a list/tuple
            elif isinstance(sub_data, list) or isinstance(sub_data, tuple):
                # key name is a plural. This means each item
                # in the list needs to be wrapped in an XML
                # node that is a singular version of the list name.
                if isplural(key):
                    for d in sub_data:
                        self.dict_to_xml(SubElement(elm, singular(key)), d)

                # key name isn't a plural. Just insert the content
                # as an XML node with subnodes
                else:
                    for d in sub_data:
                        self.dict_to_xml(elm, d)

            # Normal element - just insert the data.
            else:
                if key in self.BOOLEAN_FIELDS:
                    val = 'true' if sub_data else 'false'
                else:
                    val = six.text_type(sub_data)
                elm.text = val

        return root_elm

    def _prepare_data_for_save(self, data):
        if isinstance(data, list) or isinstance(data, tuple):
            root_elm = Element(self.name)
            for d in data:
                sub_elm = SubElement(root_elm, self.singular)
                self.dict_to_xml(sub_elm, d)
        else:
            root_elm = self.dict_to_xml(Element(self.singular), data)

        return tostring(root_elm)

    def _parse_api_response(self, response, resource_name):
        data = json.loads(response.text, object_hook=json_load_object_hook)
        assert data['Status'] == 'OK', "Expected the API to say OK but received %s" % data['Status']
        return data[resource_name]

    def _get_data(self, func):
        """ This is the decorator for our DECORATED_METHODS.
        Each of the decorated methods must return:
            uri, params, method, body, headers, singleobject
        """
        def wrapper(*args, **kwargs):
            from xero import __version__ as VERSION
            timeout = kwargs.pop('timeout', None)

            uri, params, method, body, headers, singleobject = func(*args, **kwargs)
            cert = getattr(self.credentials, 'client_cert', None)

            if headers is None:
                headers = {}

            # Use the JSON API by default, but remember we might request a PDF (application/pdf)
            # so don't force the Accept header.
            if 'Accept' not in headers:
                headers['Accept'] = 'application/json'

            # Set a user-agent so Xero knows the traffic is coming from pyxero
            headers['User-Agent'] = 'pyxero/%s ' % VERSION + requests.utils.default_user_agent()

            response = getattr(requests, method)(
                    uri, data=body, headers=headers, auth=self.credentials.oauth,
                    params=params, cert=cert, timeout=timeout)

            if response.status_code == 200:
                # If we haven't got XML or JSON, assume we're being returned a binary file
                if not response.headers['content-type'].startswith('application/json'):
                    return response.content

                return self._parse_api_response(response, self.name)

            elif response.status_code == 400:
                raise XeroBadRequest(response)

            elif response.status_code == 401:
                raise XeroUnauthorized(response)

            elif response.status_code == 403:
                raise XeroForbidden(response)

            elif response.status_code == 404:
                raise XeroNotFound(response)

            elif response.status_code == 500:
                raise XeroInternalError(response)

            elif response.status_code == 501:
                raise XeroNotImplemented(response)

            elif response.status_code == 503:
                # Two 503 responses are possible. Rate limit errors
                # return encoded content; offline errors don't.
                # If you parse the response text and there's nothing
                # encoded, it must be a not-available error.
                payload = parse_qs(response.text)
                if payload:
                    raise XeroRateLimitExceeded(response, payload)
                else:
                    raise XeroNotAvailable(response)
            else:
                raise XeroExceptionUnknown(response)

        return wrapper

    def _get(self, id, headers=None):
        uri = '/'.join([self.base_url, self.name, id])
        params = self.extra_params.copy()
        return uri, params, 'get', None, headers, True

    def _get_attachments(self, id):
        """Retrieve a list of attachments associated with this Xero object."""
        uri = '/'.join([self.base_url, self.name, id, 'Attachments']) + '/'
        return uri, {}, 'get', None, None, False

    def _get_attachment_data(self, id, filename):
        """
        Retrieve the contents of a specific attachment (identified by filename).
        """
        uri = '/'.join([self.base_url, self.name, id, 'Attachments', filename])
        return uri, {}, 'get', None, None, False

    def get_attachment(self, id, filename, file):
        """
        Retrieve the contents of a specific attachment (identified by filename).

        Writes data to file object, returns length of data written.
        """
        data = self.get_attachment_data(id, filename)
        file.write(data)
        return len(data)

    def save_or_put(self, data, method='post', headers=None, summarize_errors=True):
        uri = '/'.join([self.base_url, self.name])
        body = {'xml': self._prepare_data_for_save(data)}
        params = self.extra_params.copy()
        if not summarize_errors:
            params['summarizeErrors'] = 'false'
        return uri, params, method, body, headers, False

    def _save(self, data):
        return self.save_or_put(data, method='post')

    def _put(self, data, summarize_errors=True):
        return self.save_or_put(data, method='put', summarize_errors=summarize_errors)

    def _put_attachment_data(self, id, filename, data, content_type, include_online=False):
        """Upload an attachment to the Xero object."""
        uri = '/'.join([self.base_url, self.name, id, 'Attachments', filename])
        params = {'IncludeOnline': 'true'} if include_online else {}
        headers = {'Content-Type': content_type, 'Content-Length': len(data)}
        return uri, params, 'put', data, headers, False

    def put_attachment(self, id, filename, file, content_type, include_online=False):
        """Upload an attachment to the Xero object (from file object)."""
        self.put_attachment_data(id, filename, file.read(), content_type,
                                 include_online=include_online)

    def prepare_filtering_date(self, val):
        if isinstance(val, datetime):
            val = val.strftime('%a, %d %b %Y %H:%M:%S GMT')
        else:
            val = '"%s"' % val
        return {'If-Modified-Since': val}

    def _filter(self, **kwargs):
        params = self.extra_params.copy()
        headers = None
        uri = '/'.join([self.base_url, self.name])

        if kwargs:
            if 'since' in kwargs:
                val = kwargs['since']
                headers = self.prepare_filtering_date(val)
                del kwargs['since']

            def get_filter_params(key, value):
                last_key = key.split('_')[-1]
                if last_key.upper().endswith('ID'):
                    return 'Guid("%s")' % six.text_type(value)
                if key in self.BOOLEAN_FIELDS:
                    return 'true' if value else 'false'
                elif key in self.DATE_FIELDS:
                   return 'DateTime(%s,%s,%s)' % (value.year, value.month, value.day)
                elif key in self.DATETIME_FIELDS:
                    return value.isoformat()
                else:
                    return '"%s"' % six.text_type(value)

            def generate_param(key, value):
                parts = key.split("__")
                field = key.replace('_', '.')
                fmt = '%s==%s'
                if len(parts) == 2:
                    # support filters:
                    # Name__Contains=John becomes Name.Contains("John")
                    if parts[1] in ["contains", "startswith", "endswith"]:
                        field = parts[0]
                        fmt = ''.join(['%s.', parts[1], '(%s)'])
                    elif parts[1] in self.OPERATOR_MAPPINGS:
                        field = parts[0]
                        key = field
                        fmt = '%s' + self.OPERATOR_MAPPINGS[parts[1]] + '%s'
                    elif parts[1] in ["isnull"]:
                        sign = '=' if value else '!'
                        return '%s%s=null' % (parts[0], sign)
                return fmt % (
                    field,
                    get_filter_params(key, value)
                )

            # Move any known parameter names to the query string
            KNOWN_PARAMETERS = ['order', 'offset', 'page']
            for param in KNOWN_PARAMETERS:
                if param in kwargs:
                    params[param] = kwargs.pop(param)

            filter_params = []

            if 'raw' in kwargs:
                raw = kwargs.pop('raw')
                filter_params.append(raw)

            # Treat any remaining arguments as filter predicates
            # Xero will break if you search without a check for null in the first position:
            # http://developer.xero.com/documentation/getting-started/http-requests-and-responses/#title3
            sortedkwargs = sorted(six.iteritems(kwargs),
                key=lambda item: -1 if 'isnull' in item[0] else 0)
            for key, value in sortedkwargs:
                filter_params.append(generate_param(key, value))

            if filter_params:
                params['where'] = '&&'.join(filter_params)

        return uri, params, 'get', None, headers, False

    def _all(self):
        uri = '/'.join([self.base_url, self.name])
        return uri, {}, 'get', None, None, False

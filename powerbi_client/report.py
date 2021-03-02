#!/usr/bin/env python
# coding: utf-8

# Copyright (c) Microsoft.

"""
TODO: Add module docstring
"""

import time
import requests

from IPython import get_ipython
from ipywidgets import DOMWidget
from jupyter_ui_poll import ui_events
from traitlets import Bool, Dict, Float, Unicode, List, observe

from ._frontend import module_name, module_version

from .authentication import DeviceCodeLoginAuthentication

class Report(DOMWidget):
    """PowerBI report embedding widget"""

    # Name of the widget view class in front-end
    _view_name = Unicode('ReportView').tag(sync=True)

    # Name of the widget model class in front-end
    _model_name = Unicode('ReportModel').tag(sync=True)

    # Name of the front-end module containing widget view
    _view_module = Unicode('powerbi-client-frontend').tag(sync=True)

    # Name of the front-end module containing widget model
    _model_module = Unicode('powerbi-client-frontend').tag(sync=True)

    # Version of the front-end module containing widget view
    _view_module_version = Unicode('^0.1.0').tag(sync=True)

    # Version of the front-end module containing widget model
    _model_module_version = Unicode('^0.1.0').tag(sync=True)

    # Default values for widget traits
    VISUAL_DATA_DEFAULT_STATE = ''
    EXPORT_VISUAL_DATA_REQUEST_DEFAULT_STATE = {}
    REGISTERED_EVENT_HANDLERS_DEFAULT_STATE = {}
    EVENT_DATA_DEFAULT_STATE = {
        'event_name': None,
        'event_details': None
    }
    REPORT_FILTER_REQUEST_DEFAULT_STATE = {
        'filters': [],
        'request_completed': True
    }
    GET_PAGES_REQUEST_DEFAULT_STATE = False
    REPORT_PAGES_DEFAULT_STATE = []
    GET_VISUALS_DEFAULT_PAGE_NAME = ''
    PAGE_VISUALS_DEFAULT_STATE = []
    GET_BOOKMARKS_REQUEST_DEFAULT_STATE = False
    REPORT_BOOKMARKS_DEFAULT_STATE = []
    REPORT_BOOKMARK_DEFAULT_NAME = ''
    TOKEN_EXPIRED_DEFAULT_STATE = False

    # Other constants
    REPORT_NOT_EMBEDDED_MESSAGE = "Power BI report is not embedded"

    # Process upto n UI events per iteration
    PROCESS_EVENTS_ITERATION = 3

    # Check for UI every n seconds
    POLLING_INTERVAL = 0.5

    # Authentication object
    _auth = None

    # Widget specific properties.
    # Widget properties are defined as traitlets. Any property tagged with `sync=True`
    # is automatically synced to the frontend *any* time it changes in Python.
    # It is synced back to Python from the frontend *any* time the model is touched in frontend.

    # TODO: Add trait validation
    _embed_config = Dict(None).tag(sync=True)
    _embedded = Bool(False).tag(sync=True)

    container_height = Float(0).tag(sync=True)
    container_width = Float(0).tag(sync=True)

    # TODO: Add trait validation
    # TODO: Start with _
    export_visual_data_request = Dict(None).tag(sync=True)
    # TODO: Start with _
    visual_data = Unicode(VISUAL_DATA_DEFAULT_STATE).tag(sync=True)

    _event_data = Dict(EVENT_DATA_DEFAULT_STATE).tag(sync=True)

    # TODO: Add trait validation
    _report_filters_request = Dict(REPORT_FILTER_REQUEST_DEFAULT_STATE).tag(sync=True)

    _get_pages_request = Bool(GET_PAGES_REQUEST_DEFAULT_STATE).tag(sync=True)
    _report_pages = List(REPORT_PAGES_DEFAULT_STATE).tag(sync=True)

    _get_visuals_page_name = Unicode(GET_VISUALS_DEFAULT_PAGE_NAME).tag(sync=True)
    _page_visuals = List(PAGE_VISUALS_DEFAULT_STATE).tag(sync=True)

    _report_bookmark_name = Unicode(REPORT_BOOKMARK_DEFAULT_NAME).tag(sync=True)

    _report_bookmarks = List(REPORT_BOOKMARKS_DEFAULT_STATE).tag(sync=True)
    _get_bookmarks_request = Bool(GET_BOOKMARKS_REQUEST_DEFAULT_STATE).tag(sync=True)

    _token_expired = Bool(TOKEN_EXPIRED_DEFAULT_STATE).tag(sync=True)

    # Methods
    def __init__(self, access_token=None, token_type=0, embed_url=None, group_id=None, report_id=None, auth=None, **kwargs):

        token_expiration = 0
        try:
            # Get access token for the report using authentication
            if not access_token:
                if not auth:
                    if not Report._auth:

                        # Set DeviceCodeLoginAuthentication to be the default global authentication method
                        Report._auth = DeviceCodeLoginAuthentication()
                    auth = Report._auth
                self._auth = auth
                access_token = self._auth.get_access_token()
                token_type = 0
                token_expiration = self._auth.get_access_token_details().get('id_token_claims').get('exp')

            # Get embed URL for the report using access token
            if not embed_url:
                if not group_id or not report_id:
                    raise Exception("Group Id and Report Id are required")
                if token_type == 1:
                    raise Exception("Cannot get embed URL using embed token")

                request_url = "https://api.powerbi.com/v1.0/myorg/groups/" + group_id + "/reports/" + report_id
                response = requests.get(request_url, headers={'Authorization': 'Bearer ' + access_token})
                embed_url = response.json()['embedUrl']
        except:
            raise Exception("Could not create Access token or Embed URL")

        # Tells if Power BI events are being observed
        self._observing_events = False

        # Registered Power BI event handlers methods
        self._registered_event_handlers = dict(
            self.REGISTERED_EVENT_HANDLERS_DEFAULT_STATE)

        self._set_embed_config(access_token, embed_url, token_type, token_expiration)
        self.observe(self._update_access_token, '_token_expired')

        # Init parent class DOMWidget
        super(Report, self).__init__(**kwargs)

    def _update_access_token(self, change):
        if change.new == True:
            if not self._auth:
                raise Exception("Authentication context not found")
            self._auth.refresh_token()
            self._set_embed_config(self._auth.get_access_token(), self._embed_config['embedUrl'], self._embed_config['tokenType'], self._auth.get_access_token_details().get('id_token_claims').get('exp'))
            self._token_expired = bool(self.TOKEN_EXPIRED_DEFAULT_STATE)

    def set_access_token(self, access_token):
        """Set access token for Power BI report

        Args:
            access_token (string): report access token
        """
        self._set_embed_config(access_token=access_token, embed_url=self._embed_config['embedUrl'], token_type=self._embed_config['tokenType'])

    def _set_embed_config(self, access_token, embed_url, token_type=0, token_expiration=0):
        """
        TODO: Add docstring
        """
        self._embed_config = {
            'type': 'report',
            'accessToken': access_token,
            'embedUrl': embed_url,
            'tokenType': token_type,
            'tokenExpiration': token_expiration
        }
        self._embedded = False

    def set_dimensions(self, container_height, container_width):
        """Set width and height of Power BI report in px

        Args:
            container_height (number): report height
            container_width (number): report width
        """
        self.container_height = container_height
        self.container_width = container_width

    def export_visual_data(self, page_name, visual_name, rows=10, underlying_data=False):
        """Returns the data of given visual of the embedded Power BI report

        Args:
            page_name (string): Page name of the embedded report
            visual_name (string): Visual's unique name 
            rows (int, optional): Number of rows of data. Defaults to 10
            underlying_data (boolean, optional): Choice to show the underlying data or not. Default is False.

        Returns:
            string: visual's exported data
        """
        if self._embedded == False:
            raise Exception(self.REPORT_NOT_EMBEDDED_MESSAGE)

        # Start exporting data on client side
        self.export_visual_data_request = {
            'pageName': page_name,
            'visualName': visual_name,
            'rows': rows,
            'underlyingData': underlying_data
        }

        # Check if ipython kernel is available
        if get_ipython():
            # Wait for client-side to send visual data
            with ui_events() as ui_poll:
                # While visual data is not received
                while self.visual_data == self.VISUAL_DATA_DEFAULT_STATE:
                    ui_poll(self.PROCESS_EVENTS_ITERATION)
                    time.sleep(self.POLLING_INTERVAL)

        exported_data = self.visual_data

        # Reset the export_visual_data_request and visual_data's value
        self.export_visual_data_request = dict(self.EXPORT_VISUAL_DATA_REQUEST_DEFAULT_STATE)
        self.visual_data = self.VISUAL_DATA_DEFAULT_STATE

        return exported_data

    def on(self, event, callback):
        """Register a callback to execute when the report emits the target event
        Parameters

        Args:
            event (string): Name of Power BI event (eg. 'loaded', 'rendered', 'error')
            callback (function): User defined function. Callback function is invoked with event details as parameter
        """
        # TODO: Value of event should be from one of the Report.allowedEvents array
        self._registered_event_handlers[event] = callback

        def get_event_data(change):

            event_data = change.new
            event_name = event_data['event_name']
            event_details = event_data['event_details']

            # Do not invoke callback when _event_data trait is reset
            if event_name is None:
                return

            # Check if a handler is registered for the current event
            if event_name not in self._registered_event_handlers:
                return

            event_handler = self._registered_event_handlers[event_name]
            event_handler(event_details)

            # Reset the _event_data trait, so as to receive next event
            self._event_data = dict(self.EVENT_DATA_DEFAULT_STATE)

        # Check if already observing events
        if not self._observing_events:

            # Prevents calling DOMWidget.observe() again
            self._observing_events = True

            # Start observing Power BI events
            self.observe(get_event_data, '_event_data')

    def update_filters(self, filters):
        """Set report level filters in the embedded report.
            Currently supports models.FiltersOperations.Add

        Args:
            filters ([models.ReportLevelFilters]): List of report level filters

        Raises:
            Exception: When report is not embedded
        """
        if self._embedded == False:
            raise Exception(self.REPORT_NOT_EMBEDDED_MESSAGE)

        self._report_filters_request = {
            'filters': filters,
            'request_completed': False
        }

        # TODO: Should we wait for the filters to be applied

    def remove_filters(self):
        """Remove all report level filters from the embedded report

        Raises:
            Exception: When report is not embedded
        """
        self.update_filters([])

    def get_pages(self):
        """Returns the list of pages of the embedded Power BI report

        Returns:
            string: list of pages
        """
        if self._embedded == False:
            raise Exception(self.REPORT_NOT_EMBEDDED_MESSAGE)

        # Start getting pages on client side
        self._get_pages_request = True

        # Check if ipython kernel is available
        if get_ipython():
            # Wait for client-side to send list of pages
            with ui_events() as ui_poll:
                # While list of report pages is not received
                while self._report_pages == self.REPORT_PAGES_DEFAULT_STATE:
                    ui_poll(self.PROCESS_EVENTS_ITERATION)
                    time.sleep(self.POLLING_INTERVAL)

        pages = self._report_pages

        # Reset the get_pages_request and report_pages's value
        self._get_pages_request = bool(self.GET_PAGES_REQUEST_DEFAULT_STATE)
        self._report_pages = list(self.REPORT_PAGES_DEFAULT_STATE)

        return pages

    def visuals_on_page(self, page_name):
        """Returns the list of visuals of the given page of the embedded Power BI report

        Args:
            page_name (string): Page name of the embedded report

        Returns:
            string: list of visuals
        """
        if self._embedded == False:
            raise Exception(self.REPORT_NOT_EMBEDDED_MESSAGE)

        # Start getting visuals on client side
        self._get_visuals_page_name = page_name

        # Check if ipython kernel is available
        if get_ipython():
            # Wait for client-side to send list of visuals
            with ui_events() as ui_poll:
                # While list of visuals is not received
                while self._page_visuals == self.PAGE_VISUALS_DEFAULT_STATE:
                    ui_poll(self.PROCESS_EVENTS_ITERATION)
                    time.sleep(self.POLLING_INTERVAL)

        visuals = self._page_visuals

        # Reset the get_visuals_page_name and page_visuals's value
        self._get_visuals_page_name = self.GET_VISUALS_DEFAULT_PAGE_NAME
        self._page_visuals = list(self.PAGE_VISUALS_DEFAULT_STATE)

        return visuals

    def set_bookmark(self, bookmark_name):
        """Applies a bookmark by name on the embedded report.

        Args:
            bookmark_name (string) : Bookmark Name
        Raises:
            Exception: When report is not embedded
        """

        if self._embedded == False:
            raise Exception(self.REPORT_NOT_EMBEDDED_MESSAGE)

        self._report_bookmark_name = bookmark_name

    def get_bookmarks(self):
        """Returns the list of bookmarks of the embedded Power BI report

        Returns:
            list: list of bookmarks

        Raises:
            Exception: When report is not embedded
        """

        if self._embedded == False:
            raise Exception(self.REPORT_NOT_EMBEDDED_MESSAGE)

        # Start getting bookmarks on client side
        self._get_bookmarks_request = True

        # Check if ipython kernel is available
        if get_ipython():
            # Wait for client-side to send list of bookmarks
            with ui_events() as ui_poll:
                # While list of report bookmark(s) is not received
                while self._report_bookmarks == self.REPORT_BOOKMARKS_DEFAULT_STATE:
                    ui_poll(self.PROCESS_EVENTS_ITERATION)
                    time.sleep(self.POLLING_INTERVAL)

        bookmarks = self._report_bookmarks

        if bookmarks == ['']:
            bookmarks = self.REPORT_BOOKMARKS_DEFAULT_STATE

        # Reset the _get_bookmarks_request and _report_bookmarks values
        self._get_bookmarks_request = bool(self.GET_BOOKMARKS_REQUEST_DEFAULT_STATE)
        self._report_bookmarks = list(self.REPORT_BOOKMARKS_DEFAULT_STATE)

        return bookmarks

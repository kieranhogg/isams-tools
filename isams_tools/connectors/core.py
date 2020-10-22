import logging

from isams_tools.connectors.isams import iSAMSConnection
from isams_tools.connectors.isams_api import iSAMSJSONConnection, iSAMSXMLConnection
from settings import CONNECTION_METHOD, DATABASE_SERVER, DATABASE, DATABASE_USER, DATABASE_PASSWORD

logger = logging.getLogger('root')

class ConnectionManager:
    """Helper class to abstract away the choice of connection"""
    connection = None
    type = None

    def connect(self, connection=None):
        """Creates a suitable connection depending on settings
        :return: the connection object
        """
        if not connection:
            method = CONNECTION_METHOD
        else:
            method = connection['type']

        logger.debug("ConnectionManager.connect() using {0}".format(method))

        # FIXME: standardise the type
        if method in ['JSON', 'iSAMS_JSON']:
            self.connection = iSAMSJSONConnection()
            self.type = 'JSON'
        elif method in ['XML', 'iSAMS_XML']:
            self.connection = iSAMSXMLConnection()
            self.type = 'XML'
        elif method in ['MSSQL', 'iSAMS']:
            if not connection:
                self.connection = iSAMSConnection(DATABASE_SERVER, DATABASE_USER, DATABASE_PASS,
                                                  DATABASE)
            else:
                self.connection = iSAMSConnection(connection['server'], connection['user'], connection['password'],
                                                  connection['database'])

            self.type = 'MSSQL'
        else:
            exit("Connection method not supported")

        self.connection.connect()
        return self.connection

from twisted.internet import protocol
import service, client
from twisted.python import log


class BaseServerFactory(protocol.ServerFactory):
    def __init__(self, seperator='.', timeout=None, encoder=None):
        self.service = service.JSONRPCService(timeout, encoder=encoder)
        self.seperator = seperator

    def buildProtocol(self, addr):
        log.msg("client connected", addr)
        return self.protocol(self.service)

    def addHandler(self, handler, namespace=None):
        handler.addToService(self.service, namespace=namespace, seperator=self.seperator)


class BaseClientFactory(protocol.ClientFactory):
    pass

from twisted.internet import defer
from twisted.protocols.basic import NetstringReceiver
from twisted.python import failure, log
from txjason import protocol, client


class JSONRPCClientProtocol(NetstringReceiver):
    """
    A JSON RPC Client Protocol for TCP/Netstring connections.
    """
    def __init__(self, factory):
        self.factory = factory
        self.deferred = defer.Deferred()

    def stringReceived(self, string):
        try:
            self.factory.client.handleResponse(string)
        except client.JSONRPCProtocolError:
            log.err()
            self.transport.loseConnection()
        except:
            log.err()

    def connectionLost(self, reason):
        if self.brokenPeer:
            log.msg('Disconencted from server because of a broken peer.')
        else:
            log.msg('Lost server connection.')

        self.deferred.errback(reason)

    def disconnect(self):
        self.transport.loseConnection()
        return self.deferred



class JSONRPCServerProtocol(NetstringReceiver):
    """
    A JSON RPC Server Protocol for TCP/Netstring connections.
    """
    def __init__(self, service):
        self.service = service

    @defer.inlineCallbacks
    def stringReceived(self, string):
        result = yield self.service.call(string)
        if result is not None:
            self.sendString(result)


class JSONRPCClientFactory(protocol.BaseClientFactory):
    def __init__(self, endpoint, timeout=5, reactor=None):
        if reactor is None:
            from twisted.internet import reactor
        self.client = client.JSONRPCClient(timeout=timeout, reactor=reactor)
        self.endpoint = endpoint
        self._proto = None
        self._waiting = []
        self._notifyOnDisconnect = []
        self._connecting = False
        self._connectionDeferred = None
        self.reactor = reactor
        self.disconnecting = False

    def buildProtocol(self, addr):
        return JSONRPCClientProtocol(self)

    def _cancel(self, d):
        if self._connectionDeferred is not None:
            self._connectionDeferred.cancel()

    def _getConnection(self):
        if self._proto is not None:
            return defer.succeed(self._proto)
        d = defer.Deferred(self._cancel)
        self._waiting.append(d)
        if not self._connecting:
            self._connecting = True
            self._connectionDeferred = (
                self.endpoint.connect(self)
                .addBoth(self._gotResult)
                .addErrback(log.err, 'error connecting %r' % (self,)))
        return d

    def _gotResult(self, result):
        self._connecting = False
        if not isinstance(result, failure.Failure):
            self._proto = result
            self._proto.deferred.addBoth(self._lostProtocol)
        waiting, self._waiting = self._waiting, []
        for d in waiting:
            d.callback(result)
        return result

    def _lostProtocol(self, reason):
        if not self.disconnecting:
            log.err(reason, '%r disconnected' % (self,))
        deferreds, self._notifyOnDisconnect = self._notifyOnDisconnect, []
        for d in deferreds:
            d.errback(reason)
        self._proto = None
        self.client.cancelRequests()
        o = self.disconnecting
        self.disconnecting = False
        if o:
            return None
        else:
            return reason


    def clientConnectionFailed(self, connector, reason):
        self.connected = False
        self.closing = False
        self.reactor.connectTCP(self.host, self.port, self)

    @defer.inlineCallbacks
    def callRemote(self, __method, *args, **kwargs):
        connectionDeferred = self._getConnection()

        def gotConnection(connection):
            payload, requestDeferred = self.client.getRequest(
                __method, *args, **kwargs)
            connection.sendString(payload)
            return requestDeferred

        connectionDeferred.addCallback(gotConnection)
        return connectionDeferred

    def notifyRemote(self, __method, *args, **kwargs):
        connectionDeferred = self._getConnection()

        def gotConnection(connection):
            payload = self.client.getNotification(__method, *args, **kwargs)
            connection.sendString(payload)

        connectionDeferred.addCallback(gotConnection)
        return connectionDeferred

    def connect(self):
        return self._getConnection().addCallback(lambda ign: None)

    def disconnect(self):
        self.disconnecting = False
        if self._proto:
            return self._proto.disconnect()
        elif self._connecting:
            return self._connectionDeferred.cancel()

    def notifyDisconnect(self):
        d = defer.Deferred()
        self._notifyOnDisconnect.append(d)
        return d


class JSONRPCServerFactory(protocol.BaseServerFactory):
    protocol = JSONRPCServerProtocol

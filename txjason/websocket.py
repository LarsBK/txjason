from twisted.internet import defer
from twisted.python import failure, log
from txjason import protocol, client
from autobahn.twisted.websocket import WebSocketServerProtocol, WebSocketServerFactory

class JSONRPCServerFactoryWS(WebSocketServerFactory):
	
	def buildProtocol(self, addr):
		log.msg("WS connection", addr)
		p = JSONRPCServerProtocolWS(self.service)
		p.factory = self
		return p

	def setService(self, ser):
		self.service = ser

class JSONRPCServerProtocolWS(WebSocketServerProtocol):

	def __init__(self, service):
		self.service = service

	@defer.inlineCallbacks
	def onMessage(self, payload, isBinary):
		log.msg("Message", isBinary, payload)
		if isBinary:
			self.transport.loseConnection()
		result = yield self.service.call(payload)
		log.msg("ResultWS", result)
		if result is not None:
			self.sendMessage(result)

	def onConnect(self, request):
		log.msg("connected")
		log.msg("request", request)
		return None
	

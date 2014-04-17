from handler import Handler, exportRPC
import inspect

pythonTypeToJson = {
        basestring : "string",
        int : "integer",
        float : "float",
        list : "list",
        dict : "object"
}

class IntrospectionHandler(Handler):

    def __init__(self, service):
        self.service = service

    @exportRPC()
    def listMethods(self):
        """
        Return a list of the names of all rpc methods.
        """
        return self.service.method_data.keys()

    @exportRPC(types=[basestring])
    def methodSignature(self ,fName):
        """
        Return the signature of the method with the given name.
        """
        try:
            func = self.service.method_data[fName]
        except KeyError:
            raise MethodNotFoundError()
        try:
            try:
                types = {}
                for k,v in self.service.method_data[fName]["types"].iteritems():
                    types[k] = pythonTypeToJson[v]
            except AttributeError:
                types = [ pythonTypeToJson[x] for x in self.service.method_data[fName]["types"]]
        except KeyError:
            return None
        try:
            required = self.service.method_data[fName]["required"]
        except KeyError:
            return { "types": types}
        return { "types": types, "required" : required}


    @exportRPC(types=[basestring])
    def methodHelp(self, fName):
        """
        Return a human readable description of the method given.
        """
        try:
            func = self.service.method_data[fName]
            return inspect.getdoc(func["method"])
        except KeyError:
            raise MethodNotFoundError()
            

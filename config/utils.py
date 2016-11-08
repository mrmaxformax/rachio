import logging


class JsonObject:
    def __init__(self, js):
        self.__dict__ = js


class Asserters:
    logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)

    def __init__(self, response_json):
        self.response_object = JsonObject(response_json)

    def get_value(self, field):
        obj = eval("self.response_object." + field)
        tp = type(obj)
        return obj, tp

    def asserter(self, type, target_json):
        errors = 0

        for field in target_json:
            obj, tp = self.get_value(field)

            if type == 'type':
                if tp.__name__ != target_json[field]:
                    logging.warning("ERROR! The field '%s' - expected %s type, was %s" % (field, target_json[field], tp))
                    errors += 1

            if type == 'value':

                if obj == True:
                    obj = 'True'
                if obj == False:
                    obj = 'False'

                if obj != target_json[field]:
                    logging.warning("ERROR! The field '%s' - is expected %s value but was %s" % (field, target_json[field], obj))
                    errors += 1

        if errors != 0:
            print("Number of errors:", errors)
            return False
        return True

import argparse
import requests
import json
from config import config
from config.utils import *
from queue import Queue

tasks = Queue()
logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)


def get_testrun():
    '''
    The method reads command line arguments
    --input (str): the name of json file with test run parameters
    :return: test run file name
    '''
    try:
        get_parser = argparse.ArgumentParser()
        get_parser.add_argument('--input', help='testcase json file as input')
        testrun_file = get_parser.parse_args().input
        if testrun_file is None:
            logging.info("Please enter Test Suite name")
            exit()
        return testrun_file
    except Exception as e:
        logging.error(e)
        exit()


def check_connection(url):
    '''
    The method checked if we have connection to our API. Can be change to 'ping'
    :param url: url which should be used to check the connection
    :return: True if connection is ok or Exception if not
    Todo:
        We should have api health checkers for each services and run it before each test case
        And add "ping" to check if we have our connection or not.
        Example: ping
    '''
    try:
        logging.info("Checking Internet connection")
        requests.get(url, timeout=5)
        logging.info("Internet connection is checked: OK")
        return True
    except requests.exceptions.RequestException as e:
        logging.warning("There is a problem with Internet connection. Test will Abort")
        logging.error(e)
        exit(1)


def read_json(file_name, test_folder = ''):
    '''
    Reads file and convert it into json
    :param file_name: the path to file
    :return: json
    '''
    try:
        path = config.TESTS_DIR + "/" + test_folder + file_name + ".json"
        conf_file = open(path).read()
        json_file = json.loads(conf_file)
        return json_file
    except Exception as e:
        logging.warning("There is a problem with reading json file. Test will Abort")
        logging.error(e)
        exit(1)


def rest_request(testrun, request=None, device_id=None):
    '''
    Send request to URL
    :param testrun: json object with test run data
    :param request: json object with request data. We take it from files with test cases or from test run file
    :param device_id: device id. We get it from request to 'public/person/info'
    :return: API response object
    '''
    domain = '%s://%s' % (config.PROTOCOL, config.DOMAIN)
    device_id = '' if device_id is None else device_id

    if request is None:
        end_point = testrun.global_endPoint
        method = testrun.global_method
        header = testrun.global_headers
        payload = {}
    else:
        end_point = request.endPoint if hasattr(request, 'endPoint') else testrun.endPoint
        payload = request.payload if hasattr(request, 'payload') else {}
        method = request.method if hasattr(request, 'method') else testrun.global_method

        if hasattr(request, 'headers'):
            for k in testrun.global_headers:
                if k not in request.headers:
                    request.headers[k] = testrun.global_headers[k]
            header = request.headers
        else:
            header = testrun.global_headers

    required_url = domain + end_point + device_id
    # payload = json.dumps(request['payload'])
    querystring = {}
    logging.info("Sending %s request to %s" % (method, required_url))
    response = requests.request(method, required_url, data=payload, headers=header, params=querystring)
    return response


def get_device_id(testrun):
    '''
    This method returns Device ID
    :param testrun: we use global_endPoint value as a basic endPoint to get id
    :return: device ID if response = '200' or '' if not '200'
    '''
    logging.info('Getting device ID')
    device_id = None
    request_id = rest_request(testrun)
    if request_id.status_code == 200:
        device_id = json.loads(request_id.content.decode("utf-8"))
        device_id = device_id['id']
        logging.info("Device ID: %s" % device_id)
        return device_id
    else:
        logging.warning("ERROR: Can't get device ID. Server returns %s status code." % request_id.status_code)
        return device_id


def complete_task(testrun, test):
    '''
    This method runs all requests in Test step by step and validate response
    :param testrun: test run jsonObject
    :param test: test case jsonObject
    :return: True if test pass and False if faild
    '''

    try:
        for i, request in enumerate(test.request):
            req = JsonObject(request)
            device_id = req.deviceId if hasattr(req, "deviceId") else get_device_id(testrun)
            resp = JsonObject(req.response)
            rest = rest_request(testrun, req, device_id)
            if rest.status_code != resp.status_code:
                logging.error("Test casefailed! The expected status code is %s. The actual is %s." % (resp.status_code, rest.status_code))
                return False
            else:
                logging.info("We get expected Status code: %s" % rest.status_code)

                if hasattr(resp, "type"):
                    content = json.loads(rest.content.decode("utf-8"))
                    a = Asserters(content)
                    if not a.asserter("type", resp.type):
                        return False

                if hasattr(resp, "value"):
                    content = json.loads(rest.content.decode("utf-8"))
                    a = Asserters(content)
                    if not a.asserter("value", resp.value):
                        return False

                # if hasattr(resp, "header"):
                    #   pass

    except Exception as e:
        print(e)
        return False
    return True

def worker():
    testrun = JsonObject(read_json(get_testrun()))
    print('========================================================================')
    logging.info('STARTING NEW TEST RUN: %s' % testrun.testrun_name)
    print('========================================================================')
    check_connection(config.PROTOCOL + '://' + config.DOMAIN)
    print('')

    logging.info('Adding test cases into Queue')
    for i in range(len(testrun.testcases)):
        tasks.put(testrun.testcases[i])
    logging.info('%s Test Cases were added\n' % tasks.qsize())

    while not tasks.empty():
        test = JsonObject(read_json(tasks.get(),testrun.testfolder))
        print('========================================================================')
        logging.info('STARTING TEST: %s' % test.name)

        if complete_task(testrun, test) is False:
            logging.error("Test case failed!")
            return

        logging.info('Test Success!')
        print('========================================================================\n')


if __name__ == '__main__':
    worker()

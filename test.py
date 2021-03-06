#!/usr/bin/env python
#
# Copyright 2016 Feei. All Rights Reserved
#
# Author:   Feei <wufeifei@wufeifei.com>
# Homepage: https://github.com/wufeifei/cobra
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See the file 'doc/COPYING' for copying permission
#

import unittest
import requests
from utils import common, config
import json


class Test(unittest.TestCase):
    domain = '{0}:{1}'.format(config.Config('cobra', 'host').value, config.Config('cobra', 'port').value)
    api = 'http://' + domain + '/api/{0}'
    headers = {"Content-Type": "application/json"}

    key = common.md5('CobraAuthKey')
    target = 'https://github.com/wufeifei/dict.git'
    branch = 'master'

    def test_api(self):
        """
        Cobra API Test
        :return:
        """
        payload = json.dumps({
            "key": self.key,
            "target": self.target,
            "branch": self.branch
        })

        try:
            response = requests.post(self.api.format('add'), data=payload, headers=self.headers)
            response_json = response.json()
            code = response_json.get('code')
            self.assertEqual(code, 1001)
            result = response_json.get('result')
            scan_id = result.get('scan_id')
            print("API Add: {0}".format(result))
            status_query = json.dumps({
                'key': self.key,
                'scan_id': scan_id
            })
            status_response = requests.post(self.api.format('status'), data=status_query, headers=self.headers)
            status_response_json = status_response.json()
            code = status_response_json.get('status')
            result = status_response_json.get('result')
            print("API Status: {0}".format(result))
            self.assertEqual(code, 1001)
        except (requests.ConnectionError, requests.HTTPError) as e:
            self.fail("API Add failed: {0}".format(e))


if __name__ == '__main__':
    unittest.main()

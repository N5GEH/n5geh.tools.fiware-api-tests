"""
Tests for mqtt notification based on
1. https://fiware-orion.readthedocs.io/en/master/orion-api.html#custom-notifications
2. https://fiware-orion.readthedocs.io/en/master/user/mqtt_notifications.html

"""
from filip.models.ngsi_v2.subscriptions import Subscription
import time
import unittest
import json
from functools import wraps
from typing import Callable
from paho.mqtt.client import Client
from filip.clients.ngsi_v2 import ContextBrokerClient
from filip.models import FiwareHeader
from filip.models.ngsi_v2.context import ContextEntity
from filip.utils.cleanup import clear_all
from settings import settings
import requests


topic_default = "default/mqtt/notification"
topic_auth = "default/mqtt/notification/auth"
topic_payload = "custom/mqtt/notification/payload"
topic_json = "custom/mqtt/notification/json"
topic_ngsi = "custom/mqtt/notification/ngsi"
topic_dynamic = "custom/mqtt/notification/dynamic"
topics = [topic_default, topic_auth, topic_payload, topic_json, topic_ngsi, topic_dynamic]

standard_entity = {
    "id": "Entity:001",
    "type": "Entity",
    "attribute1": {
        "type": "Number",
        "value": 1
    },
    "attribute2": {
        "type": "Number",
        "value": 2
    }
}


def standard_test(
                  fiware_service: str,
                  fiware_servicepath: str,
                  cb_url: str = None,
                  ) -> Callable:
    # clean up
    fiware_header = FiwareHeader(service=fiware_service,
                                 service_path=fiware_servicepath)
    clear_all(fiware_header=fiware_header,
              cb_url=cb_url)

    # initial entity
    entity = ContextEntity(**standard_entity)
    with ContextBrokerClient(url=cb_url, fiware_header=fiware_header) as cbc:
        cbc.post_entity(entity=entity)

    # wrapper
    def decorator(func):
        #  Wrapper function for the decorated function
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        return wrapper

    return decorator


class TestDataModel(unittest.TestCase):

    def setUp(self) -> None:
        self.fiware_header = FiwareHeader(
            service=settings.FIWARE_SERVICE,
            service_path=settings.FIWARE_SERVICEPATH,
        )

        # Initial client
        self.cb_client = ContextBrokerClient(url=settings.CB_URL,
                                             fiware_header=self.fiware_header)

    @staticmethod
    def mqtt_setup(host, port, topic,
                   username=None, password=None,
                   tls: bool = False):
        sub_res = {
            "topic": None,
            "payload": None
        }

        def on_message(client, userdata, msg):
            nonlocal sub_res
            sub_res["payload"] = msg.payload
            sub_res["topic"] = msg.topic

        mqttc = Client()
        mqttc.on_message = on_message
        if username:
            mqttc.username_pw_set(username=username, password=password)
        else:
            mqttc.username_pw_set(username=settings.MQTT_USERNAME,
                                  password=settings.MQTT_PASSWORD)
        if tls:
            mqttc.tls_set()
        mqttc.connect(host=host,
                      port=port)
        mqttc.subscribe(topic=topic)
        mqttc.loop_start()
        return sub_res, mqttc

    @standard_test(
        fiware_service=settings.FIWARE_SERVICE,
        fiware_servicepath=settings.FIWARE_SERVICEPATH,
        cb_url=settings.CB_URL
    )
    def test_default_notification(self):
        # post notification
        notification_default_mqtt = {
          "description": "MQTT Command notification",
          "subject": {
            "entities": [
              {
                "id": standard_entity["id"]
              }
            ],
            "condition": {
                "attrs": ["attribute1"]
            }
          },
          "notification": {
            "mqtt": {
              "url": settings.MQTT_BROKER_URL_INTERNAL,
              "topic": topic_default
            }
          },
          "throttling": 0
        }
        if settings.MQTT_USERNAME:
            notification_default_mqtt["notification"][
                "mqtt"]["user"] = settings.MQTT_USERNAME
            notification_default_mqtt["notification"][
                "mqtt"]["passwd"] = settings.MQTT_PASSWORD
        self.cb_client.post_subscription(subscription=Subscription(
            **notification_default_mqtt))

        # update value
        # self.mqtt_start()
        sub_res, mqttc = self.mqtt_setup(host=settings.MQTT_BROKER_URL.host,
                                         port=settings.MQTT_BROKER_URL.port,
                                         topic=topic_default,
                                         tls=settings.MQTT_TLS
                                         )
        time.sleep(3)

        self.cb_client.update_attribute_value(entity_id=standard_entity["id"],
                                              attr_name="attribute1", value=101)
        time.sleep(3)

        # check value
        self.assertEqual(sub_res["topic"], topic_default)
        expected_payload = json.loads(sub_res["payload"].decode())
        self.assertEqual(expected_payload["data"][0]["attribute1"]["value"], 101)
        mqttc.loop_stop()
        mqttc.disconnect()

    @standard_test(
        fiware_service=settings.FIWARE_SERVICE,
        fiware_servicepath=settings.FIWARE_SERVICEPATH,
        cb_url=settings.CB_URL
    )
    def test_default_notification_auth(self):
        # post notification
        notification_auth_mqtt = {
          "description": "MQTT Command notification",
          "subject": {
            "entities": [
              {
                "id": standard_entity["id"]
              }
            ],
            "condition": {
                "attrs": ["attribute1"]
            }
          },
          "notification": {
            "mqtt": {
                "url": "mqtt://test.mosquitto.org:1884",
                "topic": topic_auth,
                "user": "rw",
                "passwd": "readwrite"  # https://test.mosquitto.org/
            }
          },
          "throttling": 0
        }
        self.cb_client.post_subscription(subscription=Subscription(
            **notification_auth_mqtt))

        # update value
        sub_res, mqttc = self.mqtt_setup(host="test.mosquitto.org",
                                         port=1884,
                                         topic=topic_auth,
                                         username="rw",
                                         password="readwrite",
                                         tls=False)
        time.sleep(3)
        self.cb_client.update_attribute_value(entity_id=standard_entity["id"],
                                              attr_name="attribute1", value=102)
        time.sleep(3)

        # check value
        self.assertEqual(sub_res["topic"], topic_auth)
        expected_payload = json.loads(sub_res["payload"].decode())
        self.assertEqual(expected_payload["data"][0]["attribute1"]["value"], 102)
        mqttc.loop_stop()
        mqttc.disconnect()

# test custom notification with payload
# topic = "custom/mqtt/notification/payload"
# "payload": "attribute1: ${attribute1}"
    @standard_test(
        fiware_service=settings.FIWARE_SERVICE,
        fiware_servicepath=settings.FIWARE_SERVICEPATH,
        cb_url=settings.CB_URL
    )
    def test_custom_notification_payload(self):
        # post notification
        notification_custom_mqtt = {
          "description": "MQTT Command notification",
          "subject": {
            "entities": [
              {
                "id": standard_entity["id"]
              }
            ],
            "condition": {
                "attrs": ["attribute1"]
            }
          },
          "notification": {
            "mqttCustom": {
              "url": settings.MQTT_BROKER_URL_INTERNAL,
              "topic": topic_payload,
              "payload": "attribute1: ${attribute1}"
            }
          },
          "throttling": 0
        }
        self.cb_client.post_subscription(subscription=Subscription(
            **notification_custom_mqtt))

        # update value
        sub_res, mqttc = self.mqtt_setup(host=settings.MQTT_BROKER_URL.host,
                                         port=settings.MQTT_BROKER_URL.port,
                                         topic=topic_payload,
                                         tls=settings.MQTT_TLS
                                         )
        time.sleep(3)

        self.cb_client.update_attribute_value(entity_id=standard_entity["id"],
                                              attr_name="attribute1", value=103)
        time.sleep(3)

        # check value
        self.assertEqual(sub_res["topic"], topic_payload)
        expected_payload = sub_res["payload"].decode()
        self.assertEqual(expected_payload, "attribute1: 103")
        mqttc.loop_stop()
        mqttc.disconnect()

# test custom notification with json
# topic = "custom/mqtt/notification/json"
    @standard_test(
        fiware_service=settings.FIWARE_SERVICE,
        fiware_servicepath=settings.FIWARE_SERVICEPATH,
        cb_url=settings.CB_URL
    )
    def test_custom_notification_json(self):
        # post notification
        notification_custom_mqtt_json = {
          "description": "MQTT Command notification",
          "subject": {
            "entities": [
              {
                "id": standard_entity["id"]
              }
            ],
            "condition": {
                "attrs": ["attribute1"]
            }
          },
          "notification": {
            "mqttCustom": {
              "url": str(settings.MQTT_BROKER_URL_INTERNAL),
              "topic": topic_json,
              "json": {
                "attribute1": "${attribute1}"
              }
            }
          },
          "throttling": 0
        }
        # TODO use filip later
        # self.cb_client.post_subscription(subscription=Subscription(
        #     **notification_custom_mqtt_json))
        url = f"{settings.CB_URL}v2/subscriptions/"
        headers = {
            'Content-Type': 'application/json',
            'fiware-service': settings.FIWARE_SERVICE,
            'fiware-servicePath': settings.FIWARE_SERVICEPATH
        }
        payload = json.dumps(notification_custom_mqtt_json)
        response = requests.request("POST", url, headers=headers, data=payload)
        self.assertEqual(response.ok, True)

        # update value
        sub_res, mqttc = self.mqtt_setup(host=settings.MQTT_BROKER_URL.host,
                                         port=settings.MQTT_BROKER_URL.port,
                                         topic=topic_json,
                                         tls=settings.MQTT_TLS
                                         )
        time.sleep(3)

        self.cb_client.update_attribute_value(entity_id=standard_entity["id"],
                                              attr_name="attribute1", value=104)
        time.sleep(3)

        # check value
        self.assertEqual(sub_res["topic"], topic_json)
        expected_payload = json.loads(sub_res["payload"].decode())
        self.assertEqual(expected_payload["attribute1"], 104)
        mqttc.loop_stop()
        mqttc.disconnect()

# test custom notification with ngsi
# topic = "custom/mqtt/notification/ngsi"
    @standard_test(
        fiware_service=settings.FIWARE_SERVICE,
        fiware_servicepath=settings.FIWARE_SERVICEPATH,
        cb_url=settings.CB_URL
    )
    def test_custom_notification_ngsi(self):
        new_entity = {
            "id": "newId",
            "type": "newType",
            "attribute_ngsi": {
                "value": "${attribute1}",
                "type": "Number"
            }
        }
        # post notification
        notification_custom_mqtt_ngsi = {
          "description": "MQTT Command notification",
          "subject": {
            "entities": [
              {
                "id": standard_entity["id"]
              }
            ],
            "condition": {
                "attrs": ["attribute1"]
            }
          },
          "notification": {
            "mqttCustom": {
              "url": str(settings.MQTT_BROKER_URL_INTERNAL),
              "topic": topic_ngsi,
              "ngsi": new_entity
            }
          },
          "throttling": 0
        }
        # TODO use filip later
        # self.cb_client.post_subscription(subscription=Subscription(
        #     **notification_custom_mqtt))
        url = f"{settings.CB_URL}v2/subscriptions/"
        headers = {
            'Content-Type': 'application/json',
            'fiware-service': settings.FIWARE_SERVICE,
            'fiware-servicePath': settings.FIWARE_SERVICEPATH
        }
        payload = json.dumps(notification_custom_mqtt_ngsi)
        response = requests.request("POST", url, headers=headers, data=payload)

        # update value
        sub_res, mqttc = self.mqtt_setup(host=settings.MQTT_BROKER_URL.host,
                                         port=settings.MQTT_BROKER_URL.port,
                                         topic=topic_ngsi,
                                         tls=settings.MQTT_TLS
                                         )
        time.sleep(3)

        self.cb_client.update_attribute_value(entity_id=standard_entity["id"],
                                              attr_name="attribute1", value=105)
        time.sleep(3)

        # check value
        self.assertEqual(sub_res["topic"], topic_ngsi)
        expected_payload = json.loads(sub_res["payload"].decode())
        self.assertEqual(expected_payload["data"][0]["id"], new_entity["id"])
        self.assertEqual(expected_payload["data"][0]["type"], new_entity["type"])
        self.assertEqual(expected_payload["data"][0]["attribute_ngsi"]["value"], 105)
        mqttc.loop_stop()
        mqttc.disconnect()

# test custom notification with dynamic topic
# more entities
# topic = "custom/mqtt/notification/dynamic/#"
    @standard_test(
        fiware_service=settings.FIWARE_SERVICE,
        fiware_servicepath=settings.FIWARE_SERVICEPATH,
        cb_url=settings.CB_URL
    )
    def test_custom_notification_dynamic_topic(self):
        # create entities
        for i in range(3):
            standard_entity["id"] = f"Entity:{i}"
            standard_entity["type"] = f"Type{i}"
            self.cb_client.post_entity(ContextEntity(**standard_entity))
        # post notification
        notification_custom_mqtt_dynamic_topic = {
          "description": "MQTT Command notification",
          "subject": {
            "entities": [
              {
                "idPattern": ".*"
              }
            ],
            "condition": {
                "attrs": ["attribute1"]
            }
          },
          "notification": {
            "mqttCustom": {
              "url": settings.MQTT_BROKER_URL_INTERNAL,
              "topic": topic_dynamic + "/${type}" + "/${id}",
            }
          },
          "throttling": 0
        }
        self.cb_client.post_subscription(subscription=Subscription(
            **notification_custom_mqtt_dynamic_topic))

        # update value
        sub_res, mqttc = self.mqtt_setup(host=settings.MQTT_BROKER_URL.host,
                                         port=settings.MQTT_BROKER_URL.port,
                                         topic=topic_dynamic+"/#",
                                         tls=settings.MQTT_TLS
                                         )
        time.sleep(3)
        for i in range(3):
            self.cb_client.update_attribute_value(entity_id=f"Entity:{i}",
                                                  attr_name="attribute1", value=106)
            time.sleep(3)
            # check value
            self.assertEqual(sub_res["topic"], topic_dynamic+f"/Type{i}"+f"/Entity:{i}")
            expected_payload = json.loads(sub_res["payload"].decode())
            self.assertEqual(expected_payload["data"][0]["id"], f"Entity:{i}")
            self.assertEqual(expected_payload["data"][0]["type"], f"Type{i}")
            self.assertEqual(expected_payload["data"][0]["attribute1"]["value"], 106)
            time.sleep(3)
        mqttc.loop_stop()
        mqttc.disconnect()


if __name__ == "__main__":
    unittest.main()

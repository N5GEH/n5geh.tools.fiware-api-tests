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


topic_default = "default/mqtt/notification"
topic_auth = "default/mqtt/notification/auth"
topic_payload = "custom/mqtt/notification/payload"
topic_json = "custom/mqtt/notification/json"
topic_ngsi = "custom/mqtt/notification/ngsi"
topic_dynamic = "custom/mqtt/notification/dynamic/#"
topic_dynamic_multiple = "custom/mqtt/notification/dynamic/multiple/#"
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
                   username=None, password=None):
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
        self.cb_client.post_subscription(subscription=Subscription(
            **notification_default_mqtt))

        # update value
        # self.mqtt_start()
        sub_res, mqttc = self.mqtt_setup(host=settings.MQTT_BROKER_URL_INTERNAL.host,
                                         port=settings.MQTT_BROKER_URL_INTERNAL.port,
                                         topic=topic_default)
        time.sleep(1)

        self.cb_client.update_attribute_value(entity_id=standard_entity["id"],
                                              attr_name="attribute1", value=101)
        time.sleep(2)

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
                                         password="readwrite")
        time.sleep(1)
        self.cb_client.update_attribute_value(entity_id=standard_entity["id"],
                                              attr_name="attribute1", value=102)
        time.sleep(2)

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
        sub_res, mqttc = self.mqtt_setup(host=settings.MQTT_BROKER_URL_INTERNAL.host,
                                         port=settings.MQTT_BROKER_URL_INTERNAL.port,
                                         topic=topic_payload)
        time.sleep(1)

        self.cb_client.update_attribute_value(entity_id=standard_entity["id"],
                                              attr_name="attribute1", value=103)
        time.sleep(1)

        # check value
        self.assertEqual(sub_res["topic"], topic_payload)
        expected_payload = sub_res["payload"].decode()
        self.assertEqual(expected_payload, "attribute1: 103")
        mqttc.loop_stop()
        mqttc.disconnect()

# test custom notification with json
# topic = "custom/mqtt/notification/json"

# test custom notification with ngsi
# topic = "custom/mqtt/notification/ngsi"

# test custom notification with dynamic topic
# more entities
# topic = "custom/mqtt/notification/dynamic/#"


if __name__ == "__main__":
    unittest.main()

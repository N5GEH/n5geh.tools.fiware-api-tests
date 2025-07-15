"""
Tests for mqtt notification based on
1. https://fiware-orion.readthedocs.io/en/master/orion-api.html#custom-notifications
2. https://fiware-orion.readthedocs.io/en/master/user/mqtt_notifications.html

"""
import json
import time
import pytest
from filip.clients.ngsi_v2 import ContextBrokerClient
from filip.models import FiwareHeader
from filip.models.ngsi_v2.context import ContextEntity
from filip.models.ngsi_v2.subscriptions import Subscription
from filip.utils.cleanup import clear_all
from paho.mqtt.client import Client, CallbackAPIVersion

from settings import settings

# ##############################################################################
# Constants and Configurations
# ##############################################################################

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


# ##############################################################################
# Fixtures and Helper Functions
# ##############################################################################

def mqtt_setup(host,
               port,
               topic,
               on_message_callback,
               username=None, password=None,
               tls: bool = False):
    """
    Helper function to set up an MQTT client to listen for notifications.
    """
    # sub_res = {
    #     "topic": None,
    #     "payload": None
    # }
    #
    # def on_message(client, userdata, msg):
    #     nonlocal sub_res
    #     sub_res["payload"] = msg.payload
    #     sub_res["topic"] = msg.topic

    mqttc = Client(CallbackAPIVersion.VERSION2)
    mqttc.on_message = on_message_callback
    if username:
        mqttc.username_pw_set(username=username, password=password)
    else:
        mqttc.username_pw_set(username=settings.MQTT_USERNAME,
                              password=settings.MQTT_PASSWORD)
    if tls:
        mqttc.tls_set()

    mqttc.connect(host=host, port=port)
    mqttc.loop_start()
    mqttc.subscribe(topic=topic)
    return mqttc


@pytest.fixture(scope="session")
def cb_client():
    """
    Pytest fixture that sets up the test environment for each test function.
    - Clears all previous entities and subscriptions.
    - Creates a standard entity.
    - Yields a ContextBrokerClient instance for the test.
    """
    fiware_header = FiwareHeader(
        service=settings.FIWARE_SERVICE,
        service_path=settings.FIWARE_SERVICEPATH
    )
    # Clean up previous test runs
    # clear_all(fiware_header=fiware_header, cb_url=settings.CB_URL)

    # Create a client for the test
    client = ContextBrokerClient(url=settings.CB_URL, fiware_header=fiware_header)

    # Post a standard entity for the test
    entity = ContextEntity(**standard_entity)
    client.post_entity(entity=entity)

    yield client

    # Teardown: close client session
    clear_all(cb_client=client)
    client.close()


# ##############################################################################
# Tests
# ##############################################################################
@pytest.mark.order(1)
def test_default_notification(cb_client: ContextBrokerClient):
    """
    Tests the default NGSIv2 notification format via MQTT.
    """
    sub_res = {
        "topic": None,
        "payload": None
    }
    def on_message(client, userdata, msg):
        sub_res["payload"] = msg.payload
        sub_res["topic"] = msg.topic

    mqttc = mqtt_setup(
        host=settings.MQTT_BROKER_URL.host,
        port=settings.MQTT_BROKER_URL.port,
        topic=topic_default,
        tls=settings.MQTT_TLS,
        on_message_callback=on_message
    )

    notification_default_mqtt = {
        "description": "MQTT Command notification",
        "subject": {
            "entities": [{"id": standard_entity["id"]}],
            "condition": {"attrs": ["attribute1"]}
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
        notification_default_mqtt["notification"]["mqtt"]["user"] = settings.MQTT_USERNAME
        notification_default_mqtt["notification"]["mqtt"]["passwd"] = settings.MQTT_PASSWORD

    cb_client.post_subscription(subscription=Subscription(**notification_default_mqtt))

    time.sleep(12)  # wait for subscription to settle

    cb_client.update_attribute_value(entity_id=standard_entity["id"], attr_name="attribute1", value=101)
    time.sleep(5)  # wait for notification

    assert sub_res["topic"] == topic_default
    received_payload = json.loads(sub_res["payload"].decode())
    assert received_payload["data"][0]["attribute1"]["value"] == 101

    mqttc.loop_stop()
    mqttc.disconnect()

@pytest.mark.order(2)
def test_default_notification_auth(cb_client: ContextBrokerClient):
    """
    Tests MQTT notification to a broker requiring authentication.
    """

    sub_res = {
        "topic": None,
        "payload": None
    }

    def on_message(client, userdata, msg):
        sub_res["payload"] = msg.payload
        sub_res["topic"] = msg.topic

    mqttc = mqtt_setup(
        host="test.mosquitto.org",
        port=1884,
        topic=topic_auth,
        username="rw",
        password="readwrite",
        tls=False,
        on_message_callback=on_message
    )

    notification_auth_mqtt = {
        "description": "MQTT Command notification",
        "subject": {
            "entities": [{"id": standard_entity["id"]}],
            "condition": {"attrs": ["attribute1"]}
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
    cb_client.post_subscription(subscription=Subscription(**notification_auth_mqtt))

    time.sleep(10)

    cb_client.update_attribute_value(entity_id=standard_entity["id"], attr_name="attribute1", value=102)
    time.sleep(10)

    assert sub_res["topic"] == topic_auth
    received_payload = json.loads(sub_res["payload"].decode())
    assert received_payload["data"][0]["attribute1"]["value"] == 102

    mqttc.loop_stop()
    mqttc.disconnect()

@pytest.mark.order(3)
def test_custom_notification_payload(cb_client: ContextBrokerClient):
    """
    Tests custom MQTT notification with a simple string payload.
    """
    sub_res = {
        "topic": None,
        "payload": None
    }

    def on_message(client, userdata, msg):
        sub_res["payload"] = msg.payload
        sub_res["topic"] = msg.topic

    mqttc = mqtt_setup(
        host=settings.MQTT_BROKER_URL.host,
        port=settings.MQTT_BROKER_URL.port,
        topic=topic_payload,
        tls=settings.MQTT_TLS,
        on_message_callback=on_message
    )

    notification_custom_mqtt = {
        "description": "MQTT Command notification",
        "subject": {
            "entities": [{"id": standard_entity["id"]}],
            "condition": {"attrs": ["attribute1"]}
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
    cb_client.post_subscription(subscription=Subscription(**notification_custom_mqtt))

    time.sleep(10)

    cb_client.update_attribute_value(entity_id=standard_entity["id"], attr_name="attribute1", value=103)
    time.sleep(10)

    assert sub_res["topic"] == topic_payload
    assert sub_res["payload"].decode() == "attribute1: 103"

    mqttc.loop_stop()
    mqttc.disconnect()

@pytest.mark.order(4)
def test_custom_notification_json(cb_client: ContextBrokerClient):
    """
    Tests custom MQTT notification with a JSON payload.
    """
    sub_res = {
        "topic": None,
        "payload": None
    }

    def on_message(client, userdata, msg):
        sub_res["payload"] = msg.payload
        sub_res["topic"] = msg.topic

    mqttc = mqtt_setup(
        host=settings.MQTT_BROKER_URL.host,
        port=settings.MQTT_BROKER_URL.port,
        topic=topic_json,
        tls=settings.MQTT_TLS,
        on_message_callback=on_message
    )

    notification_custom_mqtt_json = {
        "description": "MQTT Command notification",
        "subject": {
            "entities": [{"id": standard_entity["id"]}],
            "condition": {"attrs": ["attribute1"]}
        },
        "notification": {
            "mqttCustom": {
                "url": str(settings.MQTT_BROKER_URL_INTERNAL),
                "topic": topic_json,
                "json": {"attribute1": "${attribute1}"}
            }
        },
        "throttling": 0
    }
    cb_client.post_subscription(subscription=Subscription(**notification_custom_mqtt_json))
    time.sleep(10)

    cb_client.update_attribute_value(entity_id=standard_entity["id"], attr_name="attribute1", value=104)
    time.sleep(10)

    assert sub_res["topic"] == topic_json
    received_payload = json.loads(sub_res["payload"].decode())
    assert received_payload["attribute1"] == 104

    mqttc.loop_stop()
    mqttc.disconnect()

@pytest.mark.order(5)
def test_custom_notification_ngsi(cb_client: ContextBrokerClient):
    """
    Tests custom MQTT notification with a transformed NGSI payload.
    """

    sub_res = {
        "topic": None,
        "payload": None
    }

    def on_message(client, userdata, msg):
        sub_res["payload"] = msg.payload
        sub_res["topic"] = msg.topic

    mqttc = mqtt_setup(
        host=settings.MQTT_BROKER_URL.host,
        port=settings.MQTT_BROKER_URL.port,
        topic=topic_ngsi,
        tls=settings.MQTT_TLS,
        on_message_callback=on_message
    )

    new_entity = {
        "id": "newId",
        "type": "newType",
        "attribute_ngsi": {
            "value": "${attribute1}",
            "type": "Number"
        }
    }
    notification_custom_mqtt_ngsi = {
        "description": "MQTT Command notification",
        "subject": {
            "entities": [{"id": standard_entity["id"]}],
            "condition": {"attrs": ["attribute1"]}
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
    cb_client.post_subscription(subscription=Subscription(**notification_custom_mqtt_ngsi))

    time.sleep(10)

    cb_client.update_attribute_value(entity_id=standard_entity["id"], attr_name="attribute1", value=105)
    time.sleep(10)

    assert sub_res["topic"] == topic_ngsi
    received_payload = json.loads(sub_res["payload"].decode())
    assert received_payload["data"][0]["id"] == new_entity["id"]
    assert received_payload["data"][0]["type"] == new_entity["type"]
    assert received_payload["data"][0]["attribute_ngsi"]["value"] == 105

    mqttc.loop_stop()
    mqttc.disconnect()

@pytest.mark.order(6)
def test_custom_notification_dynamic_topic(cb_client: ContextBrokerClient):
    """
    Tests custom MQTT notification with a dynamic topic based on entity attributes.
    """

    sub_res = {
        "topic": None,
        "payload": None
    }

    def on_message(client, userdata, msg):
        sub_res["payload"] = msg.payload
        sub_res["topic"] = msg.topic

    mqttc = mqtt_setup(
        host=settings.MQTT_BROKER_URL.host,
        port=settings.MQTT_BROKER_URL.port,
        topic=topic_dynamic + "/#",
        tls=settings.MQTT_TLS,
        on_message_callback=on_message
    )

    # Create additional entities for this test
    for i in range(3):
        entity_payload = standard_entity.copy()
        entity_payload["id"] = f"Entity:{i}"
        entity_payload["type"] = f"Type{i}"
        cb_client.post_entity(ContextEntity(**entity_payload))

    notification_custom_mqtt_dynamic_topic = {
        "description": "MQTT Command notification",
        "subject": {
            "entities": [{"idPattern": ".*"}],
            "condition": {"attrs": ["attribute1"]}
        },
        "notification": {
            "mqttCustom": {
                "url": settings.MQTT_BROKER_URL_INTERNAL,
                "topic": topic_dynamic + "/${type}/${id}",
            }
        },
        "throttling": 0
    }
    cb_client.post_subscription(subscription=Subscription(**notification_custom_mqtt_dynamic_topic))

    time.sleep(10)

    for i in range(3):
        entity_id = f"Entity:{i}"
        entity_type = f"Type{i}"
        cb_client.update_attribute_value(entity_id=entity_id, attr_name="attribute1", value=106)
        time.sleep(10)  # Wait for this specific notification

        # Check value for each update
        assert sub_res["topic"] == f"{topic_dynamic}/{entity_type}/{entity_id}"
        received_payload = json.loads(sub_res["payload"].decode())
        assert received_payload["data"][0]["id"] == entity_id
        assert received_payload["data"][0]["type"] == entity_type
        assert received_payload["data"][0]["attribute1"]["value"] == 106

    mqttc.loop_stop()
    mqttc.disconnect()
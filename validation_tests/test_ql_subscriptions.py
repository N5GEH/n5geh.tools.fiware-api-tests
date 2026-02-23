import pytest
import requests
import time
from settings import settings

# Constants for FIWARE Orion Context Broker and QuantumLeap
ORION_URL = settings.CB_URL
QL_URL = settings.QL_URL
QL_URL_INTERNAL = settings.QL_URL_INTERNAL
FIWARE_SERVICE = settings.FIWARE_SERVICE
FIWARE_SERVICEPATH = settings.FIWARE_SERVICEPATH
PRODUCT_TYPE = "Product"
FIRST_PRODUCT_ID = "urn:ngsi-ld:Product:001"
SECOND_PRODUCT_ID = "urn:ngsi-ld:Product:002"
THIRD_PRODUCT_ID = "urn:ngsi-ld:Product:003"

HEADERS_JSON = {
    "fiware-service": FIWARE_SERVICE,
    "fiware-servicepath": FIWARE_SERVICEPATH
}
HEADERS_TEXT = {
    "Content-Type": "text/plain",
    "fiware-service": FIWARE_SERVICE,
    "fiware-servicepath": FIWARE_SERVICEPATH
}

@pytest.fixture(scope="module", autouse=True)
def setup_and_teardown():
    # Clean up any existing entities in Orion
    r = requests.get(f"{ORION_URL}/v2/entities", headers=HEADERS_JSON)
    assert r.status_code == 200
    for entity in r.json():
        del_r = requests.delete(f"{ORION_URL}/v2/entities/{entity['id']}", headers=HEADERS_JSON)
        assert del_r.status_code == 204
    time.sleep(3)

    # clean up any existing subscriptions in Orion
    r = requests.get(f"{ORION_URL}/v2/subscriptions/", headers=HEADERS_JSON)
    assert r.status_code == 200
    for item in r.json():
        del_r = requests.delete(f"{ORION_URL}/v2/subscriptions/{item['id']}", headers=HEADERS_JSON)
        assert del_r.status_code == 204
    time.sleep(3)

    # Clean up any existing records in QuantumLeap
    r = requests.get(f"{QL_URL}/v2/entities", headers=HEADERS_JSON)
    if r.status_code == 404 and "No records" in r.content.decode():
        pass
    else:
        assert r.status_code == 200
        for entity in r.json():
            del_r = requests.delete(f"{QL_URL}/v2/entities/{entity['entityId']}", headers=HEADERS_JSON)
            assert del_r.status_code == 204

    # SetUp: Batch Create/Overwrite New Data Entities
    payload = {
        "actionType": "append",
        "entities": [
            {
                "id": FIRST_PRODUCT_ID,
                "type": PRODUCT_TYPE,
                "name": {"type": "Text", "value": "Apples", "metadata": {}},
                "offerPrice": {"type": "Integer", "value": 89, "metadata": {}},
                "price": {"type": "Integer", "value": 99, "metadata": {}},
                "size": {"type": "Text", "value": "S", "metadata": {}},
                "specialOffer": {"type": "Boolean", "value": True, "metadata": {}}
            },
            {
                "id": SECOND_PRODUCT_ID,
                "type": PRODUCT_TYPE,
                "name": {"type": "Text", "value": "Bananas", "metadata": {}},
                "price": {"type": "Integer", "value": 1099, "metadata": {}},
                "size": {"type": "Text", "value": "M", "metadata": {}}
            },
            {
                "id": THIRD_PRODUCT_ID,
                "type": PRODUCT_TYPE,
                "name": {"type": "Text", "value": "Coconuts", "metadata": {}},
                "price": {"type": "Integer", "value": 1499, "metadata": {}},
                "size": {"type": "Text", "value": "M", "metadata": {}}
            }
        ]
    }
    r = requests.post(f"{ORION_URL}/v2/op/update", headers=HEADERS_JSON, json=payload)
    assert r.status_code == 204
    # SetUp: Add Subscription
    sub_payload = {
        "description": "Notify QuantumLeap of all price changes",
        "subject": {
            "entities": [
                {"idPattern": ".*", "type": PRODUCT_TYPE}
            ],
            "condition": {"attrs": ["price"]}
        },
        "notification": {
            "http": {"url": f"{QL_URL_INTERNAL}/v2/notify"},
            "attrs": ["price"],
            "metadata": ["dateCreated", "dateModified"]
        }
    }
    r = requests.post(f"{ORION_URL}/v2/subscriptions", headers=HEADERS_JSON, json=sub_payload)
    assert r.status_code == 201
    yield
    # TearDown: Delete Historical QuantumLeap Data
    r = requests.delete(f"{QL_URL}/v2/entities/{FIRST_PRODUCT_ID}", headers=HEADERS_JSON)
    assert r.status_code == 204
    time.sleep(3)
    r = requests.get(f"{QL_URL}/v2/entities/{FIRST_PRODUCT_ID}/attrs/price", headers=HEADERS_JSON)
    assert r.status_code == 404 or r.json().get("code") == 404
    # TearDown: Delete Subscriptions
    r = requests.get(f"{ORION_URL}/v2/subscriptions/", headers=HEADERS_JSON)
    assert r.status_code == 200
    for item in r.json():
        del_r = requests.delete(f"{ORION_URL}/v2/subscriptions/{item['id']}", headers=HEADERS_JSON)
        assert del_r.status_code == 204
    # TearDown: Batch Delete Multiple Data Entities
    delete_payload = {
        "actionType": "delete",
        "entities": [
            {"id": FIRST_PRODUCT_ID, "type": PRODUCT_TYPE},
            {"id": SECOND_PRODUCT_ID, "type": PRODUCT_TYPE},
            {"id": THIRD_PRODUCT_ID, "type": PRODUCT_TYPE}
        ]
    }
    r = requests.post(f"{ORION_URL}/v2/op/update/", headers=HEADERS_JSON, json=delete_payload)
    assert r.status_code == 204
    r = requests.get(f"{ORION_URL}/v2/entities", headers=HEADERS_JSON)
    assert r.status_code == 200
    assert r.json() == []

@pytest.mark.order(1)
def test_quantumleap_timeseries():
    # retrieving QuantumLeap version
    r = requests.get(f"{QL_URL}/version", headers=HEADERS_JSON)
    assert r.status_code == 200

    # retrieve all entities in Orion.
    r = requests.get(f"{ORION_URL}/v2/entities", headers=HEADERS_JSON)
    assert r.status_code == 200
    assert len(r.json()) == 3

    # listing all subscriptions in Orion.
    r = requests.get(f"{ORION_URL}/v2/subscriptions/", headers=HEADERS_JSON)
    assert r.status_code == 200
    assert len(r.json()) == 1

     # updating an entity attribute and triggering QuantumLeap notification
    r = requests.put(f"{ORION_URL}/v2/entities/{FIRST_PRODUCT_ID}/attrs/price/value", headers=HEADERS_TEXT, data="66")
    assert r.status_code == 204
    time.sleep(3)  # wait for QuantumLeap to process the notification

    # retrieving timeseries data from QuantumLeap
    r = requests.get(f"{QL_URL}/v2/entities/{FIRST_PRODUCT_ID}/attrs/price?lastN=3", headers=HEADERS_JSON)
    assert r.status_code == 200
    assert "values" in r.json()
    assert len(r.json()["values"]) == 1

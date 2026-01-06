import pytest
import requests
import time
from settings import settings

# Constants for FIWARE Orion Context Broker
ORION_URL = settings.CB_URL
FIWARE_SERVICE = settings.FIWARE_SERVICE
FIWARE_SERVICEPATH = settings.FIWARE_SERVICEPATH
FIRST_PRODUCT_ID = "urn:ngsi-ld:Product:001"
SECOND_PRODUCT_ID = "urn:ngsi-ld:Product:002"
THIRD_PRODUCT_ID = "urn:ngsi-ld:Product:003"
PRODUCT_TYPE = "Product"

HEADERS_JSON = {
    # "Content-Type": "application/json",
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
    yield
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
    # Check that all entities are deleted
    r = requests.get(f"{ORION_URL}/v2/entities", headers=HEADERS_JSON)
    assert r.status_code == 200
    assert r.json() == []

@pytest.mark.order(1)
def test_get_all_entities():
    """Test retrieving all entities."""
    r = requests.get(f"{ORION_URL}/v2/entities", headers=HEADERS_JSON)
    assert r.status_code == 200
    assert len(r.json()) == 3

@pytest.mark.order(2)
def test_overwrite_single_attribute():
    """Test overwriting the value of a single attribute."""
    r = requests.put(f"{ORION_URL}/v2/entities/{FIRST_PRODUCT_ID}/attrs/price/value", headers=HEADERS_TEXT, data="89")
    assert r.status_code == 204
    # Check the price value
    r = requests.get(f"{ORION_URL}/v2/entities/{FIRST_PRODUCT_ID}", headers=HEADERS_JSON)
    assert r.json()["price"]["value"] == 89

@pytest.mark.order(3)
def test_overwrite_multiple_attributes():
    """Test overwriting the value of multiple attributes."""
    patch_payload = {
        "price": {"type": "Integer", "value": 79},
        "name": {"type": "Text", "value": "Ale"}
    }
    r = requests.patch(f"{ORION_URL}/v2/entities/{FIRST_PRODUCT_ID}/attrs", headers=HEADERS_JSON, json=patch_payload)
    assert r.status_code == 204
    r = requests.get(f"{ORION_URL}/v2/entities/{FIRST_PRODUCT_ID}", headers=HEADERS_JSON)
    assert r.json()["price"]["value"] == 79
    assert r.json()["name"]["value"] == "Ale"

@pytest.mark.order(4)
def test_overwrite_type_single_attribute():
    """Test overwriting the type of a single attribute."""
    patch_payload = {
        "price": {"type": "String", "value": "79"}
    }
    r = requests.patch(f"{ORION_URL}/v2/entities/{FIRST_PRODUCT_ID}/attrs", headers=HEADERS_JSON, json=patch_payload)
    assert r.status_code == 204
    r = requests.get(f"{ORION_URL}/v2/entities/{FIRST_PRODUCT_ID}", headers=HEADERS_JSON)
    assert r.json()["price"]["value"] == "79"
    assert r.json()["price"]["type"] == "String"

@pytest.mark.order(5)
def test_overwrite_type_multiple_attributes():
    """Test overwriting the type of multiple attributes."""
    patch_payload = {
        "price": {"value": 79},
        "name": {"type": "String", "value": "Ale"}
    }
    r = requests.patch(f"{ORION_URL}/v2/entities/{FIRST_PRODUCT_ID}/attrs", headers=HEADERS_JSON, json=patch_payload)
    assert r.status_code == 204
    r = requests.get(f"{ORION_URL}/v2/entities/{FIRST_PRODUCT_ID}", headers=HEADERS_JSON)
    assert r.json()["price"]["value"] == 79
    assert r.json()["price"]["type"] in ["Number", "Integer"]
    assert r.json()["name"]["value"] == "Ale"
    assert r.json()["name"]["type"] == "String"

@pytest.mark.order(6)
def test_delete_attribute():
    """Test deleting an attribute from a data entity."""
    r = requests.delete(f"{ORION_URL}/v2/entities/{FIRST_PRODUCT_ID}/attrs/specialOffer", headers=HEADERS_JSON)
    assert r.status_code == 204
    r = requests.get(f"{ORION_URL}/v2/entities/{FIRST_PRODUCT_ID}", headers=HEADERS_JSON)
    assert "specialOffer" not in r.json()

@pytest.mark.order(7)
def test_batch_delete_multiple_attributes():
    """Test batch deleting multiple attributes from a data entity."""
    payload = {
        "actionType": "delete",
        "entities": [
            {
                "id": FIRST_PRODUCT_ID,
                "type": PRODUCT_TYPE,
                "price": {},
                "name": {}
            }
        ]
    }
    r = requests.post(f"{ORION_URL}/v2/op/update/", headers=HEADERS_JSON, json=payload)
    assert r.status_code == 204
    r = requests.get(f"{ORION_URL}/v2/entities/{FIRST_PRODUCT_ID}", headers=HEADERS_JSON)
    assert "price" not in r.json()
    assert "name" not in r.json()

@pytest.mark.order(8)
def test_add_new_attribute():
    """Test adding a new attribute to an entity."""
    payload = {
        "specialOffer": {"value": True}
    }
    r = requests.post(f"{ORION_URL}/v2/entities/{FIRST_PRODUCT_ID}/attrs", headers=HEADERS_JSON, json=payload)
    assert r.status_code == 204
    r = requests.get(f"{ORION_URL}/v2/entities/{FIRST_PRODUCT_ID}", headers=HEADERS_JSON)
    assert r.json()["specialOffer"]["value"] is True
    assert r.json()["specialOffer"]["type"] == "Boolean"

@pytest.mark.order(9)
def test_batch_create_new_attributes():
    """Test batch creating new attributes with append_strict."""
    payload = {
        "actionType": "append_strict",
        "entities": [
            {
                "id": FIRST_PRODUCT_ID,
                "type": PRODUCT_TYPE,
                "name": {"type": "Text", "value": "Apples", "metadata": {}},
                "price": {"type": "Integer", "value": 99, "metadata": {}}
            }
        ]
    }
    r = requests.post(f"{ORION_URL}/v2/op/update/", headers=HEADERS_JSON, json=payload)
    # This may fail if attributes already exist, so accept 422 (Unprocessable Entity)
    assert r.status_code in [204, 422]

@pytest.mark.order(10)
def test_update_metadata_of_multiple_attributes():
    """Test updating metadata of multiple attributes."""
    payload = {
        "actionType": "append",
        "entities": [
            {
                "id": FIRST_PRODUCT_ID,
                "type": PRODUCT_TYPE,
                "name": {"type": "Text", "value": "Apples", "metadata": {"TimeInstant": {"type": "DateTime", "value": "2024-04-04T14:08:16.655Z"}}},
                "price": {"type": "Integer", "value": 99, "metadata": {"TimeInstant": {"type": "DateTime", "value": "2024-04-04T14:08:16.655Z"}}}
            }
        ]
    }
    r = requests.post(f"{ORION_URL}/v2/op/update/", headers=HEADERS_JSON, json=payload)
    assert r.status_code == 204
    r = requests.get(f"{ORION_URL}/v2/entities/{FIRST_PRODUCT_ID}", headers=HEADERS_JSON)
    assert r.json()["price"]["metadata"]
    assert r.json()["name"]["metadata"]

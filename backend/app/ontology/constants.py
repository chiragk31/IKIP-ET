"""
Ontology Constants and Mappings
"""

from app.utils.constants import EntityType, RelationshipType

# The core allowed entity types
CORE_ENTITY_TYPES = {e.value for e in EntityType}

# The core allowed relationship types
VALID_RELATIONSHIP_TYPES = {r.value for r in RelationshipType}

# Entity synonym mapping (Target Canonical -> [Synonyms])
ENTITY_SYNONYMS = {
    "Pump": ["Water Pump", "Feed Pump", "Centrifugal Pump", "Pumping Unit"],
    "Boiler": ["Steam Generator", "Steam Boiler"],
    "Motor": ["Electric Motor", "Drive Motor", "Drive Unit"],
    "Compressor": ["Air Compressor", "Gas Compressor"],
    "Valve": ["Control Valve", "Isolation Valve", "Gate Valve"],
    "Bearing": ["Roller Bearing", "Ball Bearing", "Journal Bearing"],
    "Operator": ["Plant Operator", "Field Operator"],
    "Engineer": ["Maintenance Engineer", "Process Engineer", "Reliability Engineer"],
    "Maintenance": ["Repair", "Service", "Overhaul"],
    "Failure": ["Breakdown", "Fault", "Malfunction", "Trip"],
}

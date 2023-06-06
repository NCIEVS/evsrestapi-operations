from typing import Optional

from pydantic import BaseModel


class Concept(BaseModel):
    code: str
    semantic_type: str
    preferred_name: str
    synonyms: Optional[list[str]]


class Attribute(BaseModel):
    code: str
    attribute_type: str
    value: str


class ParentChild(BaseModel):
    parent: str
    child: str


class Relationship(BaseModel):
    code: str
    defining: bool
    relationship_group: str
    type: str
    additional_type: str
    target_code: str

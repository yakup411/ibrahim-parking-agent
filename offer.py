from dataclasses import dataclass


@dataclass
class Offer:
    source: str
    title: str
    address: str
    price: str
    link: str
    latitude: float
    longitude: float
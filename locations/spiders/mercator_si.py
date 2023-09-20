import scrapy
from locations.categories import Categories, apply_category
from locations.hours import DAYS_FULL, OpeningHours

from locations.items import Feature


class MercatorSpider(scrapy.Spider):
    name = "mercator_si"
    item_attributes = {"brand": "Mercator", "brand_wikidata": "Q738412"}
    allowed_domains = ["mojm.mercator.si"]

    start_urls = ["https://mojm.mercator.si/v1/logistics/stores/list"]

    def parse(self, response):
        data = response.json()
        assert data["data"]["success"]

        for store in data["data"]["data"]["locations"]:
            feature = Feature(
                ref=store["id"],
                name=store["name"],
                lat=store["latitude"],
                lon=store["longitude"],
                street_address=store["address"],
                city=store["location"],
                postcode=store["post"],
                country="SI",
                opening_hours=self.parse_open_hours(store["openingHours"], store["exceptions"]),
            )

            if store["typeName"] in ("Supermarket", "Hipermarket"):
                apply_category(Categories.SHOP_SUPERMARKET, feature)
            elif store["typeName"] in ("Živilska prodajalna", "Maxi"):
                apply_category(Categories.SHOP_CONVENIENCE, feature)
            elif store["typeName"] == "Tehnika in gradnja":
                apply_category(Categories.SHOP_HARDWARE, feature)
            elif store["typeName"] == "Restavracija":
                apply_category(Categories.RESTAURANT, feature)
            elif store["typeName"] == "Bar/okrepčevalnica":
                apply_category(Categories.CAFE, feature)
            else:
                self.logger.warning("Unknown store type: %s", store["typeName"])

            yield feature

    def parse_open_hours(self, obj, exceptions):
        # TODO: is there a way to handle exceptions?
        opening_hours = OpeningHours()

        for day in DAYS_FULL:
            times = obj[day.lower()]
            if times["display"] == "ZAPRTO":
                continue
            time_open, time_close = times["display"].split(" - ")
            opening_hours.add_range(day=day[:2], open_time=time_open, close_time=time_close)

        return opening_hours.as_opening_hours()

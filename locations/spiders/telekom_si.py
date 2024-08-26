import scrapy
from scrapy.http import Response
from scrapy.http.request.json_request import JsonRequest

from locations.categories import Categories, apply_category
from locations.hours import OpeningHours
from locations.items import Feature


class TelekomSISpider(scrapy.Spider):
    name = "telekom_si"
    item_attributes = {"brand": "Telekom Slovenije", "brand_wikidata": "Q1335433"}
    allowed_domains = ["cms.telekom.si"]

    graphql_url = "https://cms.telekom.si/graphql"
    graphql_query = """
    query getPointOfSales($pointOfSalesId: ID, $culture: String) {
        integrations {
            pointOfSalesIntegration {
                getPointOfSales(pointOfSalesId: $pointOfSalesId, culture: $culture) {
                    items {
                    ...pointOfSale
                    }
                }
            }
        }
    }
    fragment pointOfSale on PointOfSale {
        name
        _url
        address
        postNumber
        postName
        email
        isEshop
        latitude
        longitude
        phoneNumber
        gsmNumber
        categories
        workingDays {
            dayOfWeek
            openinghours {
                openFrom
                openTo
            }
        }
    }"""

    def start_requests(self):
        data = {
            "operationName": "getPointOfSales",
            "query": self.graphql_query,
            "variables": {
                "culture": "sl-SI",
                "pointOfSalesId": "74b7e783-c6c1-41a7-8253-daa675c84c16",
            },
        }
        yield JsonRequest(url=self.graphql_url, method="POST", data=data)

    def parse(self, response: Response):
        data = response.json()

        for item in data["data"]["integrations"]["pointOfSalesIntegration"]["getPointOfSales"]["items"]:
            # Skip non-physical locations
            if "TEREN" in item["address"] or item["isEshop"]:
                continue

            feature = Feature(
                ref=item["_url"],
                name=item["name"],
                phone=item["phoneNumber"] or item["gsmNumber"],
                lat=item["latitude"],
                lon=item["longitude"],
                street_address=item["address"],
                postcode=item["postNumber"],
                city=item["postName"],
                email=item["email"],
                website=f"https://www.telekom.si" + item["_url"],
                country="SI",
                opening_hours=self.parse_open_hours(item["workingDays"]) or None,
            )

            apply_category(Categories.SHOP_TELECOMMUNICATION, feature)

            yield feature

    def parse_open_hours(self, hours):
        opening_hours = OpeningHours()
        for interval in hours:
            for oh in interval["openinghours"]:
                opening_hours.add_range(
                    day=interval["dayOfWeek"].title()[:2],
                    open_time=oh["openFrom"],
                    close_time=oh["openTo"],
                    time_format="%H.%M",
                )
        return opening_hours.as_opening_hours()

import logging

import scrapy

from locations.categories import Categories, apply_yes_no
from locations.hours import OpeningHours
from locations.items import Feature

DAY_MAPPING = {
    "pon": "Mo",
    "tor": "Tu",
    "sre": "We",
    "čet": "Th",
    "pet": "Fr",
    "sob": "Sa",
    "ned": "Su",
    # TODO: handle holidays
    # "praz": "PH",
}


class TriDVASpider(scrapy.Spider):
    name = "3dva_si"
    item_attributes = {
        "brand": "3DVA",
        "brand_wikidata": "Q1941592",
        "country": "SI",
        "extras": Categories.SHOP_NEWSAGENT.value,
    }
    allowed_domains = ["trafika3dva.si"]

    def start_requests(self):
        yield scrapy.Request(
            url="https://trafika3dva.si/DesktopModules/Trafika3Dva/api/Map/getMapPoints",
            method="POST",
            headers={
                "Accept": "application/json; q=0.01",
            },
        )

    def parse(self, response):
        data = response.json()

        for store in data:
            item = Feature()
            item["ref"] = store["TrafikaId"]
            item["name"] = store["Naziv"]
            item["addr_full"] = store["Naslov"] + " " + store["Posta"] + " " + store["Kraj"]
            item["lat"] = store["Lat"]
            item["lon"] = store["Long"]

            if store.get("phone"):
                item["phone"] = "+" + store["phone"]

            oh = OpeningHours()
            for schedule in store["DelovniCasi"]:
                if schedule["Vrednost"] == "zaprto":
                    continue

                try:
                    schedule["Naziv"] = schedule["Naziv"].lower().strip()

                    # Sometimes days are separate ("Četrtek", "Petek"), sometime together ("tor., sre.")
                    days = []
                    if schedule["Naziv"] == "pon. do pet.":
                        days = ["Mo", "Tu", "We", "Th", "Fr"]
                    else:
                        for key, day in DAY_MAPPING.items():
                            if key in schedule["Naziv"]:
                                days.append(day)

                    schedule["Naziv"] = schedule["Naziv"].lower().strip()

                    # Multiple ranges per day (with a break in the middle)
                    for range in schedule["Vrednost"].replace("in", ",").split(","):
                        # 24-hour shops
                        if range.startswith("24"):
                            times = ("00:00", "24:00")
                        else:
                            times = range.split("-")

                        oh.add_days_range(
                            days,
                            times[0].strip(),
                            times[1].strip(),
                            "%H:%M",
                        )
                except Exception as e:
                    logging.warning(
                        "Couldn't parse open time Naziv='%s',Vrednost='%s'", schedule["Naziv"], schedule["Vrednost"]
                    )

            item["opening_hours"] = oh.as_opening_hours()

            for service in store["Storitve"]:
                apply_yes_no("sells:lottery", item, service["Aktivna"] and service["Naziv"] == "Loto")

            yield item

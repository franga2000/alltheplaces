import scrapy
from locations.hours import OpeningHours

from locations.items import Feature


class TusSpider(scrapy.Spider):
    name = "tus_si"
    item_attributes = {"brand": "Tuš",}
    allowed_domains = ["www.tus.si"]

    start_urls = ["https://www.tus.si/wp-admin/admin-ajax.php?action=creatim_work_hours_ajax&async=false"]

    # TODO: store links are available by parsing a JS object at
    # https://www.tus.si/delovni-casi/ : 
    #    var idPermalinkDictionary = {"[store_id]": "[store_url]", ...}


    def parse(self, response):
        for row in response.json():
            # TODO: handle "type"
            feature = Feature(
                ref=row["id"],
                name=row["title"],
                phone=(row["phone"]).split(";", maxsplit=1)[0] or None,
                lat=row["y"],
                lon=row["x"],
                email=(row["emailHU"] or row["email"]).split(";", maxsplit=1)[0] or None,
                street_address=row["street"],
                postcode=row["city"],
                city=row["post"].strip(),
                country="SI",
                opening_hours=self.parse_open_hours(row["workHours"]) or None,
            )
            yield feature


    def parse_open_hours(self, hours):
        # Format sample:
        #   "mon": "08:00 - 20:00",
        # 	"sun": "00:00 - 00:00"
        opening_hours = OpeningHours()
        for day, hours in hours.items():
            if not hours:
                continue
            open_h, close_h = hours.split(" - ")
            if open_h == "00:00" and close_h == "00:00":
                continue

            opening_hours.add_range(
                day=day[:2].title(), 
                open_time=open_h,
                close_time=close_h,
            )
        return opening_hours.as_opening_hours()
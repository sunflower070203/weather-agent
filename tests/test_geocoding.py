import unittest
from unittest.mock import Mock

from weather_agent.geocoding import GeocodingClient, GeocodingError


class GeocodingClientTests(unittest.TestCase):
    def test_returns_location_candidates_with_coordinates(self):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "results": [
                {
                    "name": "北京",
                    "latitude": 39.9075,
                    "longitude": 116.3972,
                    "country": "中国",
                    "admin1": "北京市",
                    "timezone": "Asia/Shanghai",
                }
            ]
        }
        session = Mock()
        session.get.return_value = response
        client = GeocodingClient(session=session)

        candidates = client.search("北京")

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].name, "北京")
        self.assertEqual(candidates[0].longitude, 116.3972)
        self.assertEqual(candidates[0].latitude, 39.9075)
        self.assertEqual(candidates[0].display_name, "北京, 北京市, 中国")
        session.get.assert_called_once_with(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": "北京", "count": 5, "language": "zh", "format": "json"},
            timeout=10,
        )

    def test_returns_empty_candidates_when_location_is_not_found(self):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {}
        session = Mock()
        session.get.return_value = response

        self.assertEqual(GeocodingClient(session=session).search("不存在地点"), ())

    def test_falls_back_to_explicit_municipality_for_unrecognized_poi(self):
        missing = Mock()
        missing.raise_for_status.return_value = None
        missing.json.return_value = {}
        city = Mock()
        city.raise_for_status.return_value = None
        city.json.return_value = {
            "results": [
                {
                    "name": "北京",
                    "latitude": 39.9075,
                    "longitude": 116.3972,
                    "country": "中国",
                    "admin1": "北京市",
                    "timezone": "Asia/Shanghai",
                }
            ]
        }
        session = Mock()
        session.get.side_effect = (missing, city)

        candidates = GeocodingClient(session=session).search(
            "北京奥林匹克森林公园"
        )

        self.assertEqual(len(candidates), 1)
        self.assertTrue(candidates[0].is_approximate)
        self.assertEqual(candidates[0].resolved_query, "北京")
        self.assertEqual(session.get.call_count, 2)

    def test_rejects_blank_location_query_without_calling_service(self):
        session = Mock()

        with self.assertRaisesRegex(GeocodingError, "blank"):
            GeocodingClient(session=session).search("  ")

        session.get.assert_not_called()

    def test_exact_municipality_query_discards_other_same_name_places(self):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "results": [
                {
                    "name": "北京",
                    "latitude": 39.9075,
                    "longitude": 116.3972,
                    "country": "中国",
                    "admin1": "北京市",
                    "timezone": "Asia/Shanghai",
                },
                {
                    "name": "北京",
                    "latitude": 29.5,
                    "longitude": 106.5,
                    "country": "中国",
                    "admin1": "重庆市",
                    "timezone": "Asia/Shanghai",
                },
                {
                    "name": "北京",
                    "latitude": 30.6,
                    "longitude": 104.1,
                    "country": "中国",
                    "admin1": "四川",
                    "timezone": "Asia/Shanghai",
                },
            ]
        }
        session = Mock()
        session.get.return_value = response

        candidates = GeocodingClient(session=session).search("北京")

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].admin1, "北京市")
        self.assertEqual(candidates[0].longitude, 116.3972)

    def test_non_municipality_results_are_not_discarded_or_reordered(self):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "results": [
                {
                    "name": "杭州",
                    "latitude": 30.0,
                    "longitude": 102.0,
                    "country": "中国",
                    "admin1": "四川",
                    "timezone": "Asia/Shanghai",
                },
                {
                    "name": "杭州市",
                    "latitude": 30.27,
                    "longitude": 120.15,
                    "country": "中国",
                    "admin1": "浙江",
                    "timezone": "Asia/Shanghai",
                },
            ]
        }
        session = Mock()
        session.get.return_value = response

        candidates = GeocodingClient(session=session).search("杭州")

        self.assertEqual(len(candidates), 2)
        self.assertEqual(candidates[0].admin1, "四川")
        self.assertEqual(candidates[1].admin1, "浙江")


if __name__ == "__main__":
    unittest.main()

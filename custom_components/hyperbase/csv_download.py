from datetime import datetime
from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant
from homeassistant.helpers.httpx_client import get_async_client

import csv
from io import StringIO
from aiohttp import web
import httpx

from .const import DOMAIN, LOGGER

class CSVDownloadView(HomeAssistantView):
    url = "/api/hyperbase/download_csv"
    name = "api:hyperbase:download_csv"
    requires_auth = False

    def __init__(self, hass: HomeAssistant):
        self.hass = hass
        super().__init__()

    async def get(self, request: web.Request) -> web.Response:
        config_entries = self.hass.config_entries.async_entries(DOMAIN)
        if not config_entries:
            return web.Response(status=404, text="Integration not configured")

        config = config_entries[0].data
        base_url = config.get("base_url")
        project_id = config.get("project_id")
        auth_token = config.get("auth_token")
        
        if not base_url:
            return web.Response(status=400, text="REST endpoint not configured")

        try:
            client = get_async_client(self.hass, verify_ssl=False)
            headers = {}
            if auth_token:
                headers["Authorization"] = f"Bearer {auth_token}"
            
            start_time = request.query.get("start_time")
            end_time = request.query.get("end_time")
            collection_id = request.query.get("collection_id")

            query = {
                "orders": [
                    {"field": "connector_entity", "kind": "asc"},
                    {"field": "record_date", "kind": "asc"},
                ],
                "filters": [{
                    "op": "AND",
                    "children": [
                        {"field": "record_date", "op": ">=", "value": start_time},
                        {"field": "record_date", "op": "<=", "value": end_time},
                    ]
                }]
            }
            
            LOGGER.debug(query)
            response = await client.post(f"{base_url}/api/rest/project/{project_id}/collection/{collection_id}/records",
                headers=headers,
                timeout=httpx.Timeout(10, connect=5, read=20, write=5),
                json=query
                )
            response.raise_for_status()

            data = response.json().get("data")
            count = response.json().get("pagination").get("total")

            if count < 1:
                return web.Response(status=404, text="No data retrieved")
            
            csv_headers = data[0].keys()
            out = StringIO()
            
            writer = csv.DictWriter(out, fieldnames=csv_headers)
            writer.writeheader()
            
            _start_time = datetime.fromisoformat(start_time).strftime("%Y%m%d-%H%M%S")
            _end_time = datetime.fromisoformat(end_time).strftime("%Y%m%d-%H%M%S")
            filename = f"{collection_id}_{_start_time}_{_end_time}.csv"
            for row in data:
                writer.writerow(row)

            return web.Response(
                body=out.getvalue(),
                content_type="text/csv",
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}"'
                }
            )

        except httpx.HTTPStatusError as e:
            return web.Response(status=e.response.status_code, text=f"HTTP error: {str(e)}")
        except Exception as e:
            return web.Response(status=500, text=f"Error: {str(e)}")
import httpx
import config

class MiroClient:
    def __init__(self):
        self.base_url = "https://miro.com"
        self.board_id = config.MIRO_BOARD_ID
        self.headers = {
            "Authorization": f"Bearer {config.MIRO_ACCESS_TOKEN}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

# =====================================================================
# Service methods
# =====================================================================
    async def get_all_items(self) -> list:
        url = f"{self.base_url}/boards/{self.board_id}/items"
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers)
            if response.status_code != 200:
                print(f"Error fetching items: {response.text}")
                return []
            return response.json().get("data", [])

    async def _find_items_by_query(self, item_type: str, text_query: str = "", color_query: str = "") -> list:
        all_items = await self.get_all_items()
        matched_items = []
        
        text_query = text_query.lower() if text_query else ""
        color_query = color_query.lower() if color_query else ""

        for item in all_items:
            if item.get("type") != item_type:
                continue
                
            content = item.get("data", {}).get("content", "").lower()
            style = item.get("style", {})
            fill_color = style.get("fillColor", "").lower()
            
            text_match = text_query in content if text_query else True
            color_match = color_query in fill_color if color_query else True
            
            if text_query or color_query:
                if text_match and color_match:
                    matched_items.append(item)
                    
        return matched_items

    async def _delete_item_by_id(self, item_id: str) -> bool:
        url = f"{self.base_url}/boards/{self.board_id}/items/{item_id}"
        async with httpx.AsyncClient() as client:
            response = await client.delete(url, headers=self.headers)
            return response.status_code == 204

# =====================================================================
# Shapes operations
# =====================================================================
    async def create_shape(self, text: str, color: str, font_color: str, x: int, y: int, width: int, height: int) -> dict:
        url = f"{self.base_url}/boards/{self.board_id}/shapes"
        payload = {
            "data": {"content": text, "shape": "rectangle"},
            "style": {"fillColor": color, "borderColor": color, "borderWidth": "2.0"},
            "position": {"x": x, "y": y, "origin": "center"},
            "geometry": {"width": width, "height": height}
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=self.headers, json=payload)
            return response.json() if response.status_code == 201 else {}

    async def delete_shape(self, text_query: str = "", color_query: str = "") -> str:
        shapes = await self._find_items_by_query("shape", text_query, color_query)
        if not shapes:
            return "No matching shapes found to delete."
        
        deleted_count = 0
        for shape in shapes:
            if await self._delete_item_by_id(shape["id"]):
                deleted_count += 1
        return f"Successfully deleted {deleted_count} shape(s)."

    async def update_shape(self, find_text: str = "", find_color: str = "", **kwargs) -> str:
        shapes = await self._find_items_by_query("shape", find_text, find_color)
        if not shapes:
            return "No matching shapes found to update."

        updated_count = 0
        async with httpx.AsyncClient() as client:
            for shape in shapes:
                url = f"{self.base_url}/boards/{self.board_id}/shapes/{shape['id']}"
                payload = {"data": {}, "style": {}, "position": {}, "geometry": {}}
                
                if kwargs.get("new_text") is not None:
                    payload["data"]["content"] = kwargs["new_text"]
                if kwargs.get("new_color") is not None:
                    payload["style"]["fillColor"] = kwargs["new_color"]
                    payload["style"]["borderColor"] = kwargs["new_color"]
                if kwargs.get("new_width") is not None:
                    payload["geometry"]["width"] = kwargs["new_width"]
                if kwargs.get("new_height") is not None:
                    payload["geometry"]["height"] = kwargs["new_height"]
                if kwargs.get("new_x") is not None:
                    payload["position"]["x"] = kwargs["new_x"]
                if kwargs.get("new_y") is not None:
                    payload["position"]["y"] = kwargs["new_y"]

                payload = {k: v for k, v in payload.items() if v}

                if payload:
                    response = await client.patch(url, headers=self.headers, json=payload)
                    if response.status_code == 200:
                        updated_count += 1

        return f"Successfully updated {updated_count} shape(s)."

# =====================================================================
# Sticky notes operations
# =====================================================================
    async def create_sticker(self, text: str, color: str, x: int, y: int, shape: str) -> dict:
        url = f"{self.base_url}/boards/{self.board_id}/sticky_notes"
        payload = {
            "data": {"content": text, "shape": shape},
            "style": {"fillColor": color},
            "position": {"x": x, "y": y, "origin": "center"}
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=self.headers, json=payload)
            return response.json() if response.status_code == 201 else {}

    async def delete_sticker(self, text_query: str = "", color_query: str = "") -> str:
        stickers = await self._find_items_by_query("sticky_note", text_query, color_query)
        if not stickers:
            return "No matching sticky notes found to delete."
        
        deleted_count = 0
        for sticker in stickers:
            if await self._delete_item_by_id(sticker["id"]):
                deleted_count += 1
        return f"Successfully deleted {deleted_count} sticky note(s)."

    async def update_sticker(self, find_text: str = "", find_color: str = "", **kwargs) -> str:
        stickers = await self._find_items_by_query("sticky_note", find_text, find_color)
        if not stickers:
            return "No matching sticky notes found to update."

        updated_count = 0
        async with httpx.AsyncClient() as client:
            for sticker in stickers:
                url = f"{self.base_url}/boards/{self.board_id}/sticky_notes/{sticker['id']}"
                payload = {"data": {}, "style": {}, "position": {}}
                
                if kwargs.get("new_text") is not None:
                    payload["data"]["content"] = kwargs["new_text"]
                if kwargs.get("new_shape") is not None:
                    payload["data"]["shape"] = kwargs["new_shape"]
                if kwargs.get("new_color") is not None:
                    payload["style"]["fillColor"] = kwargs["new_color"]
                if kwargs.get("new_x") is not None:
                    payload["position"]["x"] = kwargs["new_x"]
                if kwargs.get("new_y") is not None:
                    payload["position"]["y"] = kwargs["new_y"]

                payload = {k: v for k, v in payload.items() if v}

                if payload:
                    response = await client.patch(url, headers=self.headers, json=payload)
                    if response.status_code == 200:
                        updated_count += 1

        return f"Successfully updated {updated_count} sticky note(s)."

# =====================================================================
# Zone\Frame operations
# =====================================================================
    async def create_zone(self, zone_name: str, x: int, y: int, width: int, height: int) -> dict:
        url = f"{self.base_url}/boards/{self.board_id}/frames"
        payload = {
            "data": {"title": zone_name},
            "position": {"x": x, "y": y},
            "geometry": {"width": width, "height": height}
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=self.headers, json=payload)
            return response.json() if response.status_code == 201 else {}

    async def delete_zone(self, zone_name: str) -> str:
        all_items = await self.get_all_items()
        for item in all_items:
            if item.get("type") == "frame" and item.get("data", {}).get("title", "").lower() == zone_name.lower():
                if await self._delete_item_by_id(item["id"]):
                    return f"Zone '{zone_name}' successfully deleted."
        return f"Zone '{zone_name}' not found."

    async def copy_zone(self, source_zone_name: str, new_zone_name: str) -> str:
        all_items = await self.get_all_items()
        source_frame = None
        
        for item in all_items:
            if item.get("type") == "frame" and item.get("data", {}).get("title", "").lower() == source_zone_name.lower():
                source_frame = item
                break
                
        if not source_frame:
            return f"Source zone '{source_zone_name}' not found."

        src_x = source_frame["position"]["x"]
        src_y = source_frame["position"]["y"]
        src_w = source_frame["geometry"]["width"]
        src_h = source_frame["geometry"]["height"]

        offset_x = src_w + 200
        new_x = src_x + offset_x
        new_y = src_y

        created_frame = await self.create_zone(new_zone_name, new_x, new_y, src_w, src_h)
        if not created_frame:
            return "Failed to create new zone layer."

        left = src_x - (src_w / 2)
        right = src_x + (src_w / 2)
        top = src_y - (src_h / 2)
        bottom = src_y + (src_h / 2)

        copied_elements_count = 0
        
        for item in all_items:
            if item.get("type") not in ["shape", "sticky_note"]:
                continue
                
            item_x = item["position"]["x"]
            item_y = item["position"]["y"]

            if left <= item_x <= right and top <= item_y <= bottom:
                rel_x = item_x - src_x
                rel_y = item_y - src_y
                target_x = new_x + rel_x
                target_y = new_y + rel_y

                if item["type"] == "shape":
                    await self.create_shape(
                        text=item["data"].get("content", ""),
                        color=item["style"].get("fillColor", "#ffffff"),
                        font_color=item["style"].get("textColor", "#000000"),
                        x=target_x, 
                        y=target_y,
                        width=item["geometry"].get("width", 100),
                        height=item["geometry"].get("height", 100)
                    )
                elif item["type"] == "sticky_note":
                    await self.create_sticker(
                        text=item["data"].get("content", ""),
                        color=item["style"].get("fillColor", "light_yellow"),
                        x=target_x, 
                        y=target_y,
                        shape=item["data"].get("shape", "square")
                    )
                copied_elements_count += 1

        return f"Zone '{source_zone_name}' successfully duplicated into '{new_zone_name}' with {copied_elements_count} items."

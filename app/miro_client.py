import httpx
import config

class MiroClient:
    def __init__(self):
        self.base_url = config.MIRO_API_ENDPOINT
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
        url = f"{self.base_url}/boards/{self.board_id}/items?limit=50"
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
        
    async def _delete_item_by_id(self, item_id: str, item_type: str) -> bool:
        api_type = "sticky_notes" if item_type == "sticky_note" else f"{item_type}s"
        url = f"{self.base_url}/boards/{self.board_id}/{api_type}/{item_id}"
        
        async with httpx.AsyncClient() as client:
            response = await client.delete(url, headers=self.headers)
            return response.status_code == 204


# =====================================================================
# Shapes operations
# =====================================================================
    async def create_shape(self, text: str, color: str, font_color: str, x: int, y: int, width: int, height: int) -> dict:
        url = f"{self.base_url}/boards/{self.board_id}/items"
        payload = {
            "type": "shape",
            "data": {"content": text, "shape": "rectangle"},
            "style": {"fillColor": color, "borderColor": color, "borderWidth": 2.0, "textColor": font_color},
            "position": {"x": x, "y": y, "origin": "center"},
            "geometry": {"width": width, "height": height}
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=self.headers, json=payload)
            if response.status_code != 201:
                print(f"Miro Error (create_shape): {response.status_code} - {response.text}")
                return {}
            return response.json()

    async def delete_shape(self, text_query: str = "", color_query: str = "") -> str:
        shapes = await self._find_items_by_query("shape", text_query, color_query)
        if not shapes:
            return "No matching shapes found to delete."
        
        deleted_count = 0
        
        for shape in shapes:
            if await self._delete_item_by_id(shape["id"], "shape"):
                deleted_count += 1

        return f"Successfully deleted {deleted_count} shape(s)."

    async def update_shape(self, find_text: str = "", find_color: str = "", **kwargs) -> str:
        shapes = await self._find_items_by_query("shape", find_text, find_color)
        if not shapes:
            return "No matching shapes found to update."

        updated_count = 0
        async with httpx.AsyncClient() as client:
            for shape in shapes:
                url = f"{self.base_url}/boards/{self.board_id}/items/{shape['id']}"
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
        url = f"{self.base_url}/boards/{self.board_id}/items"
        payload = {
            "type": "sticky_note",
            "data": {"content": text, "shape": shape},
            "style": {"fillColor": color},
            "position": {"x": x, "y": y, "origin": "center"}
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=self.headers, json=payload)
            if response.status_code != 201:
                print(f"Miro Error (create_sticker): {response.status_code} - {response.text}")
                return {}
            return response.json()

    async def delete_sticker(self, text_query: str = "", color_query: str = "") -> str:
        stickers = await self._find_items_by_query("sticky_note", text_query, color_query)
        if not stickers:
            return "No matching sticky notes found to delete."
        
        deleted_count = 0
        
        for sticker in stickers:
            if await self._delete_item_by_id(sticker["id"], "sticky_note"):
                deleted_count += 1
                
        return f"Successfully deleted {deleted_count} sticky note(s)."

    async def update_sticker(self, find_text: str = "", find_color: str = "", **kwargs) -> str:
        stickers = await self._find_items_by_query("sticky_note", find_text, find_color)
        if not stickers:
            return "No matching sticky notes found to update."

        updated_count = 0
        async with httpx.AsyncClient() as client:
            for sticker in stickers:
                url = f"{self.base_url}/boards/{self.board_id}/items/{sticker['id']}"
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
        url = f"{self.base_url}/boards/{self.board_id}/items"
        payload = {
            "type": "frame",
            "data": {"title": zone_name},
            "position": {"x": x, "y": y},
            "geometry": {"width": width, "height": height}
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=self.headers, json=payload)
            if response.status_code != 201:
                print(f"Miro Error (create_zone): {response.status_code} - {response.text}")
                return {}
            return response.json()

    async def delete_zone(self, zone_name: str) -> str:
        all_items = await self.get_all_items()
        for item in all_items:
            if item.get("type") == "frame" and item.get("data", {}).get("title", "").lower() == zone_name.lower():
                if await self._delete_item_by_id(item["id"], "frame"):
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
        src_w = source_frame.get("geometry", {}).get("width", 0) or source_frame.get("size", {}).get("width", 800)
        src_h = source_frame.get("geometry", {}).get("height", 0) or source_frame.get("size", {}).get("height", 600)

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
                        width=item.get("geometry", {}).get("width", 100),
                        height=item.get("geometry", {}).get("height", 100)
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

    async def get_frame_geometry_and_contents(self, frame_title: str) -> dict:
        all_items = await self.get_all_items()
        target_frame = None
        
        for item in all_items:
            if item.get("type") == "frame" and item.get("data", {}).get("title", "").lower() == frame_title.lower():
                target_frame = item
                break
                
        if not target_frame:
            return {}
            
        f_x = target_frame["position"]["x"]
        f_y = target_frame["position"]["y"]
        f_w = target_frame.get("geometry", {}).get("width", 0) or target_frame.get("size", {}).get("width", 800)
        f_h = target_frame.get("geometry", {}).get("height", 0) or target_frame.get("size", {}).get("height", 600)
        
        left = f_x - (f_w / 2)
        right = f_x + (f_w / 2)
        top = f_y - (f_h / 2)
        bottom = f_y + (f_h / 2)
        
        inner_elements = []
        for item in all_items:
            if item.get("id") == target_frame["id"]:
                continue
            i_x = item.get("position", {}).get("x", 0)
            i_y = item.get("position", {}).get("y", 0)
            
            if left <= i_x <= right and top <= i_y <= bottom:
                inner_elements.append({
                    "type": item.get("type"),
                    "text": item.get("data", {}).get("content", item.get("data", {}).get("title", "")),
                    "x": i_x,
                    "y": i_y
                })
                
        return {
            "frame_coords": {"x": f_x, "y": f_y, "width": f_w, "height": f_h},
            "bounds": {"left": left, "right": right, "top": top, "bottom": bottom},
            "existing_elements": inner_elements
        }

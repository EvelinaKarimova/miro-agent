import os
import json
import config
from aiogram import Router, types
from aiogram.filters import Command
from app.ai_agent import AIAgent
from app.miro_client import MiroClient

# Initialize router, AI agent, and Miro client instance
router = Router()
ai_agent = AIAgent()
miro_client = MiroClient()

# Path to the local JSON storage for persistence between restarts
CONTEXT_FILE = "active_zone_state.json"

def load_active_zone() -> dict or None:
    """Loads saved active zone metadata from disk upon startup."""
    if os.path.exists(CONTEXT_FILE):
        try:
            with open(CONTEXT_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
    return None

def save_active_zone(zone_data: dict or None):
    """Saves or flushes the active zone metadata to disk for persistence."""
    if zone_data is None:
        if os.path.exists(CONTEXT_FILE):
            os.remove(CONTEXT_FILE)
    else:
        with open(CONTEXT_FILE, "w", encoding="utf-8") as f:
            json.dump(zone_data, f, ensure_ascii=False, indent=4)

# Initialize application memory state from the state file
CURRENT_CONTEXT = {
    "active_zone": load_active_zone()
}

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    """Handles the /start command and validates previous session data."""
    welcome_text = (
        "Hi! I am your AI Miro Assistant.\n"
        "Tell me what to do with the board in natural language.\n\n"
    )
    
    saved_zone = CURRENT_CONTEXT["active_zone"]
    if saved_zone:
        welcome_text += (
            f"🧠 <b>I remembered your previous session!</b>\n"
            f"We left off working inside the zone: <b>'{saved_zone['name']}'</b>.\n"
            f"I will continue placing new elements there.\n\n"
        )
    else:
        welcome_text += "No active zone is currently selected. Working around center (0,0).\n\n"

    await message.answer(welcome_text)

@router.message()
async def handle_user_prompt(message: types.Message):
    """Main routing engine that funnels user natural language input straight to the LLM agent."""

    # === SECURITY CHECK ===
    if message.from_user.id not in config.ALLOWED_USERS:
        await message.answer("⛔ <b>Access Denied.</b> You are not authorized to control this Miro board.")
        return

    user_text = message.text
    
    thinking_msg = await message.answer("Thinking...")
    # Process message via LLM, passing current session spatial awareness data
    messages, ai_response = await ai_agent.process_message(user_text, active_zone=CURRENT_CONTEXT["active_zone"])

    # If the LLM chooses to chat back with text instead of calling API tools
    if not ai_response.tool_calls:
        try:
            await thinking_msg.delete()
        except Exception:
            pass
        await message.answer(ai_response.content)
        return

    await message.answer(f"Executing {len(ai_response.tool_calls)} action(s)...")

    # Saving response to history 
    messages.append(ai_response)

    # Iterate through batch commands issued by the AI
    for tool_call in ai_response.tool_calls:
        function_name = tool_call.function.name
        arguments = json.loads(tool_call.function.arguments)
        execution_result = "Success"

        try:
            # === Session Context Focus Management tool execution ===
            if function_name == "set_active_zone":
                target_zone = arguments.get("zone_name")
                
                if target_zone is None:
                    # User requested to clear out spatial anchoring context
                    CURRENT_CONTEXT["active_zone"] = None
                    save_active_zone(None)
                    await message.answer("Active zone reset. Working around center (0,0).")
                    execution_result = "Active zone cleared successfully."
                else:
                    # Fetch frames from Miro to resolve physical board coordinates
                    all_items = await miro_client.get_all_items()
                    found_item = None
                    
                    # Checking for name strictly
                    for item in all_items:
                        if isinstance(item, dict) and item.get("type") == "frame":
                            title = item.get("data", {}).get("title", "")
                            if title.lower() == target_zone.lower():
                                found_item = item
                                break
                    
                    # Checking substrings
                    if not found_item:
                        for item in all_items:
                            if isinstance(item, dict) and item.get("type") == "frame":
                                title = item.get("data", {}).get("title", "")
                                if target_zone.lower() in title.lower() or title.lower() in target_zone.lower():
                                    found_item = item
                                    break
                                    
                    if found_item:
                        zone_data = {
                            "name": found_item["data"]["title"],
                            "x": found_item["position"]["x"],
                            "y": found_item["position"]["y"]
                        }
                        CURRENT_CONTEXT["active_zone"] = zone_data
                        save_active_zone(zone_data)
                        await message.answer(f"Active zone successfully switched to <b>'{found_item['data']['title']}'</b>.")
                        execution_result = f"Successfully switched to zone {found_item['data']['title']}"
                    else:
                        await message.answer(f"AI requested to switch to zone '{target_zone}', but no matching frame exists on the Miro board.")
                        execution_result = f"Error: Zone '{target_zone}' not found on the board."
                        
            elif function_name == "inspect_frame_geometry":
                frame_name = arguments.get("frame_name")
                geo_data = await miro_client.get_frame_geometry_and_contents(frame_name)
                if geo_data:
                    execution_result = json.dumps(geo_data, ensure_ascii=False)
                else:
                    execution_result = f"Error: Frame '{frame_name}' was not found on the board."

            # === Native Miro Canvas Element Modifications tools ===
            elif function_name == "create_shape":
                await miro_client.create_shape(**arguments)
                execution_result = f"Shape with text '{arguments.get('text')}' created successfully."
            elif function_name == "delete_shape":
                execution_result = await miro_client.delete_shape(**arguments)
                await message.answer(execution_result)
            elif function_name == "update_shape":
                f_text = arguments.pop("find_text", "")
                f_color = arguments.pop("find_color", "")
                execution_result = await miro_client.update_shape(find_text=f_text, find_color=f_color, **arguments)
                await message.answer(execution_result)
                
            elif function_name == "create_sticker":
                await miro_client.create_sticker(**arguments)
                execution_result = f"Sticker with text '{arguments.get('text')}' created successfully."
            elif function_name == "delete_sticker":
                execution_result = await miro_client.delete_sticker(**arguments)
                await message.answer(execution_result)
            elif function_name == "update_sticker":
                f_text = arguments.pop("find_text", "")
                f_color = arguments.pop("find_color", "")
                execution_result = await miro_client.update_sticker(find_text=f_text, find_color=f_color, **arguments)
                await message.answer(execution_result)
                
            elif function_name == "create_zone":
                await miro_client.create_zone(**arguments)
                execution_result = f"Zone '{arguments.get('zone_name')}' created successfully."
            elif function_name == "delete_zone":
                execution_result = await miro_client.delete_zone(**arguments)
                await message.answer(execution_result)
            elif function_name == "copy_zone":
                execution_result = await miro_client.copy_zone(**arguments)
                await message.answer(execution_result)
                
            elif function_name == "get_board_elements":
                target_zone_name = arguments.get("zone_name")
                target_type = arguments.get("element_type")
                
                status_msg = "🔍 Reading board: "
                if target_type: status_msg += f"searching for {target_type}s "
                if target_zone_name: status_msg += f"inside zone '{target_zone_name}'"
                await message.answer(status_msg if target_type or target_zone_name else "🔍 Reading elements from the entire Miro board...")
                
                # Getting all the board items
                raw_items = await miro_client.get_all_items()
                
                non_frame_items = []
                if isinstance(raw_items, list):
                    non_frame_items = [i for i in raw_items if isinstance(i, dict) and i.get("type") != "frame"]
                else:
                    raw_items = []
                
                # If the frame is set then scanning it
                target_frame = None
                if target_zone_name:
                    for item in raw_items:
                        if isinstance(item, dict) and item.get("type") == "frame" and item.get("data", {}).get("title", "").lower() == target_zone_name.lower():

                            target_frame = item
                            break
                
                cleaned_items = []
                if target_zone_name and not target_frame:
                    execution_result = f"Error: Zone '{target_zone_name}' was not found on the board."
                else:
                    if target_zone_name and not target_frame:
                        execution_result = f"Error: Zone '{target_zone_name}' was not found on the board."
                    else:
                    # Calculating frame borders
                        left_bound, right_bound, top_bound, bottom_bound = 0, 0, 0, 0
                        if target_frame:
                            f_pos = target_frame.get("position", {})
                            f_x = f_pos.get("x", 0) if isinstance(f_pos, dict) else 0
                            f_y = f_pos.get("y", 0) if isinstance(f_pos, dict) else 0

                            f_w = target_frame.get("geometry", {}).get("width", 0) or target_frame.get("size", {}).get("width", 400)
                            f_h = target_frame.get("geometry", {}).get("height", 0) or target_frame.get("size", {}).get("height", 400)

                            left_bound = f_x - (f_w / 2)
                            right_bound = f_x + (f_w / 2)
                            top_bound = f_y - (f_h / 2)
                            bottom_bound = f_y + (f_h / 2)

                    for item in raw_items:
                        if not isinstance(item, dict):
                            continue

                        item_type = item.get("type", "unknown")
                        
                        # Filter by target type
                        if target_type:
                            miro_type_check = "sticky_note" if target_type == "sticker" else target_type
                            if item_type != miro_type_check:
                                continue

                        if target_frame and item.get("id") == target_frame.get("id"):
                            continue
                            
                        item_data = item.get("data", {})
                        if not isinstance(item_data, dict):
                            item_data = {}
                            
                        # Collecting text from widgets
                        item_text = item_data.get("content", item_data.get("title", ""))
                        
                        
                        if not item_text and "fields" in item.get("data", {}):
                            fields_data = [str(f.get("value", "")) for f in item["data"]["fields"] if f.get("value")]
                            item_text = " | ".join(fields_data)
                        
                        if not item_text and "text" in item_data:
                            item_text = item_data.get("text", "")

                        # === TIMELINE / GANTT PARSER ===
                        if item_type in ["timeline", "gantt_chart", "kanban"] or "records" in item_data:
                            records = item_data.get("records", [])
                            if isinstance(records, list):
                                timeline_tasks = []
                                for rec in records:
                                    if isinstance(rec, dict):
                                        t_title = rec.get("title", rec.get("content", "Task"))
                                        t_start = rec.get("start_date", rec.get("startDate", ""))
                                        t_end = rec.get("end_date", rec.get("endDate", ""))
                                        t_status = rec.get("status", "")
                                        
                                        task_info = f"[{t_title} | Сроки: {t_start} - {t_end}"
                                        if t_status:
                                            task_info += f" | Статус: {t_status}"
                                        task_info += "]"
                                        timeline_tasks.append(task_info)
                                
                                if timeline_tasks:
                                    item_text = f"Timeline '{item_data.get('title', 'Roadmap')}' Tasks: " + " ; ".join(timeline_tasks)

                        pos = item.get("position", {})
                        if not isinstance(pos, dict):
                            pos = {}
                        i_x = pos.get("x", 0)
                        i_y = pos.get("y", 0)
                        
                        # Filter by target frame
                        if target_frame:
                            is_inside = (left_bound <= i_x <= right_bound) and (top_bound <= i_y <= bottom_bound)
                            if not is_inside:
                                continue
                        # If the object is a frame then collect digest from inner objects
                        if item_type == "frame":
                            frame_format = item_data.get("format", {})
                            if not isinstance(frame_format, dict):
                                frame_format = {}
                            f_w = frame_format.get("width", 0) or item.get("geometry", {}).get("width", 0) or 400
                            f_h = frame_format.get("height", 0) or item.get("geometry", {}).get("height", 0) or 400
                            
                            f_left = i_x - (f_w / 2)
                            f_right = i_x + (f_w / 2)
                            f_top = i_y - (f_h / 2)
                            f_bottom = i_y + (f_h / 2)

                            
                            inner_contents = []
                            for sub_item in non_frame_items:
                                if not isinstance(sub_item, dict):
                                    continue
                                    
                                s_pos = sub_item.get("position", {})
                                if not isinstance(s_pos, dict):
                                    s_pos = {}
                                s_x = s_pos.get("x", 0)
                                s_y = s_pos.get("y", 0)
                                
                                if f_left <= s_x <= f_right and f_top <= s_y <= f_bottom:
                                    s_data = sub_item.get("data", {})
                                    if not isinstance(s_data, dict):
                                        s_data = {}
                                    sub_text = s_data.get("content", s_data.get("title", ""))
                                    if not sub_text and "fields" in s_data and isinstance(s_data["fields"], list):
                                        sub_text = " | ".join([str(f.get("value", "")) for f in s_data["fields"] if isinstance(f, dict) and f.get("value")])
                                    if sub_text:
                                        inner_contents.append(sub_text[:40]) 
                            
                            if inner_contents:
                                item_text = f"{item_text} [Sub-contents: {', '.join(inner_contents[:5])}]"

                        if not item_text or item_text.strip() == "|":
                            continue

                        cleaned_items.append({
                            "id": item.get("id"),
                            "type": item_type,
                            "text": item_text,
                            "x": i_x,
                            "y": i_y
                        })
                    await thinking_msg.delete()
                    execution_result = json.dumps(cleaned_items, ensure_ascii=False)
        except Exception as e:
            execution_result = json.dumps({"error": str(e)}, ensure_ascii=False)
            await message.answer(f"Error executing {function_name}: {str(e)}")

        messages.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "name": function_name,
            "content": str(execution_result)
        })

    try:
        await thinking_msg.delete()
    except Exception:
        pass

    await message.answer("Done! Sending results back to AI...")

    final_response = await ai_agent.get_final_answer(messages)
    await message.answer(final_response.content)

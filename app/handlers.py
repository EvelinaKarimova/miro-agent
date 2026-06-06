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
    
    await message.answer("Thinking...")
    # Process message via LLM, passing current session spatial awareness data
    messages, ai_response = await ai_agent.process_message(user_text, active_zone=CURRENT_CONTEXT["active_zone"])

    # If the LLM chooses to chat back with text instead of calling API tools
    if not ai_response.tool_calls:
        await message.answer(ai_response.content)
        return

    await message.answer(f"Executing {len(ai_response.tool_calls)} action(s)...")
    
    # Functions results to return to the agent
    tool_outputs = []

    # Saving response to history 
    messages.append(ai_response)

    # Iterate through batch commands issued by the AI
    for tool_call in ai_response.tool_calls:
        function_name = tool_call.function.name
        arguments = json.loads(tool_call.function.arguments)
        execution_result = ""

        try:
            # === Session Context Focus Management tool execution ===
            if function_name == "set_active_zone":
                target_zone = arguments.get("zone_name")
                
                if target_zone is None:
                    # User requested to clear out spatial anchoring context
                    CURRENT_CONTEXT["active_zone"] = None
                    save_active_zone(None)
                    await message.answer("Active zone reset. Working around center (0,0).")
                else:
                    # Fetch frames from Miro to resolve physical board coordinates
                    all_items = await miro_client.get_all_items()
                    found = False
                    for item in all_items:
                        if item.get("type") == "frame" and item.get("data", {}).get("title", "").lower() == target_zone.lower():
                            zone_data = {
                                "name": item["data"]["title"],
                                "x": item["position"]["x"],
                                "y": item["position"]["y"]
                            }
                            CURRENT_CONTEXT["active_zone"] = zone_data
                            save_active_zone(zone_data)
                            await message.answer(f"Active zone successfully switched to <b>'{item['data']['title']}'</b>.")
                            found = True
                            break
                    if not found:
                        await message.answer(f"AI requested to switch to zone '{target_zone}', but no such frame exists on the Miro board.")

            # === Native Miro Canvas Element Modifications tools ===
            elif function_name == "create_shape":
                await miro_client.create_shape(**arguments)
            elif function_name == "delete_shape":
                result = await miro_client.delete_shape(**arguments)
                await message.answer(result)
            elif function_name == "update_shape":
                f_text = arguments.pop("find_text", "")
                f_color = arguments.pop("find_color", "")
                result = await miro_client.update_shape(find_text=f_text, find_color=f_color, **arguments)
                await message.answer(result)
                
            elif function_name == "create_sticker":
                await miro_client.create_sticker(**arguments)
            elif function_name == "delete_sticker":
                result = await miro_client.delete_sticker(**arguments)
                await message.answer(result)
            elif function_name == "update_sticker":
                f_text = arguments.pop("find_text", "")
                f_color = arguments.pop("find_color", "")
                result = await miro_client.update_sticker(find_text=f_text, find_color=f_color, **arguments)
                await message.answer(result)
                
            elif function_name == "create_zone":
                await miro_client.create_zone(**arguments)
            elif function_name == "delete_zone":
                result = await miro_client.delete_zone(**arguments)
                await message.answer(result)
            elif function_name == "copy_zone":
                result = await miro_client.copy_zone(**arguments)
                await message.answer(result)
            elif function_name == "get_board_elements":
                target_zone_name = arguments.get("zone_name")
                target_type = arguments.get("element_type")
                
                status_msg = "🔍 Reading board: "
                if target_type: status_msg += f"searching for {target_type}s "
                if target_zone_name: status_msg += f"inside zone '{target_zone_name}'"
                await message.answer(status_msg if target_type or target_zone_name else "🔍 Reading elements from the entire Miro board...")
                
                # Getting all the board items
                raw_items = await miro_client.get_all_items()
                
                # If the frame is set then scanning it
                target_frame = None
                if target_zone_name:
                    for item in raw_items:
                        if item.get("type") == "frame" and item.get("data", {}).get("title", "").lower() == target_zone_name.lower():
                            target_frame = item
                            break
                
                cleaned_items = []
                
                if target_zone_name and not target_frame:
                    execution_result = f"Error: Zone '{target_zone_name}' was not found on the board."
                else:
                    # Calculating frame borders
                    if target_frame:
                        f_x = target_frame["position"]["x"]
                        f_y = target_frame["position"]["y"]
                        f_w = target_frame.get("geometry", {}).get("width", 0) or target_frame.get("size", {}).get("width", 400)
                        f_h = target_frame.get("geometry", {}).get("height", 0) or target_frame.get("size", {}).get("height", 400)
                        
                        left_bound = f_x - (f_w / 2)
                        right_bound = f_x + (f_w / 2)
                        top_bound = f_y - (f_h / 2)
                        bottom_bound = f_y + (f_h / 2)

                    for item in raw_items:
                        item_type = item.get("type", "unknown")
                        
                        # Filter by target type
                        if target_type:
                            miro_type_check = "sticky_note" if target_type == "sticker" else target_type
                            if item_type != miro_type_check:
                                continue

                        if target_frame and item.get("id") == target_frame.get("id"):
                            continue
                            
                        item_text = item.get("data", {}).get("content", item.get("data", {}).get("title", ""))
                        pos = item.get("position", {})
                        i_x = pos.get("x", 0)
                        i_y = pos.get("y", 0)
                        
                        # Filter by target frame
                        if target_frame:
                            is_inside = (left_bound <= i_x <= right_bound) and (top_bound <= i_y <= bottom_bound)
                            if not is_inside:
                                continue
                        
                        cleaned_items.append({
                            "id": item.get("id"),
                            "type": item_type,
                            "text": item_text,
                            "x": i_x,
                            "y": i_y
                        })
                    
                    execution_result = json.dumps(cleaned_items, ensure_ascii=False)
        except Exception as e:
            await message.answer(f"Error executing {function_name}: {str(e)}")

        messages.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "name": function_name,
            "content": execution_result
        })

    await message.answer("Done! Sending results back to AI...")

    # Sending function execution result to the agent
    final_response = await ai_agent.get_final_answer(messages)
    
    # Answer to the user
    await message.answer(final_response.content)

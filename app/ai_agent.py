from typing import Optional
import openai
from openai import OpenAI
from pydantic import BaseModel, Field
import config

# =====================================================================
# Shapes contracts (Customizable sizes, text, borders)
# =====================================================================
class CreateShapeSchema(BaseModel):
    text: str = Field(description="Text to be written inside the shape. Keep it concise.")
    color: str = Field(description="The background fill color of the shape in HEX format.")
    font_color: str = Field(default="#000000", description="The text color in HEX format.")
    x: int = Field(default=0, description="The X coordinate. Increment by 150-200 for sequential shapes.")
    y: int = Field(default=0, description="The Y coordinate.")
    width: int = Field(default=100, description="Custom width in pixels. Use 200+ for large shapes, banners, or boxes.")
    height: int = Field(default=100, description="Custom height in pixels.")

class DeleteShapeSchema(BaseModel):
    text_query: str = Field(default="", description="Text or substring on the shape to delete. Leave empty if searching by color only.")
    color_query: str = Field(default="", description="HEX or color description of the shape to delete.")

class UpdateShapeSchema(BaseModel):
    find_text: str = Field(default="", description="Text or substring of the shape(s) to update.")
    find_color: str = Field(default="", description="Color description or HEX of the shape(s) to update.")
    new_text: Optional[str] = Field(default=None, description="New text content.")
    new_color: Optional[str] = Field(default=None, description="New fill color in HEX format.")
    new_width: Optional[int] = Field(default=None, description="New width in pixels.")
    new_height: Optional[int] = Field(default=None, description="New height in pixels.")
    new_x: Optional[int] = Field(default=None, description="New X coordinate.")
    new_y: Optional[int] = Field(default=None, description="New Y coordinate.")


# =====================================================================
# Sticky notes contracts (Fixed proportions, special Miro system colors)
# =====================================================================
class CreateStickerSchema(BaseModel):
    text: str = Field(description="The text content inside the sticky note.")
    color: str = Field(
        default="light_yellow",
        description=(
            "Miro system color name for the sticky note. Supported values: "
            "'gray', 'black', 'light_yellow', 'yellow', 'orange', 'light_green', 'green', "
            "'dark_green', 'cyan', 'blue', 'dark_blue', 'violet', 'magenta', 'pink', 'red'."
        )
    )
    x: int = Field(default=0, description="The X coordinate. Standard spacing between stickers is around 250 units.")
    y: int = Field(default=0, description="The Y coordinate.")
    shape: str = Field(
        default="square",
        description="The type/shape of the sticky note. Allowed values: 'square' (1:1 aspect ratio) or 'rectangle' (4:3 aspect ratio)."
    )

class DeleteStickerSchema(BaseModel):
    text_query: str = Field(default="", description="Text or substring on the sticky note to delete.")
    color_query: str = Field(default="", description="Miro system color name of the sticky note to delete.")

class UpdateStickerSchema(BaseModel):
    find_text: str = Field(default="", description="Text or substring of the sticky note(s) to update.")
    find_color: str = Field(default="", description="Miro system color name of the sticky note(s) to update.")
    new_text: Optional[str] = Field(default=None, description="New text content.")
    new_color: Optional[str] = Field(default=None, description="New Miro system color name.")
    new_shape: Optional[str] = Field(default=None, description="Change shape to 'square' or 'rectangle'.")
    new_x: Optional[int] = Field(default=None, description="Move to new X coordinate.")
    new_y: Optional[int] = Field(default=None, description="Move to new Y coordinate.")


# =====================================================================
# Zone\Frame contracts
# =====================================================================
class CreateZoneSchema(BaseModel):
    zone_name: str = Field(description="The title/name of the new working zone or frame.")
    x: int = Field(default=0, description="The X coordinate for the center of the new zone.")
    y: int = Field(default=0, description="The Y coordinate for the center of the new zone.")
    width: int = Field(default=800, description="The width of the zone/frame. Default is 800.")
    height: int = Field(default=600, description="The height of the zone/frame. Default is 600.")

class DeleteZoneSchema(BaseModel):
    zone_name: str = Field(description="The exact name of the zone/frame to delete.")

class CopyZoneSchema(BaseModel):
    source_zone_name: str = Field(description="The exact name of the existing zone to copy.")
    new_zone_name: str = Field(description="The name/title for the new duplicated zone.")

class SetActiveZoneSchema(BaseModel):
    zone_name: Optional[str] = Field(
        default=None,
        description=(
            "The exact name of the zone (frame) the user wants to switch their attention to. "
            "If the user explicitly asks to reset, clear, or forget the current active zone, set this to None."
        )
    )

# =====================================================================
# Ai agent logic
# =====================================================================
class AIAgent:
    def __init__(self):
        self.client = OpenAI(api_key=config.OPENAI_API_KEY,  base_url=config.OPENAI_BASE_URL)
        
    def _get_tools(self):
        return [
            # Shapes
            openai.pydantic_function_tool(model=CreateShapeSchema, name="create_shape", description="Creates a customizable geometric shape with arbitrary width/height and HEX colors."),
            openai.pydantic_function_tool(model=DeleteShapeSchema, name="delete_shape", description="Deletes shapes based on text or HEX colors."),
            openai.pydantic_function_tool(model=UpdateShapeSchema, name="update_shape", description="Modifies coordinates, text, custom dimensions, or HEX colors of shapes."),
            
           # Sticky notes
            openai.pydantic_function_tool(model=CreateStickerSchema, name="create_sticker", description="Creates a classic Miro sticky note using standard system color palettes and fixed square/rectangle ratios."),
            openai.pydantic_function_tool(model=DeleteStickerSchema, name="delete_sticker", description="Deletes classic sticky notes by text or Miro system color names."),
            openai.pydantic_function_tool(model=UpdateStickerSchema, name="update_sticker", description="Modifies content, positioning, or standard system colors of classic sticky notes."),
            
            # Zones
            openai.pydantic_function_tool(model=CreateZoneSchema, name="create_zone", description="Creates a named frame (working zone)."),
            openai.pydantic_function_tool(model=DeleteZoneSchema, name="delete_zone", description="Deletes an entire frame by name."),
            openai.pydantic_function_tool(model=CopyZoneSchema, name="copy_zone", description="Duplicates a frame along with all content inside it."),
             openai.pydantic_function_tool(model=SetActiveZoneSchema, name="set_active_zone", description="Switches the current active working zone (frame) focus or resets it completely.")
        ]

    async def process_message(self, user_text: str, active_zone: dict = None):
        system_instruction = (
            "You are an intelligent Miro board administrator. Your goal is to manage the board canvas, "
            "keeping the layout neat, structured, and visually appealing. Analyze the user's prompt "
            "and invoke the necessary tools. You can call tools for single or mass/batch operations. "
            "You are allowed to call multiple tools sequentially or simultaneously. "
            "If the user is just chatting and doesn't require any board modification, respond with plain text."
            "Carefully choose whether to use 'shapes' or 'sticky notes' based on user intent. If the user explicitly asks for classic 'stickers'"
            "or implies fixed post-it notes, use sticky tools. If they mention banners, blocks, arbitrary dimensions, "
            "or customizable boxes, use shape tools. Keep layouts organized and adjust positioning relative to active zones if provided."
        )
        
        if active_zone:
            system_instruction += (
                f"\n\nCRITICAL CONTEXT: Active frame '{active_zone['name']}' center is X: {active_zone['x']}, Y: {active_zone['y']}. "
                f"Calculate new elements coordinates relative to this zone."
            )

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_text}
            ],
            tools=self._get_tools()
        )
        return response.choices.message
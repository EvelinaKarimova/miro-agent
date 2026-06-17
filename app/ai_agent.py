from typing import Literal, Optional
import openai
from openai import AsyncOpenAI
from pydantic import BaseModel, Field
import config
from datetime import date


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

class InspectFrameGeometrySchema(BaseModel):
    frame_name: str = Field(description="The name of the frame to inspect its dimensions and object positions for layout planning.")


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

class GetBoardElementsSchema(BaseModel):
    zone_name: Optional[str] = Field(default=None, description="The name of the specific frame (zone) to look inside. If not provided, inspects the whole canvas.")
    element_type: Optional[Literal["sticker", "shape", "frame"]] = Field(
        default=None, 
        description="CRITICAL: Leave this field EMPTY (None) if you want to scan the whole board or see all object types together. ONLY fill this if the user explicitly asked for ONE specific type."
    )

GetBoardElementsSchema.model_rebuild()
InspectFrameGeometrySchema.model_rebuild()


# =====================================================================
# Ai agent logic
# =====================================================================
class AIAgent:
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=config.OPENAI_API_KEY,
            base_url=config.OPENAI_BASE_URL
        )
        
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
            openai.pydantic_function_tool(model=SetActiveZoneSchema, name="set_active_zone", description="Switches the current active working zone (frame) focus or resets it completely."),
            
            # Inspection & Layout mapping
            openai.pydantic_function_tool(model=GetBoardElementsSchema, name="get_board_elements", description="Use this tool to read, count, or inspect existing elements (stickers, shapes, frames) on the board. You can filter by 'zone_name' to look inside a specific frame, and/or by 'element_type' to search only for specific objects like frames or sticky notes."),       
            openai.pydantic_function_tool(model=InspectFrameGeometrySchema, name="inspect_frame_geometry", description="Use this tool to get exact frame boundaries and coordinates of all items inside it before choosing coordinates for new items.")

        ]

    async def process_message(self, user_text: str, active_zone: dict = None):
        # What is the date today
        current_date_str = date.today().strftime("%d.%m.%Y")
        current_weekday = date.today().strftime("%A")

        system_instruction = (
            "You are an intelligent Miro board administrator with flawless spatial awareness, geometric reasoning, and semantic understanding.\n\n"
            "Use this baseline to dynamically parse any relative time constraints, dates, or deadlines from user prompts.\n\n"
            f"CURRENT TEMPORAL CONTEXT: Today is {current_weekday}, {current_date_str}.\n"
            "SEMANTIC MATCHING & SEARCH RULES:\n"
            "- Canvas elements and working zones may have implicit meaning derived entirely from their content rather than literal titles. "
            "When the user references a specific domain, project view, or functional area (such as a backlog, timeline, or roadmap), "
            "always invoke 'get_board_elements' to extract the complete canvas hierarchy first.\n"
            "- Analyze the inner contents, text values, statuses, and structure of elements residing inside each zone. "
            "Match the user's high-level intent with the most logically relevant frame or object cluster based on context. "
            "Proceed with execution immediately once a strong semantic association is discovered, avoiding unnecessary clarification requests.\n\n"
            "SPATIAL LAYOUT & OBJECT POSITIONING RULES:\n"
            "- Before placing, aligning, or mass-arranging elements inside any existing frame or area, ALWAYS invoke 'inspect_frame_geometry' to acquire its exact physical boundaries and a map of occupied space.\n"
            "- Treat the frame as a bounded coordinate bounding box. Calculate coordinates (X, Y) for new elements dynamically so they are distributed logically, evenly, and fit entirely within the frame's left/right/top/bottom boundaries.\n"
            "- Always factor in the sizes of new and existing objects. Never allow elements to overlap, stack directly on top of each other, or collide, unless explicitly requested.\n"
            "- Adapt the structure layout natively to the user's implicit intent: analyze the structural pattern of existing elements and naturally continue or complete the pattern using clean grid math.\n\n"
            "UNIVERSAL TOOL ROUTING:\n"
            "- READ/INSPECT: For all information retrieval, search, date filtering, counting, or presence verification, use a SINGLE call to 'get_board_elements' with 'element_type' left empty to fetch everything at once.\n"
            "- CONTEXT/ATTENTION: To lock, clear, or shift your active working focus to a specific canvas area, use 'set_active_zone'.\n"
            "- MUTATIONS: For state-changing operations, invoke the precise create/delete/update tool required.\n\n"
            "Operational guidelines: Rely strictly on tool outputs as your source of truth. Do not invent coordinates or make assumptions about the board layout."
        )
        
        if active_zone:
            system_instruction += (
                f"\n\nCRITICAL CONTEXT: Active frame '{active_zone['name']}' center is X: {active_zone['x']}, Y: {active_zone['y']}. "
                f"Calculate new elements coordinates relative to this zone."
            )

        # Creating messages array
        messages = [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": user_text}
        ]

        response = await self.client.chat.completions.create(
            model=config.OPENAI_MODEL,
            messages=messages,
            tools=self._get_tools()
        )
        return messages, response.choices[0].message


    async def get_final_answer(self, messages: list):
        """Final answer"""
        response = await self.client.chat.completions.create(
            model=config.OPENAI_MODEL,
            messages=messages
        )
        return response.choices[0].message
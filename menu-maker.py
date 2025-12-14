#!/usr/bin/env python3
"""
Menu Maker - Enhanced categorized menu system
Features: Categories, Info display, Collapse/Expand, Theme selection
"""

import os
import subprocess
import json
import copy
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import Vertical, Horizontal, Container, ScrollableContainer
from textual.widgets import Header, Footer, Static, Button, Input, Label, TextArea, Checkbox
from textual.binding import Binding
from textual.screen import Screen
from textual.reactive import reactive


DEFAULT_COLOR_PAIRS = [
    {"name": "Teal Glow", "background": "#034e68", "text": "#caf0f8"},
    {"name": "Amber Pop", "background": "#6f1d1b", "text": "#ffe5d9"},
    {"name": "Purple Mist", "background": "#240046", "text": "#f8f9fa"},
    {"name": "Forest Tones", "background": "#283618", "text": "#fefae0"},
    {"name": "Slate Shine", "background": "#2b2d42", "text": "#edf2f4"},
]


def normalize_hex_color(value: Optional[str]) -> Optional[str]:
    """Normalize a hex color string to #RRGGBB."""
    if not value or not isinstance(value, str):
        return None
    color = value.strip().lower()
    if not color:
        return None
    if not color.startswith("#"):
        color = f"#{color}"
    if len(color) != 7:
        return None
    try:
        int(color[1:], 16)
    except ValueError:
        return None
    return color


def sanitize_color_pair(color_pair: Optional[Dict[str, str]]) -> Optional[Dict[str, str]]:
    """Validate and normalize a color pair dict."""
    if not color_pair or not isinstance(color_pair, dict):
        return None
    background = normalize_hex_color(color_pair.get("background"))
    text = normalize_hex_color(color_pair.get("text"))
    if background and text:
        return {"background": background, "text": text}
    return None


class InfoScreen(Screen):
    """Screen for displaying app information."""
    
    BINDINGS = [
        Binding("escape,i,enter", "close", "Close"),
    ]
    
    def __init__(self, item_data: Dict[str, str]):
        super().__init__()
        self.item_data = item_data
    
    def compose(self) -> ComposeResult:
        """Create info screen layout."""
        with Container(classes="info-container"):
            yield Label("Application Information", classes="info-title")
            yield Label(f"Label: {self.item_data.get('label', 'N/A')}", classes="info-field")
            yield Label(f"Command: {self.item_data.get('cmd', 'N/A')}", classes="info-field")
            yield Label(f"Category: {self.item_data.get('category', 'N/A')}", classes="info-field")
            yield Label("", classes="info-spacer")
            yield Label("Description:", classes="info-label")
            yield Label(f"{self.item_data.get('info', 'No description available')}", classes="info-description")
            yield Label("", classes="info-spacer")
            with Horizontal(classes="button-row"):
                yield Button("Close", id="close", variant="primary")
    
    def action_close(self) -> None:
        """Close the info screen."""
        self.dismiss()
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "close":
            self.dismiss()


class EditTitleScreen(Screen):
    """Screen for editing the application title."""
    
    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("ctrl+s", "save", "Save"),
    ]
    
    def __init__(self, current_title: str):
        super().__init__()
        self.current_title = current_title
    
    def compose(self) -> ComposeResult:
        """Create title edit screen layout."""
        with Container(classes="edit-container"):
            yield Label("Edit Application Title", classes="edit-title")
            
            yield Label("Application Title:")
            yield Input(value=self.current_title, id="title_input")
            
            with Horizontal(classes="button-row"):
                yield Button("Save", id="save", variant="primary")
                yield Button("Cancel", id="cancel")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "save":
            self.action_save()
        elif event.button.id == "cancel":
            self.action_cancel()
    
    def action_save(self) -> None:
        """Save the title."""
        title_input = self.query_one("#title_input", Input)
        new_title = title_input.value.strip()
        
        if new_title:
            self.dismiss({"action": "save", "title": new_title})
        else:
            self.dismiss({"action": "cancel"})
    
    def action_cancel(self) -> None:
        """Cancel editing."""
        self.dismiss({"action": "cancel"})


class EditCategoryScreen(Screen):
    """Screen for editing category names and colors."""
    
    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("ctrl+s", "save", "Save"),
    ]
    
    def __init__(
        self,
        old_category_name: str,
        category_colors: Optional[Dict[str, str]],
        available_colors: List[Dict[str, str]],
        existing_categories: List[str],
        max_columns: int,
        current_column: int
    ):
        super().__init__()
        self.old_category_name = old_category_name
        self.category_colors = sanitize_color_pair(category_colors) or {}
        self.available_colors = copy.deepcopy(available_colors) if available_colors else []
        self.existing_categories = existing_categories
        self.palette_render_id = 0
        self.max_columns = max(1, max_columns)
        self.category_column = max(1, min(self.max_columns, current_column or 1))
        self.current_palette: List[Dict[str, str]] = []
    
    def compose(self) -> ComposeResult:
        """Create category edit screen layout."""
        with Container(classes="edit-container"):
            yield Label("Edit Category", classes="edit-title")
            
            yield Label("Category Name:")
            yield Input(value=self.old_category_name, id="category_input")
            
            yield Label(f"Column (1-{self.max_columns}):")
            yield Input(value=str(self.category_column), id="column_input", placeholder="1")
            
            yield Label("Color Presets (click to use):")
            with ScrollableContainer(classes="color-palette", id="palette_container"):
                palette_entries = self._build_palette_entries()
                self.palette_render_id += 1
                for idx, color in enumerate(palette_entries):
                    name = color.get("name") or f"Color {idx + 1}"
                    preview = f"{color.get('background', '')} / {color.get('text', '')}"
                    button_id = self._make_palette_button_id(idx)
                    yield self.create_color_button(button_id, name, preview, color)
            
            yield Label("Custom Color Name (optional):")
            yield Input(id="color_name_input", placeholder="e.g. Sunset")
            
            yield Label("Background Color (#RRGGBB):")
            yield Input(value=self.category_colors.get("background", ""), id="background_input", placeholder="#123456")
            
            yield Label("Text Color (#RRGGBB):")
            yield Input(value=self.category_colors.get("text", ""), id="text_input", placeholder="#ffffff")
            
            with Horizontal(classes="button-row"):
                yield Button("Add Custom Color", id="add_color")
            
            yield Label("", id="color_error", classes="error-message")
            
            with Horizontal(classes="button-row"):
                yield Button("Save", id="save", variant="primary")
                yield Button("Cancel", id="cancel")

    def _make_palette_button_id(self, idx: int) -> str:
        """Return a unique id for palette buttons."""
        return f"color_{self.palette_render_id}_{idx}"

    def _build_palette_entries(self) -> List[Dict[str, str]]:
        """Build palette list ensuring a minimum number of entries."""
        palette = [color.copy() for color in self.available_colors]
        seen_pairs = set()
        for color in palette:
            bg = color.get("background")
            text = color.get("text")
            if bg and text:
                seen_pairs.add((bg.lower(), text.lower()))
        for default in DEFAULT_COLOR_PAIRS:
            bg = default.get("background")
            text = default.get("text")
            if not bg or not text:
                continue
            pair = (bg.lower(), text.lower())
            if pair not in seen_pairs:
                palette.append(default.copy())
                seen_pairs.add(pair)
            if len(palette) >= 4:
                break
        while len(palette) < 4:
            palette.append({
                "name": f"Color {len(palette) + 1}",
                "background": "#034e68",
                "text": "#caf0f8"
            })
        self.current_palette = palette
        return palette

    def create_color_button(self, button_id: str, name: str, preview: str, color: Dict[str, str]) -> Button:
        """Create a color preset button styled with its colors."""
        button = Button(f"{name} — {preview}", id=button_id, classes="color-button")
        try:
            if color.get("background"):
                button.styles.background = color["background"]
            if color.get("text"):
                button.styles.color = color["text"]
        except Exception:
            pass
        return button
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id or ""
        if button_id == "save":
            self.action_save()
        elif button_id == "cancel":
            self.action_cancel()
        elif button_id == "add_color":
            self.action_add_color()
        elif button_id.startswith("color_"):
            self.apply_palette_choice(button_id)
    
    def action_add_color(self) -> None:
        """Add the current inputs as a saved color pair."""
        background = normalize_hex_color(self.query_one("#background_input", Input).value)
        text = normalize_hex_color(self.query_one("#text_input", Input).value)
        
        if not background or not text:
            self.show_error("Enter valid background and text colors (e.g. #1a2b3c).")
            return
        
        name_input = self.query_one("#color_name_input", Input)
        name = name_input.value.strip() or f"Custom {len(self.available_colors) + 1}"
        
        # Update if the pair already exists, otherwise append
        for color in self.available_colors:
            if color.get("background") == background and color.get("text") == text:
                color["name"] = name
                break
        else:
            self.available_colors.append({
                "name": name,
                "background": background,
                "text": text
            })
        
        self.clear_error()
        self.refresh_color_palette()
    
    def apply_palette_choice(self, button_id: str) -> None:
        """Apply a selected preset color to the input fields."""
        try:
            idx = int(button_id.split("_")[-1])
            palette = self.current_palette or self._build_palette_entries()
            color = palette[idx]
        except (ValueError, IndexError):
            return
        
        background_input = self.query_one("#background_input", Input)
        text_input = self.query_one("#text_input", Input)
        background_input.value = color.get("background", "")
        text_input.value = color.get("text", "")
        self.clear_error()
    
    def refresh_color_palette(self) -> None:
        """Refresh the preset color list."""
        try:
            container = self.query_one("#palette_container", ScrollableContainer)
        except Exception:
            return
        
        container.remove_children()
        self.palette_render_id += 1
        palette_entries = self._build_palette_entries()
        for idx, color in enumerate(palette_entries):
            name = color.get("name") or f"Color {idx + 1}"
            preview = f"{color.get('background', '')} / {color.get('text', '')}"
            button_id = self._make_palette_button_id(idx)
            button = self.create_color_button(button_id, name, preview, color)
            container.mount(button)
    
    def action_save(self) -> None:
        """Save the category settings."""
        category_input = self.query_one("#category_input", Input)
        new_name = category_input.value.strip()
        background_input = self.query_one("#background_input", Input)
        text_input = self.query_one("#text_input", Input)
        column_input = self.query_one("#column_input", Input)
        
        if not new_name:
            self.show_error("Category name is required.")
            return
        
        normalized_background = normalize_hex_color(background_input.value)
        normalized_text = normalize_hex_color(text_input.value)
        
        if (normalized_background and not normalized_text) or (normalized_text and not normalized_background):
            self.show_error("Provide both background and text colors or leave both blank.")
            return
        
        if (new_name != self.old_category_name and 
            new_name in [name for name in self.existing_categories if name != self.old_category_name]):
            self.show_error("Another category already uses that name.")
            return
        
        colors = None
        if normalized_background and normalized_text:
            colors = {
                "background": normalized_background,
                "text": normalized_text
            }
        
        try:
            column_value = int(column_input.value.strip())
        except (ValueError, AttributeError):
            column_value = self.category_column
        column_value = max(1, min(self.max_columns, column_value))
        
        self.clear_error()
        self.dismiss({
            "action": "save",
            "old_name": self.old_category_name,
            "new_name": new_name,
            "colors": colors,
            "column": column_value,
            "custom_colors": copy.deepcopy(self.available_colors)
        })
    
    def show_error(self, message: str) -> None:
        """Display an error message."""
        try:
            error_label = self.query_one("#color_error", Label)
            error_label.update(message)
        except Exception:
            pass
    
    def clear_error(self) -> None:
        """Clear the error message."""
        try:
            error_label = self.query_one("#color_error", Label)
            error_label.update("")
        except Exception:
            pass
    
    def action_cancel(self) -> None:
        """Cancel editing."""
        self.dismiss({"action": "cancel"})


class EditItemScreen(Screen):
    """Screen for editing menu items with all fields."""
    
    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("ctrl+s", "save", "Save"),
    ]
    
    def __init__(self, item_data: Dict[str, str], categories: List[str], item_index: int = -1):
        super().__init__()
        self.item_data = item_data.copy()
        self.categories = categories
        self.item_index = item_index
        self.current_category_index = 0
        
        # Set default category index
        if self.item_data.get('category') in categories:
            self.current_category_index = categories.index(self.item_data['category'])
    
    def compose(self) -> ComposeResult:
        """Create edit screen layout."""
        with Container(classes="edit-container"):
            title = "Edit Item" if self.item_index >= 0 else "New Item"
            yield Label(title, classes="edit-title")
            
            yield Label("Label:")
            yield Input(value=self.item_data.get('label', ''), id="label_input")
            
            yield Label("Command:")
            yield Input(value=self.item_data.get('cmd', ''), id="cmd_input")
            
            yield Label("Info/Description:")
            yield TextArea(text=self.item_data.get('info', ''), id="info_input")
            
            yield Label("Category:")
            yield Input(value=self.item_data.get('category', self.categories[0] if self.categories else 'General'), id="category_input")
            
            yield Label("Pause before returning to menu:")
            pause_value = self.item_data.get('pause', False)
            if isinstance(pause_value, str):
                pause_value = pause_value.lower() in ('true', 'yes', '1')
            yield Checkbox("Pause and wait for keypress", value=pause_value, id="pause_checkbox")
            
            with Horizontal(classes="button-row"):
                yield Button("Save", id="save", variant="primary")
                yield Button("Cancel", id="cancel")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "save":
            self.action_save()
        elif event.button.id == "cancel":
            self.action_cancel()
    
    def action_save(self) -> None:
        """Save the item data."""
        label_input = self.query_one("#label_input", Input)
        cmd_input = self.query_one("#cmd_input", Input)
        info_input = self.query_one("#info_input", TextArea)
        category_input = self.query_one("#category_input", Input)
        pause_checkbox = self.query_one("#pause_checkbox", Checkbox)
        
        result_data = {
            "label": label_input.value.strip(),
            "cmd": cmd_input.value.strip(),
            "info": info_input.text.strip(),
            "category": category_input.value.strip() or "General",
            "pause": pause_checkbox.value
        }
        
        self.dismiss({"action": "save", "data": result_data, "index": self.item_index})
    
    def action_cancel(self) -> None:
        """Cancel editing."""
        self.dismiss({"action": "cancel"})


class SettingsScreen(Screen):
    """Screen for managing application settings."""
    
    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("enter", "apply", "Apply"),
        Binding("up", "cursor_up", "Up"),
        Binding("down", "cursor_down", "Down"),
    ]
    
    THEMES = {
        "classic": {
            "name": "Classic Teal",
            "primary": "#00b4d8",
            "accent": "#00f5ff", 
            "bg": "#034e68",
            "surface": "#023047",
            "text": "#caf0f8"
        },
        "nord": {
            "name": "Nord Theme",
            "primary": "#5e81ac",
            "accent": "#88c0d0",
            "bg": "#2e3440",
            "surface": "#3b4252",
            "text": "#eceff4"
        },
        "gruvbox": {
            "name": "Gruvbox Dark",
            "primary": "#d79921",
            "accent": "#fabd2f",
            "bg": "#282828",
            "surface": "#3c3836",
            "text": "#fbf1c7"
        },
        "dracula": {
            "name": "Dracula",
            "primary": "#bd93f9",
            "accent": "#ff79c6",
            "bg": "#282a36",
            "surface": "#44475a",
            "text": "#f8f8f2"
        },
        "monokai": {
            "name": "Monokai",
            "primary": "#a6e22e",
            "accent": "#f92672",
            "bg": "#272822",
            "surface": "#383830",
            "text": "#f8f8f2"
        }
    }
    
    MAX_COLUMNS = 6
    
    def __init__(self, current_title: str, current_theme: str = "classic", columns: int = 1):
        super().__init__()
        self.current_title = current_title
        self.current_theme = current_theme
        self.selected_index = 0
        self.theme_keys = list(self.THEMES.keys())
        self.column_count = max(1, min(self.MAX_COLUMNS, columns))
        if current_theme in self.theme_keys:
            self.selected_index = self.theme_keys.index(current_theme)
    
    def compose(self) -> ComposeResult:
        """Create settings screen layout."""
        with Container(classes="edit-container"):
            yield Label("Application Settings", classes="edit-title")
            
            yield Label("Choose Theme:")
            
            with Container():
                for i, (theme_key, theme_data) in enumerate(self.THEMES.items()):
                    selected_marker = "▶ " if i == self.selected_index else "  "
                    yield Label(f"{selected_marker}{theme_data['name']}", id=f"theme_{i}")
            
            yield Label(f"Columns (1-{self.MAX_COLUMNS}):", id="columns_label")
            yield Input(value=str(self.column_count), id="columns_input", placeholder="1")
            
            yield Label("")
            yield Label("Application Title:")
            yield Input(value=self.current_title, id="title_input")
            
            with Horizontal(classes="button-row"):
                yield Button("Apply", id="apply", variant="primary")
                yield Button("Cancel", id="cancel", variant="default")
    
    def action_cursor_up(self) -> None:
        """Move selection up."""
        self.selected_index = max(0, self.selected_index - 1)
        self.update_selection()
    
    def action_cursor_down(self) -> None:
        """Move selection down."""
        self.selected_index = min(len(self.theme_keys) - 1, self.selected_index + 1)
        self.update_selection()
    
    def action_apply(self) -> None:
        """Apply settings."""
        selected_theme = self.theme_keys[self.selected_index]
        columns_value = self.get_selected_columns()
        title_input = self.query_one("#title_input", Input)
        title_value = title_input.value.strip() if title_input else self.current_title
        if not title_value:
            title_value = self.current_title
        self.dismiss({
            "action": "apply",
            "theme": selected_theme,
            "columns": columns_value,
            "title": title_value
        })
    
    def action_cancel(self) -> None:
        """Cancel theme selection."""
        self.dismiss({"action": "cancel"})
    
    def update_selection(self) -> None:
        """Update visual selection."""
        for i, theme_key in enumerate(self.theme_keys):
            label = self.query_one(f"#theme_{i}", Label)
            theme_data = self.THEMES[theme_key]
            selected_marker = "▶ " if i == self.selected_index else "  "
            label.update(f"{selected_marker}{theme_data['name']}")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "apply":
            self.action_apply()
        elif event.button.id == "cancel":
            self.action_cancel()
    
    def get_selected_columns(self) -> int:
        """Return the selected column count."""
        try:
            columns_input = self.query_one("#columns_input", Input)
            value = int(columns_input.value.strip())
        except (ValueError, AttributeError):
            value = self.column_count
        return max(1, min(self.MAX_COLUMNS, value))


class MenuMaker(App):
    """Menu Maker - Enhanced categorized menu system."""
    
    CSS = """
    Screen {
        background: #023047;
    }
    
    /* Responsive header - compact for small screens */
    Header {
        background: #00b4d8;
        color: white;
        text-align: center;
        height: 1;
        padding: 0;
        margin: 0;
    }
    
    /* Compact footer for small screens */
    Footer {
        background: #00b4d8;
        color: #caf0f8;
        height: 1;
        padding: 0;
        margin: 0;
    }
    
    .main-container {
        height: 1fr;
        border: none;
        background: #034e68;
        padding: 0;
        margin: 0;
    }
    
    /* Compact status bar */
    .status-bar {
        dock: top;
        height: 1;
        background: #0077b6;
        color: #caf0f8;
        text-align: center;
        padding: 0;
        margin: 0;
    }
    
    /* Optimized menu container with minimal padding */
    .menu-container {
        height: 1fr;
        border: none;
        background: #034e68;
        padding: 0;
        margin: 0;
        overflow-y: auto;
    }
    
    .columns-container {
        width: 100%;
        height: 100%;
        padding: 1 1;
    }
    
    .menu-column {
        width: 1fr;
        min-width: 20;
        padding-right: 1;
    }
    
    /* Compact category headers */
    .category-header {
        height: 1;
        padding: 0 1;
        margin: 0;
        background: #034e68;
        color: #caf0f8;
        text-style: bold;
        border: none;
    }
    
    .category-header.-selected {
        background: #00f5ff;
        color: #023047;
    }
    
    /* Compact menu items */
    .menu-item {
        height: 1;
        padding: 0 2;
        margin: 0;
        background: #034e68;
        color: #caf0f8;
        border: none;
    }
    
    .menu-item.-selected {
        background: #00f5ff;
        color: #023047;
        text-style: bold;
    }
    
    /* Responsive info container */
    .info-container {
        align: center middle;
        width: 90%;
        max-width: 70;
        height: auto;
        background: #034e68;
        border: solid #00f5ff;
        padding: 1;
    }
    
    .info-title {
        text-align: center;
        text-style: bold;
        color: #00f5ff;
        margin-bottom: 0;
    }
    
    .info-field {
        color: #caf0f8;
        margin-bottom: 0;
    }
    
    .info-description {
        color: #caf0f8;
        text-style: italic;
        margin-bottom: 0;
    }
    
    /* Responsive edit container */
    .edit-container {
        align: left top;
        width: 100%;
        height: 100%;
        background: #034e68;
        border: solid #00f5ff;
        padding: 1 2;
    }
    
    .edit-title {
        text-align: center;
        text-style: bold;
        color: #00f5ff;
        margin-bottom: 0;
    }
    
    /* Compact theme editor */
    .theme-editor-container {
        width: 1fr;
        height: 1fr;
        background: #034e68;
        padding: 1;
    }
    
    .theme-editor-title {
        text-align: center;
        text-style: bold;
        color: #00f5ff;
        height: 1;
    }
    
    .theme-option {
        height: 2;
        border: solid #00b4d8;
        margin-bottom: 0;
        padding: 0 1;
    }
    
    /* Compact button row */
    .button-row {
        align: center middle;
        height: auto;
        margin-top: 0;
    }
    
    .color-palette {
        height: 10;
        overflow-y: auto;
        border: solid #00f5ff;
        padding: 0 1;
        margin-bottom: 1;
    }
    
    .color-button {
        height: auto;
        text-align: left;
        margin-bottom: 0;
    }
    
    .error-message {
        color: #ff6b6b;
        height: 1;
    }
    
    Button {
        margin: 0;
        padding: 0 1;
    }
    """
    
    TITLE = "Menu Maker"
    SUB_TITLE = "Enhanced Categorized Menu System"
    
    BINDINGS = [
        Binding("q,escape", "exit_app", "Exit", priority=True),
        Binding("e", "edit_item", "Edit", show=True),
        Binding("enter", "execute_item", "Execute", show=True),
        Binding("n", "new_item", "New Item", show=True),
        Binding("d", "delete_item", "Delete", show=True),
        Binding("s", "open_settings", "Settings", show=True),
        Binding("i", "show_info", "Info", show=True),
        Binding("space", "toggle_category", "Toggle Category", show=True),
        # Enhanced key bindings for Linux compatibility
        Binding("up,k", "cursor_up", "Up", show=False),
        Binding("down,j", "cursor_down", "Down", show=False),
        Binding("tab", "cursor_down", "Next", show=False),
        Binding("shift+tab", "cursor_up", "Previous", show=False),
        # Additional Linux-specific navigation keys
        Binding("ctrl+p", "cursor_up", "Up Alt", show=False),
        Binding("ctrl+n", "cursor_down", "Down Alt", show=False),
        Binding("ctrl+b", "scan_bin_directory", "Scan ./bin", show=True),
    ]
    
    # Reactive state
    current_index = reactive(0)
    menu_data = reactive({})
    
    def __init__(self):
        super().__init__()
        self.menu_widgets = []
        self.display_items = []  # Flattened list for navigation
        self.status_bar = None
        self.menu_container = None
        self.custom_colors: List[Dict[str, str]] = copy.deepcopy(DEFAULT_COLOR_PAIRS)
        self.theme_colors = SettingsScreen.THEMES["classic"].copy()
        self.column_count = 1
        self.max_columns = SettingsScreen.MAX_COLUMNS
        # Create config directory if it doesn't exist
        config_dir = Path.home() / ".local" / "menu-maker"
        config_dir.mkdir(parents=True, exist_ok=True)
        self.config_file = config_dir / "menus.json"
        self.theme_file = config_dir / "theme.json"
        self.app_theme = "classic"
        self.app_title = "Menu Maker — Enhanced Categorized Menu System"
        
        # Linux/Debian compatibility detection
        self.is_linux_system = self.detect_linux_system()
        self.terminal_type = self.detect_terminal_type()
        
        self.load_menu_data()
        self.load_theme_data()
    
    def detect_linux_system(self) -> bool:
        """Detect if running on Linux system."""
        try:
            return os.name == 'posix' and 'linux' in os.uname().sysname.lower()
        except:
            return False
    
    def detect_terminal_type(self) -> str:
        """Detect terminal type for compatibility adjustments."""
        try:
            term = os.environ.get('TERM', '').lower()
            term_program = os.environ.get('TERM_PROGRAM', '').lower()
            
            if 'xterm' in term or 'gnome' in term_program:
                return 'xterm'
            elif 'screen' in term:
                return 'screen'
            elif 'tmux' in term:
                return 'tmux'
            elif 'linux' in term:
                return 'linux_console'
            else:
                return 'unknown'
        except:
            return 'unknown'
    
    def load_menu_data(self) -> None:
        """Load menu data from ~/.local/menu-maker/menus.json file."""
        try:
            # Check for migration from old location
            old_config = Path("menus.json")
            if old_config.exists() and not self.config_file.exists():
                # Migrate old config to new location
                self.config_file.parent.mkdir(parents=True, exist_ok=True)
                old_config.rename(self.config_file)
            
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    self.menu_data = data.get('categories', {})
                    loaded_colors = []
                    for idx, entry in enumerate(data.get('custom_colors', []), start=1):
                        pair = sanitize_color_pair(entry)
                        if pair:
                            loaded_colors.append({
                                "name": entry.get("name") or f"Color {idx}",
                                "background": pair["background"],
                                "text": pair["text"]
                            })
                    if loaded_colors:
                        self.custom_colors = loaded_colors
                    # Load saved settings if available (but theme is now in separate file)
                    if 'app_settings' in data:
                        settings = data['app_settings']
                        if 'title' in settings:
                            self.app_title = settings['title']
                        self.set_column_count(settings.get('columns', 1), apply_layout=False, save_on_change=False)
                        # Remove old theme data if it exists (migration cleanup)
                        if 'theme' in settings:
                            del settings['theme']
                            # Save cleaned data back
                            data['app_settings'] = settings
                            with open(self.config_file, 'w') as f:
                                json.dump(data, f, indent=2)
            else:
                self.create_default_menu()
            if self.ensure_category_columns():
                self.save_menu_data()
        except Exception as e:
            self.create_default_menu()
    
    def load_theme_data(self) -> None:
        """Load theme data from ~/.local/menu-maker/theme.json file in MC format."""
        try:
            if self.theme_file.exists():
                with open(self.theme_file, 'r') as f:
                    theme_data = json.load(f)
                    # MC-style format: {"skin": "theme_name", "colors": {...}}
                    if 'skin' in theme_data:
                        self.app_theme = theme_data['skin']
                        # Don't apply theme yet - wait for on_mount
            else:
                # Create default theme file
                self.app_theme = "classic"
                self.save_theme_data()
        except Exception as e:
            # Fall back to default theme
            self.app_theme = "classic"
            self.save_theme_data()
    
    def save_theme_data(self) -> None:
        """Save theme data to ~/.local/menu-maker/theme.json in MC format."""
        try:
            # Get current theme definition
            theme_def = SettingsScreen.THEMES.get(self.app_theme, SettingsScreen.THEMES["classic"])
            
            # MC-style format with skin name and color definitions
            theme_data = {
                "skin": self.app_theme,
                "description": f"Menu Maker theme: {theme_def['name']}",
                "colors": {
                    "primary": theme_def["primary"],
                    "accent": theme_def["accent"], 
                    "background": theme_def["bg"],
                    "surface": theme_def["surface"],
                    "text": theme_def["text"]
                },
                "metadata": {
                    "created_by": "Menu Maker",
                    "version": "1.0",
                    "compatible_with": "textual"
                }
            }
            
            with open(self.theme_file, 'w') as f:
                json.dump(theme_data, f, indent=2)
        except Exception as e:
            pass  # Fail silently to avoid breaking the app
    
    def create_default_menu(self) -> None:
        """Create default categorized menu structure."""
        self.column_count = 1
        default_data = {
            "System Tools": {
                "expanded": True,
                "column": 1,
                "items": [
                    {"label": "System Monitor", "cmd": "htop", "info": "Interactive process viewer", "category": "System Tools"}
                ]
            }
        }
        self.menu_data = default_data
        self.custom_colors = copy.deepcopy(DEFAULT_COLOR_PAIRS)
        self.save_menu_data()
    
    def save_menu_data(self) -> None:
        """Save menu data to ~/.local/menu-maker/menus.json file."""
        try:
            # Ensure config directory exists
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            
            data = {
                "categories": self.menu_data,
                "app_settings": {
                    "title": self.app_title,
                    "columns": self.column_count
                },
                "custom_colors": self.custom_colors
            }
            with open(self.config_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            pass  # Silently handle save errors
    
    def compose(self) -> ComposeResult:
        """Create the application layout."""
        self.header = Header()
        yield self.header
        
        with Container(classes="main-container"):
            self.status_bar = Static("", classes="status-bar")
            yield self.status_bar
            
            with ScrollableContainer(classes="menu-container") as container:
                self.menu_container = container
                # Menu items will be populated in update_menu_display
                pass
        
        yield Footer()
    
    def on_mount(self) -> None:
        """Initialize after mounting."""
        # Apply loaded theme first
        self.apply_theme(self.app_theme)
        self.update_title()
        self.update_menu_display()
        self.update_status()
        # Ensure proper initial index setting
        object.__setattr__(self, 'current_index', 0)
    
    def update_menu_display(self) -> None:
        """Update menu display with categories and items."""
        if not self.menu_container:
            return
        
        # Clear existing widgets
        self.menu_container.remove_children()
        self.menu_widgets.clear()
        self.display_items.clear()
        
        # Remove empty categories first
        self.cleanup_empty_categories()
        
        columns_wrapper = Horizontal(classes="columns-container")
        self.menu_container.mount(columns_wrapper)
        column_containers: Dict[int, Vertical] = {}
        for column_index in range(1, self.column_count + 1):
            column_container = Vertical(classes="menu-column", id=f"column_{column_index}")
            columns_wrapper.mount(column_container)
            column_containers[column_index] = column_container
        
        columns_changed = False
        columns_content: Dict[int, List[Tuple[str, Dict[str, Any]]]] = {i: [] for i in range(1, self.column_count + 1)}
        for category_name, category_data in self.menu_data.items():
            column_index = self.normalize_column_value(category_data.get('column', 1))
            if category_data.get('column') != column_index:
                category_data['column'] = column_index
                columns_changed = True
            columns_content.setdefault(column_index, []).append((category_name, category_data))
        
        if columns_changed:
            self.save_menu_data()
        
        # Build flattened display list and widgets
        total_items = 0
        for column_index in range(1, self.column_count + 1):
            column_container = column_containers[column_index]
            for category_name, category_data in columns_content.get(column_index, []):
                # Add category header with proper prefix
                is_expanded = category_data.get('expanded', True)
                header_text = f"▼{category_name}" if is_expanded else f"▶{category_name}"
                
                category_header = Static(header_text, classes="category-header")
                category_colors = self.get_category_color_pair(category_name)
                if category_colors:
                    category_header.base_bg = category_colors["background"]
                    category_header.base_text = category_colors["text"]
                else:
                    category_header.base_bg = None
                    category_header.base_text = None
                column_container.mount(category_header)
                self.menu_widgets.append(category_header)
                self.display_items.append({"type": "category", "name": category_name, "widget": category_header})
                total_items += 1
                
                # Add items if expanded
                if is_expanded:
                    items = category_data.get('items', [])
                    for item in items:
                        item_widget = Static(f"    {item['label']}", classes="menu-item")
                        if category_colors:
                            item_widget.base_bg = category_colors["background"]
                            item_widget.base_text = category_colors["text"]
                        column_container.mount(item_widget)
                        self.menu_widgets.append(item_widget)
                        self.display_items.append({"type": "item", "data": item, "widget": item_widget})
                        total_items += 1
        
        # Force container refresh and multiple highlighting updates for cross-platform compatibility
        if self.menu_container:
            self.menu_container.refresh()
        
        # Force immediate highlighting update and ensure container shows all content
        self.update_highlighting()
        
        # Ensure container can scroll and shows all content
        if self.menu_container and total_items > 0:
            # Force container to show all content and reset scroll position
            self.menu_container.scroll_home(animate=False)
            # Ensure the current selection is visible
            if 0 <= self.current_index < len(self.display_items):
                try:
                    widget = self.display_items[self.current_index]["widget"]
                    widget.scroll_visible()
                except (IndexError, KeyError):
                    pass
    
    def cleanup_empty_categories(self) -> None:
        """Remove categories that have no items."""
        updated_data = {}
        for category_name, category_data in self.menu_data.items():
            items = category_data.get('items', [])
            if items:  # Only keep categories that have items
                updated_data[category_name] = category_data
        
        if updated_data != self.menu_data:
            self.menu_data = updated_data
            self.save_menu_data()

    def clamp_column_count(self, value: Any) -> int:
        """Clamp column count to valid range."""
        try:
            count = int(value)
        except (TypeError, ValueError):
            count = 1
        return max(1, min(self.max_columns, count))

    def normalize_column_value(self, value: Any) -> int:
        """Normalize a category column to current limits."""
        try:
            column = int(value)
        except (TypeError, ValueError):
            column = 1
        return max(1, min(self.column_count, column))

    def ensure_category_columns(self) -> bool:
        """Ensure every category has a valid column assignment."""
        changed = False
        for category_data in self.menu_data.values():
            current_column = category_data.get('column', 1)
            normalized = self.normalize_column_value(current_column)
            if current_column != normalized:
                category_data['column'] = normalized
                changed = True
        return changed

    def set_column_count(self, count: Any, apply_layout: bool = True, persist: bool = False, save_on_change: bool = True) -> bool:
        """Set the column count and optionally persist the change."""
        normalized = self.clamp_column_count(count)
        changed = normalized != self.column_count
        self.column_count = normalized
        columns_changed = self.ensure_category_columns()
        if persist or (save_on_change and (changed or columns_changed)):
            self.save_menu_data()
        if apply_layout and self.menu_container:
            self.update_menu_display()
            self.update_status()
        return changed or columns_changed

    def get_category_color_pair(self, category_name: str) -> Optional[Dict[str, str]]:
        """Return sanitized color pair for a category if it exists."""
        category_data = self.menu_data.get(category_name, {})
        return sanitize_color_pair(category_data.get('colors'))

    def apply_widget_colors(self, widget: Optional[Static], selected: bool = False) -> None:
        """Apply either highlight or base colors to a widget."""
        if not widget or not hasattr(widget, "styles"):
            return
        try:
            if selected:
                highlight_bg = self.theme_colors.get("accent", "#00f5ff")
                highlight_text = self.theme_colors.get("bg", "#023047")
                widget.styles.background = highlight_bg
                widget.styles.color = highlight_text
                return
            base_bg = getattr(widget, "base_bg", None)
            base_text = getattr(widget, "base_text", None)
            if base_bg and base_text:
                widget.styles.background = base_bg
                widget.styles.color = base_text
            else:
                widget.styles.background = None
                widget.styles.color = None
        except Exception:
            pass
    
    def update_highlighting(self) -> None:
        """Update visual highlighting with enhanced Linux compatibility."""
        if not self.display_items:
            return

        # Ensure index is always within valid range
        current_idx = max(0, min(self.current_index, len(self.display_items) - 1))
        object.__setattr__(self, 'current_index', current_idx)

        # Clear all selections with explicit widget access and platform-specific timing
        for i, item in enumerate(self.display_items):
            widget = item.get("widget")
            if widget and hasattr(widget, "remove_class"):
                widget.remove_class("-selected")
                self.apply_widget_colors(widget, selected=False)
                # Force immediate refresh for Linux systems
                if hasattr(widget, "refresh"):
                    widget.refresh()
        
        # Apply selection to current item with explicit validation
        if 0 <= current_idx < len(self.display_items):
            current_item = self.display_items[current_idx]
            current_widget = current_item.get("widget")
            
            if current_widget and hasattr(current_widget, "add_class"):
                current_widget.add_class("-selected")
                self.apply_widget_colors(current_widget, selected=True)
                
                # Force immediate visual update for Linux terminals
                if hasattr(current_widget, "refresh"):
                    current_widget.refresh()
                
                # Enhanced scrolling with Linux-specific optimizations
                if self.menu_container:
                    self.ensure_widget_visible(current_widget, current_idx)
    
    def ensure_widget_visible(self, widget, index: int) -> None:
        """Ensure widget is visible with Linux-optimized scrolling."""
        if not widget or not self.menu_container:
            return
            
        try:
            # Primary scrolling method for most terminals
            if hasattr(widget, "scroll_visible"):
                widget.scroll_visible(animate=False)
                return
        except Exception:
            pass
            
        try:
            # Alternative for containers that support widget scrolling
            if hasattr(self.menu_container, "scroll_to_widget"):
                self.menu_container.scroll_to_widget(widget, animate=False)
                return
        except Exception:
            pass
            
        # Linux-specific fallback with manual calculation
        if self.is_linux_system:
            try:
                # Calculate widget position and container viewport
                widget_region = getattr(widget, 'region', None)
                container_region = getattr(self.menu_container, 'region', None)
                
                if widget_region and container_region:
                    # Simple scroll calculation based on widget position
                    widget_top = widget_region.y
                    container_height = container_region.height
                    
                    # Scroll to ensure widget is in viewport
                    if hasattr(self.menu_container, 'scroll_to'):
                        scroll_y = max(0, widget_top - (container_height // 2))
                        self.menu_container.scroll_to(0, scroll_y, animate=False)
            except Exception:
                # Final fallback: force container refresh
                if hasattr(self.menu_container, 'refresh'):
                    self.menu_container.refresh()
    
    def update_title(self) -> None:
        """Update the header title with responsive sizing."""
        if hasattr(self, 'header'):
            # Get terminal size for responsive title
            try:
                import os
                terminal_width = os.get_terminal_size().columns
            except:
                terminal_width = 80
            
            if terminal_width < 60:
                # Ultra compact title for very small terminals
                self.title = "Menu"
                self.sub_title = ""
            elif terminal_width < 80:
                # Compact title for small terminals
                self.title = "Menu Maker"
                self.sub_title = ""
            else:
                # Full title for larger terminals
                self.title = self.app_title
                self.sub_title = ""
    
    def update_status(self) -> None:
        """Update status bar with responsive content."""
        if self.status_bar:
            total = len(self.display_items)
            current = self.current_index + 1 if self.display_items else 0
            
            # Get terminal size for responsive status
            try:
                import os
                terminal_width = os.get_terminal_size().columns
            except:
                terminal_width = 80
            
            if terminal_width < 60:
                # Ultra compact for very small terminals (52x10)
                self.status_bar.update(f"{current}/{total} | ↑↓ E Enter")
            elif terminal_width < 80:
                # Compact for small terminals (71x16)
                theme_short = self.app_theme[:4].title()
                self.status_bar.update(f"{current}/{total} | {theme_short} | ↑↓ E Enter I ^B")
            else:
                # Full status for larger terminals
                theme_name = self.app_theme.title()
                self.status_bar.update(f"Item {current}/{total} | Theme: {theme_name} | ↑↓ Navigate | Enter Execute | E Edit | I Info | ^B Scan")
    
    def watch_current_index(self, new_index: int) -> None:
        """React to index changes."""
        # Disable reactive updates to prevent conflicts
        pass
    
    def watch_menu_data(self, new_data: Dict[str, Any]) -> None:
        """React to menu data changes."""
        self.update_menu_display()
        self.update_status()
    
    async def action_cursor_up(self) -> None:
        """Move cursor up with enhanced Linux compatibility."""
        if not self.display_items or len(self.display_items) == 0:
            return
        
        # Calculate new index with wrap-around for better UX
        new_index = (self.current_index - 1) % len(self.display_items)
        
        if new_index != self.current_index:
            # Direct assignment without triggering reactive updates
            object.__setattr__(self, 'current_index', new_index)
            
            # Linux-optimized update strategy
            if self.is_linux_system:
                # Immediate synchronous updates for Linux terminals
                self.update_highlighting()
                self.update_status()
            else:
                # Asynchronous updates for other systems
                self.call_after_refresh(self.update_highlighting)
                self.call_after_refresh(self.update_status)
    
    async def action_cursor_down(self) -> None:
        """Move cursor down with enhanced Linux compatibility."""
        if not self.display_items or len(self.display_items) == 0:
            return
        
        # Calculate new index with wrap-around for better UX
        new_index = (self.current_index + 1) % len(self.display_items)
        
        if new_index != self.current_index:
            # Direct assignment without triggering reactive updates
            object.__setattr__(self, 'current_index', new_index)
            
            # Linux-optimized update strategy
            if self.is_linux_system:
                # Immediate synchronous updates for Linux terminals
                self.update_highlighting()
                self.update_status()
            else:
                # Asynchronous updates for other systems
                self.call_after_refresh(self.update_highlighting)
                self.call_after_refresh(self.update_status)
    
    async def action_execute_item(self) -> None:
        """Execute item or toggle category based on selection."""
        if not self.display_items or self.current_index >= len(self.display_items):
            return
        
        current_item = self.display_items[self.current_index]
        
        if current_item["type"] == "item":
            # Execute the application
            command = current_item["data"].get("cmd", "")
            if command:
                pause_setting = current_item["data"].get("pause", False)
                await self.run_external_command(command, pause_setting)
            else:
                pass  # Silently handle missing command
        elif current_item["type"] == "category":
            # Toggle category expansion/collapse
            await self.action_toggle_category()
    
    async def run_external_command(self, command: str, pause: bool = False) -> None:
        """Run external command and return to menu."""
        try:
            with self.suspend():
                os.system('clear')
                print(f"MenuWorks: Executing '{command}'")
                print("=" * 60)
                print()
                
                result = subprocess.run(command, shell=True)
                
                if pause:
                    # Show completion message and wait for keypress
                    print()
                    print("=" * 60)
                    print(f"Command completed with exit code: {result.returncode}")
                    print("Press Enter to return to MenuMaker...")
                    input()
                    os.system('clear')
                else:
                    # Clear screen immediately after app exits
                    os.system('clear')
            
        except Exception as e:
            pass  # Silently handle execution errors
    
    async def action_toggle_category(self) -> None:
        """Toggle category expansion and save state."""
        if not self.display_items or self.current_index >= len(self.display_items):
            return
        
        current_item = self.display_items[self.current_index]
        
        if current_item["type"] == "category":
            category_name = current_item["name"]
            if category_name in self.menu_data:
                # Remember the category we're toggling to restore position
                selected_category = category_name
                
                # Toggle expanded state
                current_state = self.menu_data[category_name].get('expanded', True)
                updated_data = dict(self.menu_data)
                updated_data[category_name]['expanded'] = not current_state
                self.menu_data = updated_data
                
                # Save state to persist across restarts
                self.save_menu_data()
                
                # Update display to reflect changes
                self.update_menu_display()
                
                # Restore position to the same category after display update
                self.restore_position_to_category(selected_category)
    
    def restore_position_to_category(self, category_name: str) -> None:
        """Restore cursor position to the specified category after display update."""
        for i, item in enumerate(self.display_items):
            if item["type"] == "category" and item["name"] == category_name:
                self.current_index = i
                break
    
    def navigate_to_item(self, target_item: Dict[str, str]) -> None:
        """Navigate to a specific item in the menu display."""
        target_label = target_item.get('label', '')
        target_cmd = target_item.get('cmd', '')
        
        for i, item in enumerate(self.display_items):
            if (item["type"] == "item" and 
                item["data"].get('label', '') == target_label and
                item["data"].get('cmd', '') == target_cmd):
                self.current_index = i
                self.update_highlighting()
                self.update_status()
                break
    
    def action_show_info(self) -> None:
        """Show info for current item."""
        if not self.display_items or self.current_index >= len(self.display_items):
            return
        
        current_item = self.display_items[self.current_index]
        
        if current_item["type"] == "item":
            self.push_screen(InfoScreen(current_item["data"]))
        else:
            pass  # Silently handle category info requests
    
    def action_edit_item(self) -> None:
        """Edit the currently selected item or category."""
        if not self.display_items or self.current_index >= len(self.display_items):
            return
        
        current_item = self.display_items[self.current_index]
        
        if current_item["type"] == "item":
            categories = list(self.menu_data.keys())
            item_data = current_item["data"]
            
            def handle_edit_result(result):
                if result and result.get("action") == "save":
                    self.update_item(item_data, result["data"])
            
            self.push_screen(EditItemScreen(item_data, categories, self.current_index), callback=handle_edit_result)
        
        elif current_item["type"] == "category":
            category_name = current_item["name"]
            category_data = self.menu_data.get(category_name, {})
            category_colors = category_data.get('colors')
            existing_categories = list(self.menu_data.keys())
            current_column = category_data.get('column', 1)
            
            def handle_category_edit_result(result):
                if result and result.get("action") == "save":
                    self.custom_colors = result.get("custom_colors", self.custom_colors)
                    self.update_category_details(
                        result["old_name"],
                        result["new_name"],
                        result.get("colors"),
                        result.get("column")
                    )
            
            self.push_screen(
                EditCategoryScreen(
                    category_name,
                    category_colors,
                    self.custom_colors,
                    existing_categories,
                    self.column_count,
                    current_column
                ),
                callback=handle_category_edit_result
            )
    
    def action_new_item(self) -> None:
        """Create a new menu item."""
        categories = list(self.menu_data.keys())
        if not categories:
            categories = ["General"]
        
        new_item = {"label": "", "cmd": "", "info": "", "category": categories[0]}
        
        def handle_new_result(result):
            if result and result.get("action") == "save":
                self.add_new_item(result["data"])
        
        self.push_screen(EditItemScreen(new_item, categories, -1), callback=handle_new_result)
    
    def add_new_item(self, item_data: Dict[str, str]) -> None:
        """Add a new item to the menu."""
        category = item_data.get('category', 'General')
        
        # Ensure category exists
        updated_data = dict(self.menu_data)
        if category not in updated_data:
            updated_data[category] = {
                "expanded": True,
                "column": self.normalize_column_value(1),
                "items": []
            }
        
        # Add item to category
        updated_data[category]['items'].append(item_data)
        self.menu_data = updated_data
        self.save_menu_data()
        self.update_menu_display()
    
    def update_item(self, old_item: Dict[str, str], new_item: Dict[str, str]) -> None:
        """Update an existing item and handle category changes."""
        updated_data = dict(self.menu_data)
        
        old_label = old_item.get('label', '')
        old_cmd = old_item.get('cmd', '')
        old_category = old_item.get('category', '')
        new_category = new_item.get('category', '')
        
        # Find and remove the item from its current category
        item_found = False
        for category_name, category_data in updated_data.items():
            items = category_data.get('items', [])
            for i, item in enumerate(items):
                # Match by label and command to find the right item
                if (item.get('label', '') == old_label and 
                    item.get('cmd', '') == old_cmd):
                    # Remove from current category
                    items.pop(i)
                    item_found = True
                    break
            if item_found:
                break
        
        if not item_found:
            return
        
        # Create new category if it doesn't exist
        if new_category not in updated_data:
            updated_data[new_category] = {
                "expanded": True,
                "column": self.normalize_column_value(1),
                "items": []
            }
        
        # Add item to new category
        updated_data[new_category]['items'].append(new_item)
        
        # Clean up empty categories
        categories_to_remove = []
        for category_name, category_data in updated_data.items():
            if not category_data.get('items', []):
                categories_to_remove.append(category_name)
        
        for category_name in categories_to_remove:
            del updated_data[category_name]
        
        self.menu_data = updated_data
        self.save_menu_data()
        self.update_menu_display()
        
        # Navigate to the item in its new category
        self.navigate_to_item(new_item)
    
    def update_category_details(self, old_name: str, new_name: str, colors: Optional[Dict[str, str]], column: Optional[int]) -> None:
        """Update category name, colors, and column assignments."""
        if old_name not in self.menu_data:
            return
        
        sanitized_colors = sanitize_color_pair(colors)
        updated_data = dict(self.menu_data)
        category_data = updated_data[old_name].copy()
        column_value = self.normalize_column_value(column if column is not None else category_data.get('column', 1))
        category_data['column'] = column_value
        
        if sanitized_colors:
            category_data['colors'] = sanitized_colors
        elif 'colors' in category_data:
            del category_data['colors']
        
        target_name = new_name or old_name
        if target_name != old_name and target_name in updated_data:
            # Shouldn't happen due to validation, but guard against overwriting
            target_name = old_name
        
        if target_name != old_name:
            for item in category_data.get('items', []):
                item['category'] = target_name
            updated_data[target_name] = category_data
            del updated_data[old_name]
        else:
            updated_data[old_name] = category_data
        
        self.menu_data = updated_data
        self.save_menu_data()
        self.update_menu_display()
        self.restore_position_to_category(target_name)
        self.update_highlighting()
        self.update_status()
    
    async def action_delete_item(self) -> None:
        """Delete the currently selected item."""
        if not self.display_items or self.current_index >= len(self.display_items):
            return
        
        current_item = self.display_items[self.current_index]
        
        if current_item["type"] == "item":
            item_data = current_item["data"]
            category = item_data.get('category')
            
            # Remove item from category
            updated_data = dict(self.menu_data)
            if category in updated_data:
                items = updated_data[category].get('items', [])
                if item_data in items:
                    items.remove(item_data)
                    
                    # Remove empty category
                    if not items:
                        del updated_data[category]
                    
                    self.menu_data = updated_data
                    self.save_menu_data()
                    self.update_menu_display()
                    
                    # Adjust current index
                    if self.current_index >= len(self.display_items) - 1:
                        self.current_index = max(0, len(self.display_items) - 2)

    def action_open_settings(self) -> None:
        """Open the settings screen for title, theme, and layout."""
        def handle_settings_result(result: Optional[Dict[str, Any]]) -> None:
            if not result or result.get("action") != "apply":
                return
            
            new_title = result.get("title", self.app_title).strip() or self.app_title
            new_theme = result.get("theme", self.app_theme)
            new_columns = result.get("columns", self.column_count)
            
            title_changed = new_title != self.app_title
            theme_changed = new_theme != self.app_theme
            columns_changed = self.set_column_count(
                new_columns,
                apply_layout=not theme_changed,
                save_on_change=False
            )
            
            if title_changed:
                self.app_title = new_title
                self.update_title()
            else:
                self.app_title = new_title
            
            if theme_changed:
                self.app_theme = new_theme
                self.apply_theme(new_theme)
            else:
                if columns_changed:
                    self.update_menu_display()
                    self.update_status()
            
            self.save_menu_data()
        
        self.push_screen(
            SettingsScreen(self.app_title, self.app_theme, self.column_count),
            callback=handle_settings_result
        )
    
    def apply_theme(self, theme_name: str) -> None:
        """Apply theme colors to the entire application."""
        theme_data = SettingsScreen.THEMES.get(theme_name, SettingsScreen.THEMES["classic"])
        self.theme_colors = theme_data.copy()
        
        # Create dynamic CSS with theme colors AND responsive sizing
        dynamic_css = f"""
        Screen {{
            background: {theme_data['bg']};
        }}
        
        /* Responsive header - compact for small screens */
        Header {{
            background: {theme_data['primary']};
            color: white;
            text-align: center;
            height: 1;
            padding: 0;
            margin: 0;
        }}
        
        /* Compact footer for small screens */
        Footer {{
            background: {theme_data['primary']};
            color: {theme_data['text']};
            height: 1;
            padding: 0;
            margin: 0;
        }}
        
        .main-container {{
            height: 1fr;
            border: none;
            background: {theme_data['surface']};
            padding: 0;
            margin: 0;
        }}
        
        /* Compact status bar */
        .status-bar {{
            dock: top;
            height: 1;
            background: {theme_data['primary']};
            color: {theme_data['text']};
            text-align: center;
            padding: 0;
            margin: 0;
        }}
        
        /* Optimized menu container with minimal padding */
        .menu-container {{
            height: 1fr;
            border: none;
            background: {theme_data['surface']};
            padding: 0;
            margin: 0;
            overflow-y: auto;
        }}
        
        .columns-container {{
            width: 100%;
            height: 100%;
            padding: 1 1;
        }}
        
        .menu-column {{
            width: 1fr;
            min-width: 20;
            padding-right: 1;
        }}
        
        /* Compact category headers */
        .category-header {{
            height: 1;
            padding: 0 1;
            margin: 0;
            background: {theme_data['surface']};
            color: {theme_data['text']};
            text-style: bold;
            border: none;
        }}
        
        .category-header.-selected {{
            background: {theme_data['accent']};
            color: {theme_data['bg']};
        }}
        
        /* Compact menu items */
        .menu-item {{
            height: 1;
            padding: 0 2;
            margin: 0;
            background: {theme_data['surface']};
            color: {theme_data['text']};
            border: none;
        }}
        
        .menu-item.-selected {{
            background: {theme_data['accent']};
            color: {theme_data['bg']};
            text-style: bold;
        }}
        
        /* Responsive info container */
        .info-container {{
            align: center middle;
            width: 90%;
            max-width: 70;
            height: auto;
            background: {theme_data['surface']};
            border: solid {theme_data['accent']};
            padding: 1;
        }}
        
        .info-title {{
            text-align: center;
            text-style: bold;
            color: {theme_data['accent']};
            margin-bottom: 0;
        }}
        
        .info-field {{
            color: {theme_data['text']};
            margin-bottom: 0;
        }}
        
        .info-description {{
            color: {theme_data['text']};
            text-style: italic;
            margin-bottom: 0;
        }}
        
        /* Responsive edit container */
        .edit-container {{
            align: left top;
            width: 100%;
            height: 100%;
            background: {theme_data['surface']};
            border: solid {theme_data['accent']};
            padding: 1 2;
        }}
        
        .edit-title {{
            text-align: center;
            text-style: bold;
            color: {theme_data['accent']};
            margin-bottom: 0;
        }}
        
        /* Compact theme editor */
        .theme-editor-container {{
            width: 1fr;
            height: 1fr;
            background: {theme_data['surface']};
            padding: 1;
        }}
        
        .theme-editor-title {{
            text-align: center;
            text-style: bold;
            color: {theme_data['accent']};
            height: 1;
        }}
        
        .theme-option {{
            height: 2;
            border: solid {theme_data['primary']};
            margin-bottom: 0;
            padding: 0 1;
        }}
        
        /* Compact button row */
        .button-row {{
            align: center middle;
            height: auto;
            margin-top: 0;
        }}
        
        .color-palette {{
            height: 10;
            overflow-y: auto;
            border: solid {theme_data['accent']};
            padding: 0 1;
            margin-bottom: 1;
        }}
        
        .color-button {{
            height: auto;
            text-align: left;
            margin-bottom: 0;
        }}
        
        .error-message {{
            color: #ff6b6b;
            height: 1;
        }}
        
        Button {{
            margin: 0;
            padding: 0 1;
        }}
        """
        
        # Add unique identifier to CSS to force refresh
        import time
        css_id = f"theme_{theme_name}_{int(time.time())}"
        dynamic_css = f"/* {css_id} */\n" + dynamic_css
        
        # Apply the dynamic CSS with force refresh
        self.stylesheet.add_source(dynamic_css)
        
        # Set theme and save immediately
        self.app_theme = theme_name
        self.save_theme_data()
        
        # Force complete visual refresh
        self.refresh(layout=True)
        self.update_menu_display()
        self.update_highlighting()
        self.update_status()
        self.update_title()
        
        # Final refresh to ensure all changes are visible
        self.refresh()
    
    def action_scan_bin_directory(self) -> None:
        """Scan ./bin directory and add executables as menu items."""
        self.scan_and_add_bin_executables()
    
    def scan_and_add_bin_executables(self) -> None:
        """Scan ./bin directory for executables, move them to ~/.local/menu-maker/bin, and add them to menu."""
        source_bin_path = Path("./bin")
        
        if not source_bin_path.exists() or not source_bin_path.is_dir():
            return  # Silent handling - no bin directory found
        
        # Create destination bin directory in config location
        dest_bin_path = self.config_file.parent / "bin"
        dest_bin_path.mkdir(parents=True, exist_ok=True)
        
        # Get existing commands to avoid duplicates
        existing_commands = set()
        existing_files = set()
        for category_data in self.menu_data.values():
            for item in category_data.get('items', []):
                cmd = item.get('cmd', '').strip()
                if cmd:
                    existing_commands.add(cmd)
                    # Extract filename from command path
                    if cmd.startswith('~/.local/menu-maker/bin/'):
                        existing_files.add(Path(cmd).name)
        
        # Scan for executable files
        new_executables = []
        try:
            for file_path in source_bin_path.iterdir():
                if file_path.is_file() and os.access(file_path, os.X_OK):
                    filename = file_path.name
                    
                    # Skip if file already exists in destination
                    if filename in existing_files:
                        continue
                    
                    # Create destination path
                    dest_file_path = dest_bin_path / filename
                    new_cmd = f"~/.local/menu-maker/bin/{filename}"
                    
                    # Skip if command already exists
                    if new_cmd in existing_commands:
                        continue
                    
                    # Move file to destination directory
                    try:
                        import shutil
                        shutil.move(str(file_path), str(dest_file_path))
                        # Ensure executable permissions are preserved
                        dest_file_path.chmod(0o755)
                    except Exception:
                        continue  # Skip files that can't be moved
                    
                    # Create menu item with new path
                    executable_name = filename.replace('_', ' ').replace('-', ' ').title()
                    new_item = {
                        "label": executable_name,
                        "cmd": new_cmd,
                        "info": f"Executable: {filename}",
                        "category": "Bin Executables"
                    }
                    new_executables.append(new_item)
        
        except Exception:
            return  # Silent handling of scan errors
        
        # Add new executables to menu
        if new_executables:
            # Ensure "Bin Executables" category exists
            if "Bin Executables" not in self.menu_data:
                updated_data = dict(self.menu_data)
                updated_data["Bin Executables"] = {
                    "expanded": True,
                    "items": []
                }
                self.menu_data = updated_data
            
            # Add new items to the category
            for new_item in new_executables:
                self.add_new_item(new_item)
    
    async def action_exit_app(self) -> None:
        """Exit the application."""
        # Save current theme before exiting
        self.save_theme_data()
        self.exit()


def main():
    """Main entry point."""
    app = MenuMaker()
    app.run()


if __name__ == "__main__":
    main()

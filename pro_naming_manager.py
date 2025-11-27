"""
Pro Naming Manager for Maya
A comprehensive renaming tool with advanced features for production environments.

Features:
- Add/Remove Prefix & Suffix
- Find & Replace (with regex support)
- Sequential Numbering with padding
- Case conversion (upper, lower, title, camelCase)
- Trim whitespace and special characters
- Remove duplicate prefixes/suffixes
- Preview changes before applying
- Undo support
- Save/Load naming presets
"""

import maya.cmds as cmds
import re
import json

class ProNamingManager:
    def __init__(self):
        self.window_name = "ProNamingManagerUI"
        self.window_title = "Pro Naming Manager"
        self.preview_list = []
        
    def create_ui(self):
        if cmds.window(self.window_name, exists=True):
            cmds.deleteUI(self.window_name, window=True)
        
        self.window = cmds.window(
            self.window_name,
            title=self.window_title,
            widthHeight=(650, 700),
            sizeable=True
        )
        
        main_layout = cmds.scrollLayout(childResizable=True)
        cmds.columnLayout(adjustableColumn=True, rowSpacing=5, parent=main_layout)
        
        # Header
        cmds.separator(height=10, style="none")
        cmds.text(label="PRO NAMING MANAGER", font="boldLabelFont", height=30)
        cmds.separator(height=10, style="in")
        
        # Selection Info
        cmds.frameLayout(label="Selection", collapsable=True, collapse=False)
        cmds.columnLayout(adjustableColumn=True)
        self.selection_text = cmds.scrollField(wordWrap=True, height=80, editable=False, backgroundColor=(0.2, 0.2, 0.2))
        cmds.rowLayout(numberOfColumns=2, columnWidth2=(320, 320))
        cmds.button(label="Refresh Selection", command=self.refresh_selection)
        cmds.button(label="Clear Preview", command=self.clear_preview)
        cmds.setParent('..')
        cmds.setParent('..')
        cmds.setParent('..')
        
        # Preview
        cmds.frameLayout(label="Preview (Before → After)", collapsable=True, collapse=False)
        cmds.columnLayout(adjustableColumn=True)
        self.preview_field = cmds.scrollField(wordWrap=False, height=100, editable=False, backgroundColor=(0.15, 0.15, 0.2))
        cmds.rowLayout(numberOfColumns=2, columnWidth2=(320, 320))
        cmds.button(label="Apply Changes", command=self.apply_changes, backgroundColor=[0.3, 0.7, 0.3])
        cmds.button(label="Preview Changes", command=self.preview_changes, backgroundColor=[0.5, 0.5, 0.7])
        cmds.setParent('..')
        cmds.setParent('..')
        cmds.setParent('..')
        
        # Tabs for different operations
        tabs = cmds.tabLayout(innerMarginWidth=5, innerMarginHeight=5)
        
        # TAB 1: Basic Operations
        self.create_basic_tab(tabs)
        
        # TAB 2: Find & Replace
        self.create_find_replace_tab(tabs)
        
        # TAB 3: Numbering
        self.create_numbering_tab(tabs)
        
        # TAB 4: Case & Cleanup
        self.create_case_cleanup_tab(tabs)
        
        # TAB 5: Presets
        self.create_presets_tab(tabs)
        
        cmds.tabLayout(tabs, edit=True, 
                      tabLabel=(
                          (self.basic_tab, "Basic"),
                          (self.find_replace_tab, "Find/Replace"),
                          (self.numbering_tab, "Numbering"),
                          (self.case_cleanup_tab, "Case/Cleanup"),
                          (self.presets_tab, "Presets")
                      ))
        
        cmds.setParent('..')
        
        # Bottom buttons
        cmds.separator(height=10, style="in")
        cmds.button(label="Close", command=self.close_window, height=30)
        cmds.separator(height=10, style="none")
        
        cmds.showWindow(self.window)
        self.refresh_selection()
    
    def create_basic_tab(self, parent):
        self.basic_tab = cmds.columnLayout(adjustableColumn=True, parent=parent, rowSpacing=10)
        
        # Prefix
        cmds.frameLayout(label="Prefix Operations", collapsable=True, collapse=False)
        cmds.columnLayout(adjustableColumn=True)
        cmds.rowLayout(numberOfColumns=3, columnWidth3=(100, 440, 80))
        cmds.text(label="Add Prefix:", align="right")
        self.add_prefix_field = cmds.textField(placeholderText="e.g., CTRL_")
        cmds.button(label="Add", command=lambda *args: self.add_prefix())
        cmds.setParent('..')
        cmds.rowLayout(numberOfColumns=3, columnWidth3=(100, 440, 80))
        cmds.text(label="Remove Prefix:", align="right")
        self.remove_prefix_field = cmds.textField(placeholderText="e.g., CTRL_")
        cmds.button(label="Remove", command=lambda *args: self.remove_prefix())
        cmds.setParent('..')
        cmds.button(label="Remove All Prefixes (before first _)", command=lambda *args: self.remove_all_prefixes())
        cmds.setParent('..')
        cmds.setParent('..')
        
        # Suffix
        cmds.frameLayout(label="Suffix Operations", collapsable=True, collapse=False)
        cmds.columnLayout(adjustableColumn=True)
        cmds.rowLayout(numberOfColumns=3, columnWidth3=(100, 440, 80))
        cmds.text(label="Add Suffix:", align="right")
        self.add_suffix_field = cmds.textField(placeholderText="e.g., _GRP")
        cmds.button(label="Add", command=lambda *args: self.add_suffix())
        cmds.setParent('..')
        cmds.rowLayout(numberOfColumns=3, columnWidth3=(100, 440, 80))
        cmds.text(label="Remove Suffix:", align="right")
        self.remove_suffix_field = cmds.textField(placeholderText="e.g., _GRP")
        cmds.button(label="Remove", command=lambda *args: self.remove_suffix())
        cmds.setParent('..')
        cmds.button(label="Remove All Suffixes (after last _)", command=lambda *args: self.remove_all_suffixes())
        cmds.setParent('..')
        cmds.setParent('..')
        
        cmds.setParent('..')
    
    def create_find_replace_tab(self, parent):
        self.find_replace_tab = cmds.columnLayout(adjustableColumn=True, parent=parent, rowSpacing=10)
        
        cmds.frameLayout(label="Find & Replace", collapsable=False)
        cmds.columnLayout(adjustableColumn=True)
        cmds.rowLayout(numberOfColumns=2, columnWidth2=(100, 520))
        cmds.text(label="Find:", align="right")
        self.find_field = cmds.textField(placeholderText="Text to find")
        cmds.setParent('..')
        cmds.rowLayout(numberOfColumns=2, columnWidth2=(100, 520))
        cmds.text(label="Replace with:", align="right")
        self.replace_field = cmds.textField(placeholderText="Replacement text")
        cmds.setParent('..')
        self.regex_checkbox = cmds.checkBox(label="Use Regular Expressions (Regex)", value=False)
        self.case_sensitive_checkbox = cmds.checkBox(label="Case Sensitive", value=True)
        cmds.button(label="Find & Replace", command=lambda *args: self.find_replace(), height=35, backgroundColor=[0.4, 0.5, 0.6])
        cmds.setParent('..')
        cmds.setParent('..')
        
        # Common Replacements
        cmds.frameLayout(label="Quick Replacements", collapsable=True, collapse=True)
        cmds.columnLayout(adjustableColumn=True)
        cmds.button(label="Remove Underscores ( _ )", command=lambda *args: self.quick_replace("_", ""))
        cmds.button(label="Underscores to Spaces", command=lambda *args: self.quick_replace("_", " "))
        cmds.button(label="Spaces to Underscores", command=lambda *args: self.quick_replace(" ", "_"))
        cmds.button(label="Remove Numbers", command=lambda *args: self.remove_numbers())
        cmds.button(label="Remove Special Characters", command=lambda *args: self.remove_special_chars())
        cmds.setParent('..')
        cmds.setParent('..')
        
        cmds.setParent('..')
    
    def create_numbering_tab(self, parent):
        self.numbering_tab = cmds.columnLayout(adjustableColumn=True, parent=parent, rowSpacing=10)
        
        cmds.frameLayout(label="Sequential Numbering", collapsable=False)
        cmds.columnLayout(adjustableColumn=True)
        cmds.rowLayout(numberOfColumns=2, columnWidth2=(150, 470))
        cmds.text(label="Base Name:", align="right")
        self.base_name_field = cmds.textField(text="object", placeholderText="e.g., joint")
        cmds.setParent('..')
        cmds.rowLayout(numberOfColumns=2, columnWidth2=(150, 470))
        cmds.text(label="Start Number:", align="right")
        self.start_number_field = cmds.intField(value=1, minValue=0)
        cmds.setParent('..')
        cmds.rowLayout(numberOfColumns=2, columnWidth2=(150, 470))
        cmds.text(label="Padding (digits):", align="right")
        self.padding_field = cmds.intField(value=2, minValue=0, maxValue=6)
        cmds.setParent('..')
        cmds.rowLayout(numberOfColumns=2, columnWidth2=(150, 470))
        cmds.text(label="Separator:", align="right")
        self.separator_field = cmds.textField(text="_")
        cmds.setParent('..')
        cmds.separator(height=10)
        cmds.text(label="Preview: object_01, object_02, object_03...", font="smallPlainLabelFont", align="center")
        cmds.button(label="Apply Sequential Numbering", command=lambda *args: self.apply_numbering(), height=35, backgroundColor=[0.4, 0.6, 0.5])
        cmds.setParent('..')
        cmds.setParent('..')
        
        # Renumber
        cmds.frameLayout(label="Renumber Existing", collapsable=True, collapse=True)
        cmds.columnLayout(adjustableColumn=True)
        cmds.text(label="Keep existing name, just renumber the suffix")
        cmds.rowLayout(numberOfColumns=2, columnWidth2=(150, 470))
        cmds.text(label="Start from:", align="right")
        self.renumber_start_field = cmds.intField(value=1, minValue=0)
        cmds.setParent('..')
        cmds.rowLayout(numberOfColumns=2, columnWidth2=(150, 470))
        cmds.text(label="Padding:", align="right")
        self.renumber_padding_field = cmds.intField(value=2, minValue=0, maxValue=6)
        cmds.setParent('..')
        cmds.button(label="Renumber Selection", command=lambda *args: self.renumber_selection(), backgroundColor=[0.5, 0.5, 0.6])
        cmds.setParent('..')
        cmds.setParent('..')
        
        cmds.setParent('..')
    
    def create_case_cleanup_tab(self, parent):
        self.case_cleanup_tab = cmds.columnLayout(adjustableColumn=True, parent=parent, rowSpacing=10)
        
        # Case Conversion
        cmds.frameLayout(label="Case Conversion", collapsable=False)
        cmds.columnLayout(adjustableColumn=True)
        cmds.button(label="UPPERCASE", command=lambda *args: self.convert_case("upper"))
        cmds.button(label="lowercase", command=lambda *args: self.convert_case("lower"))
        cmds.button(label="Title Case", command=lambda *args: self.convert_case("title"))
        cmds.button(label="camelCase", command=lambda *args: self.convert_case("camel"))
        cmds.button(label="PascalCase", command=lambda *args: self.convert_case("pascal"))
        cmds.setParent('..')
        cmds.setParent('..')
        
        # Cleanup
        cmds.frameLayout(label="Cleanup Operations", collapsable=False)
        cmds.columnLayout(adjustableColumn=True)
        cmds.button(label="Remove Duplicate Prefixes", command=lambda *args: self.clean_duplicate_prefixes())
        cmds.button(label="Remove Duplicate Suffixes", command=lambda *args: self.clean_duplicate_suffixes())
        cmds.button(label="Trim Whitespace", command=lambda *args: self.trim_whitespace())
        cmds.button(label="Remove Multiple Underscores (__ → _)", command=lambda *args: self.clean_multiple_underscores())
        cmds.button(label="Remove Namespace", command=lambda *args: self.remove_namespace())
        cmds.setParent('..')
        cmds.setParent('..')
        
        cmds.setParent('..')
    
    def create_presets_tab(self, parent):
        self.presets_tab = cmds.columnLayout(adjustableColumn=True, parent=parent, rowSpacing=10)
        
        cmds.frameLayout(label="Naming Presets", collapsable=False)
        cmds.columnLayout(adjustableColumn=True)
        cmds.text(label="Save and load naming operations as presets")
        cmds.separator(height=10)
        cmds.rowLayout(numberOfColumns=2, columnWidth2=(320, 320))
        cmds.button(label="Save Preset", command=lambda *args: self.save_preset())
        cmds.button(label="Load Preset", command=lambda *args: self.load_preset())
        cmds.setParent('..')
        cmds.setParent('..')
        cmds.setParent('..')
        
        # Common Presets
        cmds.frameLayout(label="Common Naming Conventions", collapsable=True, collapse=False)
        cmds.columnLayout(adjustableColumn=True)
        cmds.button(label="Control: Add '_CTRL' suffix", command=lambda *args: self.apply_preset_ctrl())
        cmds.button(label="Group: Add '_GRP' suffix", command=lambda *args: self.apply_preset_grp())
        cmds.button(label="Joint: Add '_JNT' suffix", command=lambda *args: self.apply_preset_jnt())
        cmds.button(label="Geo: Add '_GEO' suffix", command=lambda *args: self.apply_preset_geo())
        cmds.button(label="Locator: Add '_LOC' suffix", command=lambda *args: self.apply_preset_loc())
        cmds.setParent('..')
        cmds.setParent('..')
        
        cmds.setParent('..')
    
    # Core Functions
    def refresh_selection(self, *args):
        selection = cmds.ls(selection=True, long=True)
        if selection:
            info = f"Selected: {len(selection)} objects\n\n"
            info += "\n".join([obj.split('|')[-1] for obj in selection[:15]])
            if len(selection) > 15:
                info += f"\n... and {len(selection) - 15} more"
        else:
            info = "No objects selected"
        cmds.scrollField(self.selection_text, edit=True, text=info)
    
    def clear_preview(self, *args):
        self.preview_list = []
        cmds.scrollField(self.preview_field, edit=True, text="Preview will appear here...")
    
    def get_new_names(self, operation_func):
        """Generic function to generate new names based on an operation"""
        selection = cmds.ls(selection=True, long=True)
        if not selection:
            cmds.warning("Nothing selected")
            return []
        
        new_names = []
        for obj in selection:
            short_name = obj.split('|')[-1]
            new_name = operation_func(short_name)
            if new_name and new_name != short_name:
                new_names.append((obj, short_name, new_name))
        
        return new_names
    
    def preview_changes(self, *args):
        if not self.preview_list:
            cmds.warning("No changes to preview. Perform an operation first.")
            return
        
        preview_text = f"{len(self.preview_list)} objects will be renamed:\n\n"
        for obj, old, new in self.preview_list[:20]:
            preview_text += f"{old}  →  {new}\n"
        if len(self.preview_list) > 20:
            preview_text += f"\n... and {len(self.preview_list) - 20} more"
        
        cmds.scrollField(self.preview_field, edit=True, text=preview_text)
    
    def apply_changes(self, *args):
        if not self.preview_list:
            cmds.warning("No changes to apply")
            return
        
        renamed_count = 0
        # Rename from bottom of hierarchy up (reverse order) to avoid path invalidation
        for obj, old_name, new_name in reversed(self.preview_list):
            if cmds.objExists(obj):
                try:
                    cmds.rename(obj, new_name)
                    renamed_count += 1
                except Exception as e:
                    cmds.warning(f"Could not rename {old_name}: {e}")
        
        print(f"Renamed {renamed_count} objects")
        self.preview_list = []
        self.clear_preview()
        self.refresh_selection()
    
    # Basic Operations
    def add_prefix(self):
        prefix = cmds.textField(self.add_prefix_field, query=True, text=True)
        if not prefix:
            cmds.warning("Enter a prefix")
            return
        self.preview_list = self.get_new_names(lambda name: prefix + name if not name.startswith(prefix) else name)
        self.preview_changes()
    
    def remove_prefix(self):
        prefix = cmds.textField(self.remove_prefix_field, query=True, text=True)
        if not prefix:
            cmds.warning("Enter a prefix to remove")
            return
        self.preview_list = self.get_new_names(lambda name: name[len(prefix):] if name.startswith(prefix) else name)
        self.preview_changes()
    
    def remove_all_prefixes(self):
        self.preview_list = self.get_new_names(lambda name: name.split('_', 1)[1] if '_' in name else name)
        self.preview_changes()
    
    def add_suffix(self):
        suffix = cmds.textField(self.add_suffix_field, query=True, text=True)
        if not suffix:
            cmds.warning("Enter a suffix")
            return
        self.preview_list = self.get_new_names(lambda name: name + suffix if not name.endswith(suffix) else name)
        self.preview_changes()
    
    def remove_suffix(self):
        suffix = cmds.textField(self.remove_suffix_field, query=True, text=True)
        if not suffix:
            cmds.warning("Enter a suffix to remove")
            return
        self.preview_list = self.get_new_names(lambda name: name[:-len(suffix)] if name.endswith(suffix) else name)
        self.preview_changes()
    
    def remove_all_suffixes(self):
        self.preview_list = self.get_new_names(lambda name: name.rsplit('_', 1)[0] if '_' in name else name)
        self.preview_changes()
    
    # Find & Replace
    def find_replace(self):
        find_text = cmds.textField(self.find_field, query=True, text=True)
        replace_text = cmds.textField(self.replace_field, query=True, text=True)
        use_regex = cmds.checkBox(self.regex_checkbox, query=True, value=True)
        case_sensitive = cmds.checkBox(self.case_sensitive_checkbox, query=True, value=True)
        
        if not find_text:
            cmds.warning("Enter text to find")
            return
        
        def replace_func(name):
            if use_regex:
                flags = 0 if case_sensitive else re.IGNORECASE
                return re.sub(find_text, replace_text, name, flags=flags)
            else:
                if case_sensitive:
                    return name.replace(find_text, replace_text)
                else:
                    pattern = re.compile(re.escape(find_text), re.IGNORECASE)
                    return pattern.sub(replace_text, name)
        
        self.preview_list = self.get_new_names(replace_func)
        self.preview_changes()
    
    def quick_replace(self, find_text, replace_text):
        self.preview_list = self.get_new_names(lambda name: name.replace(find_text, replace_text))
        self.preview_changes()
    
    def remove_numbers(self):
        self.preview_list = self.get_new_names(lambda name: re.sub(r'\d+', '', name))
        self.preview_changes()
    
    def remove_special_chars(self):
        self.preview_list = self.get_new_names(lambda name: re.sub(r'[^a-zA-Z0-9_]', '', name))
        self.preview_changes()
    
    # Numbering
    def apply_numbering(self):
        base_name = cmds.textField(self.base_name_field, query=True, text=True)
        start_num = cmds.intField(self.start_number_field, query=True, value=True)
        padding = cmds.intField(self.padding_field, query=True, value=True)
        separator = cmds.textField(self.separator_field, query=True, text=True)
        
        # Use flatten to get all objects in hierarchy
        selection = cmds.ls(selection=True, long=True, flatten=True)
        if not selection:
            cmds.warning("Nothing selected")
            return
        
        self.preview_list = []
        for i, obj in enumerate(selection):
            short_name = obj.split('|')[-1]
            num_str = str(start_num + i).zfill(padding)
            new_name = f"{base_name}{separator}{num_str}"
            self.preview_list.append((obj, short_name, new_name))
        
        self.preview_changes()
    
    def renumber_selection(self):
        start_num = cmds.intField(self.renumber_start_field, query=True, value=True)
        padding = cmds.intField(self.renumber_padding_field, query=True, value=True)
        
        # Use flatten to get all objects in hierarchy
        selection = cmds.ls(selection=True, long=True, flatten=True)
        if not selection:
            cmds.warning("Nothing selected")
            return
        
        self.preview_list = []
        for i, obj in enumerate(selection):
            short_name = obj.split('|')[-1]
            # Remove existing number suffix
            base = re.sub(r'_?\d+$', '', short_name)
            num_str = str(start_num + i).zfill(padding)
            new_name = f"{base}_{num_str}"
            self.preview_list.append((obj, short_name, new_name))
        
        self.preview_changes()
    
    # Case Conversion
    def convert_case(self, case_type):
        def case_func(name):
            if case_type == "upper":
                return name.upper()
            elif case_type == "lower":
                return name.lower()
            elif case_type == "title":
                return name.title()
            elif case_type == "camel":
                parts = re.split(r'[_\s]+', name)
                return parts[0].lower() + ''.join(p.title() for p in parts[1:])
            elif case_type == "pascal":
                parts = re.split(r'[_\s]+', name)
                return ''.join(p.title() for p in parts)
            return name
        
        self.preview_list = self.get_new_names(case_func)
        self.preview_changes()
    
    # Cleanup
    def clean_duplicate_prefixes(self):
        def clean_func(name):
            parts = name.split('_')
            cleaned = []
            last = None
            for part in parts:
                if part != last or len(cleaned) == 0:
                    cleaned.append(part)
                last = part
            return '_'.join(cleaned)
        
        self.preview_list = self.get_new_names(clean_func)
        self.preview_changes()
    
    def clean_duplicate_suffixes(self):
        def clean_func(name):
            parts = name.split('_')
            if len(parts) < 2:
                return name
            base = parts[0]
            last = None
            for part in parts[1:]:
                if part != last:
                    base += '_' + part
                last = part
            return base
        
        self.preview_list = self.get_new_names(clean_func)
        self.preview_changes()
    
    def trim_whitespace(self):
        self.preview_list = self.get_new_names(lambda name: name.strip())
        self.preview_changes()
    
    def clean_multiple_underscores(self):
        self.preview_list = self.get_new_names(lambda name: re.sub(r'_+', '_', name))
        self.preview_changes()
    
    def remove_namespace(self):
        self.preview_list = self.get_new_names(lambda name: name.split(':')[-1] if ':' in name else name)
        self.preview_changes()
    
    # Presets
    def save_preset(self):
        file_path = cmds.fileDialog2(fileMode=0, caption="Save Naming Preset", fileFilter="JSON Files (*.json)")
        if file_path:
            preset = {
                "add_prefix": cmds.textField(self.add_prefix_field, query=True, text=True),
                "add_suffix": cmds.textField(self.add_suffix_field, query=True, text=True),
                "find": cmds.textField(self.find_field, query=True, text=True),
                "replace": cmds.textField(self.replace_field, query=True, text=True),
                "base_name": cmds.textField(self.base_name_field, query=True, text=True),
                "start_number": cmds.intField(self.start_number_field, query=True, value=True),
                "padding": cmds.intField(self.padding_field, query=True, value=True)
            }
            try:
                with open(file_path[0], 'w') as f:
                    json.dump(preset, f, indent=4)
                print(f"Preset saved to: {file_path[0]}")
            except Exception as e:
                cmds.warning(f"Failed to save preset: {e}")
    
    def load_preset(self):
        file_path = cmds.fileDialog2(fileMode=1, caption="Load Naming Preset", fileFilter="JSON Files (*.json)")
        if file_path:
            try:
                with open(file_path[0], 'r') as f:
                    preset = json.load(f)
                cmds.textField(self.add_prefix_field, edit=True, text=preset.get("add_prefix", ""))
                cmds.textField(self.add_suffix_field, edit=True, text=preset.get("add_suffix", ""))
                cmds.textField(self.find_field, edit=True, text=preset.get("find", ""))
                cmds.textField(self.replace_field, edit=True, text=preset.get("replace", ""))
                cmds.textField(self.base_name_field, edit=True, text=preset.get("base_name", ""))
                cmds.intField(self.start_number_field, edit=True, value=preset.get("start_number", 1))
                cmds.intField(self.padding_field, edit=True, value=preset.get("padding", 2))
                print(f"Preset loaded from: {file_path[0]}")
            except Exception as e:
                cmds.warning(f"Failed to load preset: {e}")
    
    def apply_preset_ctrl(self):
        cmds.textField(self.add_suffix_field, edit=True, text="_CTRL")
        self.add_suffix()
    
    def apply_preset_grp(self):
        cmds.textField(self.add_suffix_field, edit=True, text="_GRP")
        self.add_suffix()
    
    def apply_preset_jnt(self):
        cmds.textField(self.add_suffix_field, edit=True, text="_JNT")
        self.add_suffix()
    
    def apply_preset_geo(self):
        cmds.textField(self.add_suffix_field, edit=True, text="_GEO")
        self.add_suffix()
    
    def apply_preset_loc(self):
        cmds.textField(self.add_suffix_field, edit=True, text="_LOC")
        self.add_suffix()
    
    def close_window(self, *args):
        if cmds.window(self.window_name, exists=True):
            cmds.deleteUI(self.window_name, window=True)

def show_pro_naming_manager():
    """Launch the Pro Naming Manager UI"""
    manager = ProNamingManager()
    manager.create_ui()

if __name__ == "__main__":
    show_pro_naming_manager()
else:
    show_pro_naming_manager()

import maya.cmds as cmds
import maya.mel as mel

class SuffixPrefixManager:
    def __init__(self):
        self.window_name = "SuffixPrefixManagerUI"
        self.window_title = "Suffix/Prefix Manager"
        
    def create_ui(self):
        # Delete existing window if it exists
        if cmds.window(self.window_name, exists=True):
            cmds.deleteUI(self.window_name, window=True)
        
        # Create main window
        self.window = cmds.window(
            self.window_name,
            title=self.window_title,
            widthHeight=(400, 350),
            resizeToFitChildren=True,
            sizeable=True
        )
        
        # Main layout with proper spacing
        form_layout = cmds.formLayout()
        main_layout = cmds.columnLayout(adjustableColumn=True, rowSpacing=5, parent=form_layout)
        
        # Add some padding
        cmds.separator(height=10, style="none")
        
        # Title
        cmds.text(label="Suffix/Prefix Manager", font="boldLabelFont", height=30)
        cmds.separator(height=10, style="in")
        
        # Selection info
        cmds.text(label="Selected Objects:", align="left", font="boldLabelFont")
        self.selection_text = cmds.scrollField(
            wordWrap=True, 
            height=60, 
            editable=False,
            backgroundColor=(0.2, 0.2, 0.2)
        )
        
        cmds.button(label="Refresh Selection", command=self.refresh_selection)
        cmds.separator(height=15)
        
        # Suffix Section
        cmds.text(label="SUFFIX OPERATIONS", font="boldLabelFont")
        cmds.separator(height=5)
        
        suffix_frame = cmds.frameLayout(label="Suffix Controls", collapsable=True, collapse=False)
        cmds.columnLayout(adjustableColumn=True, parent=suffix_frame)
        
        cmds.rowLayout(numberOfColumns=3, columnWidth3=(120, 200, 60), parent=suffix_frame)
        cmds.text(label="Add Suffix:", align="right")
        self.add_suffix_field = cmds.textField(text="_CON", placeholderText="e.g., _CON")
        cmds.button(label="Add", command=self.add_suffix)
        cmds.setParent('..')
        
        cmds.rowLayout(numberOfColumns=3, columnWidth3=(120, 200, 60), parent=suffix_frame)
        cmds.text(label="Remove Suffix:", align="right")
        self.remove_suffix_field = cmds.textField(text="_CON", placeholderText="e.g., _CON")
        cmds.button(label="Remove", command=self.remove_suffix)
        cmds.setParent('..')
        
        cmds.separator(height=10, parent=suffix_frame)
        cmds.button(label="Remove ALL Suffixes (everything after last _)", 
                   command=self.remove_all_suffixes, parent=suffix_frame)
        
        cmds.setParent(main_layout)
        cmds.separator(height=15)
        
        # Prefix Section
        cmds.text(label="PREFIX OPERATIONS", font="boldLabelFont")
        cmds.separator(height=5)
        
        prefix_frame = cmds.frameLayout(label="Prefix Controls", collapsable=True, collapse=False)
        cmds.columnLayout(adjustableColumn=True, parent=prefix_frame)
        
        cmds.rowLayout(numberOfColumns=3, columnWidth3=(120, 200, 60), parent=prefix_frame)
        cmds.text(label="Add Prefix:", align="right")
        self.add_prefix_field = cmds.textField(text="CTRL_", placeholderText="e.g., CTRL_")
        cmds.button(label="Add", command=self.add_prefix)
        cmds.setParent('..')
        
        cmds.rowLayout(numberOfColumns=3, columnWidth3=(120, 200, 60), parent=prefix_frame)
        cmds.text(label="Remove Prefix:", align="right")
        self.remove_prefix_field = cmds.textField(text="CTRL_", placeholderText="e.g., CTRL_")
        cmds.button(label="Remove", command=self.remove_prefix)
        cmds.setParent('..')
        
        cmds.separator(height=10, parent=prefix_frame)
        cmds.button(label="Remove ALL Prefixes (everything before first _)", 
                   command=self.remove_all_prefixes, parent=prefix_frame)
        
        cmds.setParent(main_layout)
        cmds.separator(height=15)
        
        # Utility buttons
        cmds.text(label="UTILITIES", font="boldLabelFont")
        cmds.separator(height=5)
        
        cmds.rowLayout(numberOfColumns=2, columnWidth2=(190, 190))
        cmds.button(label="Clean Duplicate Suffixes", command=self.clean_duplicate_suffixes)
        cmds.button(label="Clean Duplicate Prefixes", command=self.clean_duplicate_prefixes)
        cmds.setParent('..')
        
        cmds.separator(height=10)
        cmds.button(label="Close", command=self.close_window)
        
        # Add bottom padding
        cmds.separator(height=10, style="none")
        
        # Set form layout constraints
        cmds.formLayout(form_layout, edit=True, 
                       attachForm=[(main_layout, 'top', 10),
                                 (main_layout, 'left', 10),
                                 (main_layout, 'right', 10),
                                 (main_layout, 'bottom', 10)])
        
        # Show window and refresh selection
        cmds.showWindow(self.window)
        self.refresh_selection()
    
    def refresh_selection(self, *args):
        """Refresh the selection display"""
        selection = cmds.ls(selection=True)
        if selection:
            selection_info = f"Selected {len(selection)} objects:\n"
            selection_info += "\n".join([obj.split('|')[-1] for obj in selection[:10]])
            if len(selection) > 10:
                selection_info += f"\n... and {len(selection) - 10} more"
        else:
            selection_info = "No objects selected"
        
        cmds.scrollField(self.selection_text, edit=True, text=selection_info)
    
    def add_suffix(self, *args):
        """Add suffix to selected objects"""
        suffix = cmds.textField(self.add_suffix_field, query=True, text=True)
        if not suffix:
            cmds.warning("Please enter a suffix to add")
            return
        
        selection = cmds.ls(selection=True, long=True)
        if not selection:
            cmds.warning("Nothing selected")
            return
        
        renamed = []
        for obj in selection:
            original_name = obj.split('|')[-1]
            if not original_name.endswith(suffix):
                new_name = original_name + suffix
                try:
                    result = cmds.rename(obj, new_name)
                    renamed.append(f"{original_name} -> {new_name}")
                except Exception as e:
                    cmds.warning(f"Could not rename {original_name}: {e}")
        
        if renamed:
            print(f"Added suffix '{suffix}' to {len(renamed)} objects:")
            for item in renamed:
                print(f"  {item}")
        else:
            print(f"No objects needed suffix '{suffix}' added")
        
        self.refresh_selection()
    
    def remove_suffix(self, *args):
        """Remove specific suffix from selected objects"""
        suffix = cmds.textField(self.remove_suffix_field, query=True, text=True)
        if not suffix:
            cmds.warning("Please enter a suffix to remove")
            return
        
        selection = cmds.ls(selection=True, long=True)
        if not selection:
            cmds.warning("Nothing selected")
            return
        
        renamed = []
        for obj in selection:
            original_name = obj.split('|')[-1]
            if original_name.endswith(suffix):
                new_name = original_name[:-len(suffix)]
                if new_name:  # Make sure we don't create empty names
                    try:
                        result = cmds.rename(obj, new_name)
                        renamed.append(f"{original_name} -> {new_name}")
                    except Exception as e:
                        cmds.warning(f"Could not rename {original_name}: {e}")
        
        if renamed:
            print(f"Removed suffix '{suffix}' from {len(renamed)} objects:")
            for item in renamed:
                print(f"  {item}")
        else:
            print(f"No objects had suffix '{suffix}' to remove")
        
        self.refresh_selection()
    
    def add_prefix(self, *args):
        """Add prefix to selected objects"""
        prefix = cmds.textField(self.add_prefix_field, query=True, text=True)
        if not prefix:
            cmds.warning("Please enter a prefix to add")
            return
        
        selection = cmds.ls(selection=True, long=True)
        if not selection:
            cmds.warning("Nothing selected")
            return
        
        renamed = []
        for obj in selection:
            original_name = obj.split('|')[-1]
            if not original_name.startswith(prefix):
                new_name = prefix + original_name
                try:
                    result = cmds.rename(obj, new_name)
                    renamed.append(f"{original_name} -> {new_name}")
                except Exception as e:
                    cmds.warning(f"Could not rename {original_name}: {e}")
        
        if renamed:
            print(f"Added prefix '{prefix}' to {len(renamed)} objects:")
            for item in renamed:
                print(f"  {item}")
        else:
            print(f"No objects needed prefix '{prefix}' added")
        
        self.refresh_selection()
    
    def remove_prefix(self, *args):
        """Remove specific prefix from selected objects"""
        prefix = cmds.textField(self.remove_prefix_field, query=True, text=True)
        if not prefix:
            cmds.warning("Please enter a prefix to remove")
            return
        
        selection = cmds.ls(selection=True, long=True)
        if not selection:
            cmds.warning("Nothing selected")
            return
        
        renamed = []
        for obj in selection:
            original_name = obj.split('|')[-1]
            if original_name.startswith(prefix):
                new_name = original_name[len(prefix):]
                if new_name:  # Make sure we don't create empty names
                    try:
                        result = cmds.rename(obj, new_name)
                        renamed.append(f"{original_name} -> {new_name}")
                    except Exception as e:
                        cmds.warning(f"Could not rename {original_name}: {e}")
        
        if renamed:
            print(f"Removed prefix '{prefix}' from {len(renamed)} objects:")
            for item in renamed:
                print(f"  {item}")
        else:
            print(f"No objects had prefix '{prefix}' to remove")
        
        self.refresh_selection()
    
    def remove_all_suffixes(self, *args):
        """Remove everything after the last underscore"""
        selection = cmds.ls(selection=True, long=True)
        if not selection:
            cmds.warning("Nothing selected")
            return
        
        renamed = []
        for obj in selection:
            original_name = obj.split('|')[-1]
            if '_' in original_name:
                new_name = original_name.rsplit('_', 1)[0]  # Remove everything after last _
                if new_name and new_name != original_name:
                    try:
                        result = cmds.rename(obj, new_name)
                        renamed.append(f"{original_name} -> {new_name}")
                    except Exception as e:
                        cmds.warning(f"Could not rename {original_name}: {e}")
        
        if renamed:
            print(f"Removed all suffixes from {len(renamed)} objects:")
            for item in renamed:
                print(f"  {item}")
        else:
            print("No objects had suffixes to remove")
        
        self.refresh_selection()
    
    def remove_all_prefixes(self, *args):
        """Remove everything before the first underscore"""
        selection = cmds.ls(selection=True, long=True)
        if not selection:
            cmds.warning("Nothing selected")
            return
        
        renamed = []
        for obj in selection:
            original_name = obj.split('|')[-1]
            if '_' in original_name:
                new_name = original_name.split('_', 1)[1]  # Remove everything before first _
                if new_name and new_name != original_name:
                    try:
                        result = cmds.rename(obj, new_name)
                        renamed.append(f"{original_name} -> {new_name}")
                    except Exception as e:
                        cmds.warning(f"Could not rename {original_name}: {e}")
        
        if renamed:
            print(f"Removed all prefixes from {len(renamed)} objects:")
            for item in renamed:
                print(f"  {item}")
        else:
            print("No objects had prefixes to remove")
        
        self.refresh_selection()
    
    def clean_duplicate_suffixes(self, *args):
        """Remove duplicate suffixes (like _CON_CON_CON -> _CON)"""
        selection = cmds.ls(selection=True, long=True)
        if not selection:
            cmds.warning("Nothing selected")
            return
        
        renamed = []
        for obj in selection:
            original_name = obj.split('|')[-1]
            parts = original_name.split('_')
            if len(parts) > 1:
                # Find the last unique part
                base_name = parts[0]
                last_suffix = None
                
                # Build name removing duplicate suffixes
                for i, part in enumerate(parts[1:], 1):
                    if part != last_suffix:
                        base_name += '_' + part
                        last_suffix = part
                
                if base_name != original_name:
                    try:
                        result = cmds.rename(obj, base_name)
                        renamed.append(f"{original_name} -> {base_name}")
                    except Exception as e:
                        cmds.warning(f"Could not rename {original_name}: {e}")
        
        if renamed:
            print(f"Cleaned duplicate suffixes from {len(renamed)} objects:")
            for item in renamed:
                print(f"  {item}")
        else:
            print("No duplicate suffixes found")
        
        self.refresh_selection()
    
    def clean_duplicate_prefixes(self, *args):
        """Remove duplicate prefixes (like CTRL_CTRL_object -> CTRL_object)"""
        selection = cmds.ls(selection=True, long=True)
        if not selection:
            cmds.warning("Nothing selected")
            return
        
        renamed = []
        for obj in selection:
            original_name = obj.split('|')[-1]
            parts = original_name.split('_')
            if len(parts) > 1:
                # Remove duplicate prefixes from the beginning
                cleaned_parts = []
                last_part = None
                
                for part in parts:
                    if part != last_part or len(cleaned_parts) == 0:
                        cleaned_parts.append(part)
                        last_part = part
                
                new_name = '_'.join(cleaned_parts)
                if new_name != original_name:
                    try:
                        result = cmds.rename(obj, new_name)
                        renamed.append(f"{original_name} -> {new_name}")
                    except Exception as e:
                        cmds.warning(f"Could not rename {original_name}: {e}")
        
        if renamed:
            print(f"Cleaned duplicate prefixes from {len(renamed)} objects:")
            for item in renamed:
                print(f"  {item}")
        else:
            print("No duplicate prefixes found")
        
        self.refresh_selection()
    
    def close_window(self, *args):
        """Close the window"""
        if cmds.window(self.window_name, exists=True):
            cmds.deleteUI(self.window_name, window=True)

# Function to launch the UI
def show_suffix_prefix_manager():
    """Launch the Suffix/Prefix Manager UI"""
    manager = SuffixPrefixManager()
    manager.create_ui()

# Run the UI
if __name__ == "__main__":
    show_suffix_prefix_manager()
else:
    # If imported, you can call: suffix_prefix_manager.show_suffix_prefix_manager()
    show_suffix_prefix_manager()
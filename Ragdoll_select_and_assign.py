import maya.cmds as mc
from ragdoll import interactive as ri
import json

def select_and_assign():
    """
    Executes a series of select commands and runs `ri.assign_and_connect()` after each selection.
    Maintains the selection order in the hierarchy.
    """
    selections = [ ]
    

    for selection in selections:
        mc.select(selection, replace=True)
        ri.assign_and_connect()

# Run the function (commented out - use GUI instead)
# select_and_assign()


# Marker assignment (commented out - can be run separately if needed)
# objects = [
#     "Fox_RIG_v001_RELEASE:pCube1",
#     "Fox_RIG_v001_RELEASE:pCube3",
#     "Fox_RIG_v001_RELEASE:pCube4",
#     "Fox_RIG_v001_RELEASE:pCube5"
# ]
# 
# for obj in objects:
#     mc.select(obj, r=True)
#     ri.assign_marker()
#     # The marker node is assumed to be named rMarker_<objectName>
#     marker_name = "rMarker_" + obj.split(":")[-1]
#     try:
#         mc.setAttr(f"{marker_name}.inputType", 2)
#     except Exception as e:
#         print(f"Could not set inputType for {marker_name}: {e}")


# --- GUI SUPPORT ---
class SelectAndAssignGUI:
    def __init__(self):
        self.selections = []
        self.window = "SelectAndAssignWin"
        self.list_control = None
        self.input_field = None
        self.build_gui()

    def build_gui(self):
        if mc.window(self.window, exists=True):
            mc.deleteUI(self.window)
        mc.window(self.window, title="Select and Assign GUI", widthHeight=(600, 400))
        mc.columnLayout(adjustableColumn=True, rowSpacing=8)
        mc.text(label="Joint Chain Selections", font="boldLabelFont")
        self.list_control = mc.textScrollList(numberOfRows=12, allowMultiSelection=True, height=200)
        self.refresh_list()
        mc.rowLayout(numberOfColumns=2, adjustableColumn=2, columnWidth2=(120, 400))
        mc.text(label="Add Chain (comma-separated):")
        self.input_field = mc.textField()
        mc.setParent("..")
        mc.rowLayout(numberOfColumns=4, columnWidth4=(120, 120, 120, 120), adjustableColumn=4)
        mc.button(label="Add Chain", command=self.add_chain)
        mc.button(label="Add Selection", command=self.add_selection)
        mc.button(label="Remove Selected", command=self.remove_selected)
        mc.button(label="Run Assignment", command=self.run_assignment, backgroundColor=[0.3, 0.7, 0.3])
        mc.setParent("..")
        mc.separator(height=10, style="in")
        mc.rowLayout(numberOfColumns=2, columnWidth2=(290, 290))
        mc.button(label="Save List to JSON", command=self.save_to_json, backgroundColor=[0.4, 0.4, 0.6])
        mc.button(label="Load List from JSON", command=self.load_from_json, backgroundColor=[0.4, 0.6, 0.4])
        mc.setParent("..")
        mc.separator(height=10, style="in")
        mc.button(label="Close", command=lambda *_: mc.deleteUI(self.window), backgroundColor=[0.7, 0.3, 0.3])
        mc.showWindow(self.window)

    def refresh_list(self):
        mc.textScrollList(self.list_control, edit=True, removeAll=True)
        for chain in self.selections:
            mc.textScrollList(self.list_control, edit=True, append=", ".join(chain))

    def add_chain(self, *_):
        text = mc.textField(self.input_field, query=True, text=True)
        if text.strip():
            joints = [j.strip() for j in text.split(",") if j.strip()]
            if joints:
                self.selections.append(joints)
                self.refresh_list()
                mc.textField(self.input_field, edit=True, text="")

    def add_selection(self, *_):
        sel = mc.ls(selection=True, long=False)
        if sel:
            self.selections.append(sel)
            self.refresh_list()
            print(f"Added current selection as chain: {sel}")
        else:
            print("No objects selected in Maya.")

    def remove_selected(self, *_):
        idx = mc.textScrollList(self.list_control, query=True, selectIndexedItem=True)
        if idx:
            # Sort in reverse order to delete from end to start (avoids index shifting issues)
            for i in sorted(idx, reverse=True):
                del self.selections[i - 1]
            self.refresh_list()

    def save_to_json(self, *_):
        file_path = mc.fileDialog2(fileMode=0, caption="Save Joint Chain List", fileFilter="JSON Files (*.json)")
        if file_path:
            try:
                with open(file_path[0], 'w') as f:
                    json.dump(self.selections, f, indent=4)
                print(f"Saved joint chain list to: {file_path[0]}")
                mc.confirmDialog(title="Success", message=f"Saved to:\n{file_path[0]}", button=["OK"])
            except Exception as e:
                mc.warning(f"Failed to save: {e}")
                mc.confirmDialog(title="Error", message=f"Failed to save:\n{e}", button=["OK"])

    def load_from_json(self, *_):
        file_path = mc.fileDialog2(fileMode=1, caption="Load Joint Chain List", fileFilter="JSON Files (*.json)")
        if file_path:
            try:
                with open(file_path[0], 'r') as f:
                    self.selections = json.load(f)
                self.refresh_list()
                print(f"Loaded joint chain list from: {file_path[0]}")
                mc.confirmDialog(title="Success", message=f"Loaded from:\n{file_path[0]}\n\n{len(self.selections)} chains loaded.", button=["OK"])
            except Exception as e:
                mc.warning(f"Failed to load: {e}")
                mc.confirmDialog(title="Error", message=f"Failed to load:\n{e}", button=["OK"])

    def run_assignment(self, *_):
        for chain in self.selections:
            resolved = []
            for j in chain:
                # Try to find the object - handles both regular names and namespaced names
                matches = mc.ls(j, long=True)
                
                # If not found and doesn't have namespace, try with wildcard for any namespace
                if not matches and ':' not in j:
                    # For hierarchical paths (with |), add namespace to each part
                    if '|' in j:
                        # Split the path and add namespace to each part
                        parts = j.split('|')
                        namespaced_path = '|'.join([f"*:{part}" for part in parts])
                        matches = mc.ls(namespaced_path, long=True)
                    else:
                        # Simple name without hierarchy
                        matches = mc.ls(f"*:{j}", long=True)
                    
                    if matches:
                        print(f"Info: Found '{j}' as '{matches[0].split('|')[-1]}'")
                
                if not matches:
                    print(f"Warning: {j} does not exist in the scene.")
                elif len(matches) > 1:
                    print(f"Warning: More than one object matches name: {j} -> Using first match: {matches[0].split('|')[-1]}")
                    resolved.append(matches[0])
                else:
                    resolved.append(matches[0])
            
            if resolved:
                print(f"\nProcessing chain with {len(resolved)} joints...")
                mc.select(resolved, replace=True)
                ri.assign_and_connect()
                print(f"✓ Chain completed")

# To launch the GUI, run:
def launch_select_and_assign_gui():
    SelectAndAssignGUI()

# Launch the GUI automatically when the script is run:
launch_select_and_assign_gui()

"""
Toggle Default Material in Maya Viewport

This script toggles the "Use Default Material" option for the active viewport in Maya.
It executes MEL commands to toggle the setting.
"""

import maya.mel as mel

def toggle_default_material():
    """
    Toggles the Use Default Material option for the focused model panel.
    """
    try:
        # Get the panel with focus
        panel = mel.eval('getPanel -withFocus')
        
        # Query the current state
        current_state = mel.eval('modelEditor -q -udm ' + panel)
        # Toggle it
        new_state = 'false' if current_state else 'true'
        mel.eval('modelEditor -e -udm ' + new_state + ' ' + panel)
        print(f"Use Default Material toggled to: {new_state} on {panel}")
    except Exception as e:
        print(f"Error: {e}")

# Run the function
toggle_default_material()
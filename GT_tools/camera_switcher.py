#!/usr/bin/env python
"""
Maya Camera Switcher Tool
A Python tool for Autodesk Maya that allows switching between perspective cameras in the scene.

Usage:
1. Copy this script to your Maya scripts folder or run it in the Maya Script Editor.
2. Execute the script to open the camera switcher window.
3. Select a camera from the list to switch to it.

Author: GitHub Copilot
Date: September 3, 2025
"""

import maya.cmds as cmds
import maya.mel as mel

# Global variables for cycling
camera_checkboxes = {}
checked_cameras = []
current_index = 0
saved_cameras = []

def get_perspective_cameras():
    """
    Get all perspective cameras in the scene.
    Returns a list of camera transform nodes (not the shape nodes).
    """
    all_cameras = cmds.ls(type='camera')
    perspective_cameras = []

    for cam in all_cameras:
        # Get the transform node (parent of the camera shape)
        transform_node = cmds.listRelatives(cam, parent=True)[0]

        # Check if it's a perspective camera (not orthographic)
        if not cmds.getAttr(cam + '.orthographic'):
            perspective_cameras.append(transform_node)

    return perspective_cameras

def switch_to_camera(camera_name):
    """
    Switch the active camera to the specified camera.
    """
    try:
        # Set the camera as the active view
        cmds.lookThru(camera_name)
        print(f"Switched to camera: {camera_name}")
    except Exception as e:
        cmds.error(f"Failed to switch to camera {camera_name}: {str(e)}")

def update_checked_cameras(camera):
    """
    Update the list of checked cameras based on checkbox state.
    """
    global checked_cameras
    if cmds.checkBox(camera_checkboxes[camera], query=True, value=True):
        if camera not in checked_cameras:
            checked_cameras.append(camera)
    else:
        if camera in checked_cameras:
            checked_cameras.remove(camera)

def switch_cycle(*args):
    """
    Cycle through the checked cameras. Accepts optional args from UI callbacks.
    Uses saved selection if present.
    """
    global current_index, camera_checkboxes, checked_cameras, saved_cameras
    # Prefer saved selection if available
    active_list = saved_cameras if saved_cameras else checked_cameras

    # If active list is empty, default to all perspective cameras
    if not active_list:
        cams = get_perspective_cameras()
        if not cams:
            cmds.warning("No perspective cameras found.")
            return
        active_list = cams[:]
        # Update UI checkboxes to reflect default if present
        for cam, cb in list(camera_checkboxes.items()):
            try:
                cmds.checkBox(cb, edit=True, value=(cam in active_list))
            except Exception:
                pass

    # wrap index
    if current_index >= len(active_list):
        current_index = 0

    # Attempt to switch; protect against missing camera
    cam = active_list[current_index]
    if cmds.objExists(cam):
        switch_to_camera(cam)
    else:
        cmds.warning(f"Camera '{cam}' no longer exists. Refreshing list.")
        refresh_camera_list()
        return

    current_index += 1

def save_selection(*args):
    """
    Save the currently checked cameras as the selection to use for switching.
    """
    global saved_cameras, camera_checkboxes, current_index
    saved = []
    for cam, cb in list(camera_checkboxes.items()):
        try:
            if cmds.checkBox(cb, query=True, value=True):
                saved.append(cam)
        except Exception:
            # checkbox might be invalid; ignore
            pass
    saved_cameras = saved
    current_index = 0
    cmds.confirmDialog(title="Saved", message=f"Saved {len(saved_cameras)} camera(s) for switching.")

def assign_hotkey_dialog(*args):
    """
    Open a dialog to assign a hotkey to the switch function. Accepts optional args from UI callbacks.
    """
    if cmds.window("hotkeyDialog", query=True, exists=True):
        cmds.deleteUI("hotkeyDialog")
    
    win = cmds.window("hotkeyDialog", title="Assign Hotkey", widthHeight=(300, 120))
    layout = cmds.columnLayout(adjustableColumn=True, rowSpacing=5)
    cmds.text(label="Enter your hotkey (e.g., a, Alt+s, Ctrl+Shift+f):")
    key_field = cmds.textField()
    cmds.separator(height=10)
    cmds.rowLayout(numberOfColumns=2, columnWidth2=(145, 145))
    cmds.button(label="Assign", command=lambda _=None: [assign_hotkey(cmds.textField(key_field, query=True, text=True)), cmds.deleteUI(win) if cmds.window(win, query=True, exists=True) else None])
    cmds.button(label="Cancel", command=lambda _=None: cmds.deleteUI(win))
    cmds.setParent('..')
    cmds.showWindow(win)

def assign_hotkey(key, *args):
    """
    Assign the hotkey to the switch_cycle function.
    key: string like 's' or 'Ctrl+Alt+S'. Accepts extra args from UI callbacks.
    """
    if not key:
        cmds.warning("No key entered.")
        return
    
    # Parse modifiers and base key
    key = key.strip()
    key_lower = key.lower()
    
    # Initialize modifiers
    ctrl = False
    alt = False
    shift = False
    base_key = ''
    
    # Split by + to separate modifiers from the base key
    if '+' in key:
        parts = [p.strip().lower() for p in key.split('+')]
        
        # Last part is the base key, everything else is modifiers
        base_key = parts[-1]
        modifiers = parts[:-1]
        
        # Check each modifier
        for mod in modifiers:
            if mod in ['ctrl', 'ctl', 'control']:
                ctrl = True
            elif mod in ['alt']:
                alt = True
            elif mod in ['shift', 'shft']:
                shift = True
    else:
        # No + sign, so the entire input is the base key (no modifiers)
        base_key = key_lower
    
    # Ensure base_key is only a single character (Maya hotkeys require single char)
    if len(base_key) > 1:
        cmds.warning(f"Hotkey must be a single character. Using first character: '{base_key[0]}'")
        base_key = base_key[0]
    elif len(base_key) == 0:
        cmds.warning("No key specified. Using 'a' as default.")
        base_key = 'a'
    
    # Create or ensure a nameCommand that calls the switch_cycle function.
    cmd_name = "switchCycle_cmd"
    
    # Use a simpler Python command that's easier to escape
    python_snippet = (
        "try:\\n"
        "    import camera_switcher\\n"
        "    camera_switcher.switch_cycle()\\n"
        "except:\\n"
        "    try:\\n"
        "        import __main__\\n"
        "        __main__.switch_cycle()\\n"
        "    except:\\n"
        "        pass"
    )
    
    try:
        # Check if nameCommand exists by trying to query it
        try:
            cmds.nameCommand(cmd_name, query=True, command=True)
            # If we get here, it exists, so edit it
            cmds.nameCommand(cmd_name, edit=True, command='python("' + python_snippet + '")')
        except:
            # nameCommand doesn't exist, create it
            cmds.nameCommand(cmd_name, annotation='Switch checked cameras', command='python("' + python_snippet + '")')
        
        # Assign the hotkey to the nameCommand with modifiers
        cmds.hotkey(k=base_key, alt=alt, ctl=ctrl, name=cmd_name)
        
        # Build modifier string for display
        mod_str = ""
        if ctrl:
            mod_str += "Ctrl+"
        if alt:
            mod_str += "Alt+"
        if shift:
            mod_str += "Shift+"
        
        cmds.confirmDialog(title="Success", message=f"Hotkey '{mod_str}{base_key}' assigned to Switch function.")
    except Exception as e:
        cmds.error(f"Failed to assign hotkey '{key}': {e}")

def create_camera_switcher_ui():
    """
    Create a simple UI window for switching between cameras.
    """
    # Check if window already exists
    if cmds.window("cameraSwitcherWindow", exists=True):
        cmds.deleteUI("cameraSwitcherWindow")

    # Create window
    window = cmds.window("cameraSwitcherWindow", title="Camera Switcher", widthHeight=(300, 400))

    # Create layout
    main_layout = cmds.columnLayout(adjustableColumn=True, rowSpacing=5)

    # Title
    cmds.text(label="Perspective Cameras", align="center", font="boldLabelFont")

    # Separator
    cmds.separator(style="in", height=10)

    # Get cameras
    cameras = get_perspective_cameras()

    if not cameras:
        cmds.text(label="No perspective cameras found in scene.", align="center")
    else:
        # Clear global lists
        global camera_checkboxes, checked_cameras
        camera_checkboxes = {}
        checked_cameras = []
        
        # Create checkboxes for each camera
        for cam in cameras:
            cb = cmds.checkBox(
                label=cam,
                value=True,
                changeCommand=lambda x, c=cam: update_checked_cameras(c)
            )
            camera_checkboxes[cam] = cb
            checked_cameras.append(cam)

    # Separator
    cmds.separator(style="in", height=10)

    # Switch button
    switch_button = cmds.button(
        label="Switch",
        command=switch_cycle,
        height=30,
        backgroundColor=[0.2, 0.8, 0.2]
    )
    
    # Add right-click menu to switch button
    cmds.popupMenu(parent=switch_button)
    cmds.menuItem(label="Assign Hotkey", command=assign_hotkey_dialog)

    # Refresh button
    cmds.button(
        label="Refresh Camera List",
        command=lambda: refresh_camera_list(),
        height=30,
        backgroundColor=[0.5, 0.7, 1.0]
    )

    # Save selection button
    cmds.button(
        label="Save Selection",
        command=save_selection,
        height=30,
        backgroundColor=[0.9, 0.9, 0.5]
    )

    # Close button
    cmds.button(
        label="Close",
        command=lambda: cmds.deleteUI(window),
        height=30,
        backgroundColor=[0.8, 0.5, 0.5]
    )

    # Show window
    cmds.showWindow(window)

def refresh_camera_list():
    """
    Refresh the camera list by recreating the UI.
    """
    global current_index
    current_index = 0
    create_camera_switcher_ui()

# Main execution
if __name__ == "__main__":
    create_camera_switcher_ui()

"""
Simple camera switcher hotkey script.
Cycles through perspective cameras in the scene.

To use as a hotkey:
1. Save this script to your Maya scripts folder
2. In Maya, go to Windows > Settings/Preferences > Hotkey Editor
3. Create a new Runtime Command with this Python code:
   import switch_camera_hotkey
   switch_camera_hotkey.switch_next_camera()
4. Assign your desired hotkey to that command

Or just run this in Script Editor and assign it to a shelf button.
"""

import maya.cmds as cmds

def switch_next_camera():
    """Switch to the next perspective camera in the scene."""
    # Get all perspective cameras
    all_cameras = cmds.ls(type='camera')
    perspective_cameras = []
    
    for cam in all_cameras:
        transform_node = cmds.listRelatives(cam, parent=True)[0]
        if not cmds.getAttr(cam + '.orthographic'):
            perspective_cameras.append(transform_node)
    
    if not perspective_cameras:
        cmds.warning("No perspective cameras found.")
        return
    
    # Get current camera
    current_panel = cmds.getPanel(withFocus=True)
    if cmds.getPanel(typeOf=current_panel) != 'modelPanel':
        # If not in a viewport, use the first modelPanel
        model_panels = cmds.getPanel(type='modelPanel')
        if model_panels:
            current_panel = model_panels[0]
        else:
            cmds.warning("No viewport found.")
            return
    
    try:
        current_camera = cmds.modelPanel(current_panel, query=True, camera=True)
        # Get transform if it's a shape node
        if cmds.nodeType(current_camera) == 'camera':
            current_camera = cmds.listRelatives(current_camera, parent=True)[0]
    except:
        current_camera = None
    
    # Find next camera
    try:
        current_index = perspective_cameras.index(current_camera)
        next_index = (current_index + 1) % len(perspective_cameras)
    except:
        next_index = 0
    
    next_camera = perspective_cameras[next_index]
    
    # Switch to next camera
    cmds.lookThru(current_panel, next_camera)
    print(f"Switched to camera: {next_camera}")

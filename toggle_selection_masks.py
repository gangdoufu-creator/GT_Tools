"""
Toggle Object Selection Masks
A tool to quickly toggle Maya's object selection masks on/off for different object types.
"""

import maya.cmds as cmds


def toggle_all_selection_masks(state=None):
    """
    Toggle all selection masks on or off.
    
    Args:
        state (bool): If True, enables all masks. If False, disables all. If None, toggles current state.
    """
    mask_types = [
        'handle', 'ikHandle', 'joint', 'light', 'locator', 'camera', 
        'nurbsCurve', 'nurbsSurface', 'polymesh', 'subdiv', 'plane', 
        'lattice', 'cluster', 'sculpt', 'nonlinear', 'particleShape',
        'emitter', 'field', 'spring', 'rigidBody', 'fluid', 'follicle',
        'hairSystem', 'pfxHair', 'nCloth', 'nParticle', 'nRigid', 'dynamicConstraint',
        'stroke', 'texture', 'implicitGeometry', 'dimension'
    ]
    
    if state is None:
        # Toggle - check current state of first mask
        current = cmds.selectType(query=True, handle=True)
        state = not current
    
    print(f"Setting all selection masks to: {'ON' if state else 'OFF'}")
    
    for mask in mask_types:
        try:
            cmds.selectType(**{mask: state})
        except Exception:
            pass


def toggle_specific_masks(joints=None, curves=None, meshes=None, locators=None, 
                         lights=None, cameras=None, handles=None):
    """
    Toggle specific selection mask types.
    
    Args:
        joints (bool): Toggle joint selection
        curves (bool): Toggle curve selection
        meshes (bool): Toggle mesh selection
        locators (bool): Toggle locator selection
        lights (bool): Toggle light selection
        cameras (bool): Toggle camera selection
        handles (bool): Toggle handle/IK handle selection
    """
    if joints is not None:
        cmds.selectType(joint=joints)
        print(f"Joints: {'ON' if joints else 'OFF'}")
    
    if curves is not None:
        cmds.selectType(nurbsCurve=curves)
        print(f"Curves: {'ON' if curves else 'OFF'}")
    
    if meshes is not None:
        cmds.selectType(polymesh=meshes)
        print(f"Meshes: {'ON' if meshes else 'OFF'}")
    
    if locators is not None:
        cmds.selectType(locator=locators)
        print(f"Locators: {'ON' if locators else 'OFF'}")
    
    if lights is not None:
        cmds.selectType(light=lights)
        print(f"Lights: {'ON' if lights else 'OFF'}")
    
    if cameras is not None:
        cmds.selectType(camera=cameras)
        print(f"Cameras: {'ON' if cameras else 'OFF'}")
    
    if handles is not None:
        cmds.selectType(handle=handles, ikHandle=handles)
        print(f"Handles: {'ON' if handles else 'OFF'}")


def enable_only_joints():
    """Enable only joint selection."""
    toggle_all_selection_masks(False)
    cmds.selectType(joint=True)
    print("Enabled: Joints only")


def enable_only_curves():
    """Enable only curve selection."""
    toggle_all_selection_masks(False)
    cmds.selectType(nurbsCurve=True)
    print("Enabled: Curves only")


def enable_only_meshes():
    """Enable only mesh selection."""
    toggle_all_selection_masks(False)
    cmds.selectType(polymesh=True)
    print("Enabled: Meshes only")


def enable_common_anim():
    """Enable common animation controls (curves, joints, handles)."""
    toggle_all_selection_masks(False)
    cmds.selectType(nurbsCurve=True, joint=True, handle=True, ikHandle=True)
    print("Enabled: Animation controls (curves, joints, handles)")


def create_ui():
    """Create a UI for toggling selection masks."""
    window_name = "toggleSelectionMasksWindow"
    
    # Delete existing window if it exists
    if cmds.window(window_name, exists=True):
        cmds.deleteUI(window_name)
    
    # Create window
    window = cmds.window(window_name, title="Toggle Selection Masks", widthHeight=(300, 400))
    
    main_layout = cmds.columnLayout(adjustableColumn=True, rowSpacing=5)
    
    cmds.separator(height=10, style="none")
    cmds.text(label="Selection Mask Toggle", font="boldLabelFont", align="center")
    cmds.separator(height=10, style="none")
    
    # All On/Off buttons
    cmds.text(label="All Masks:", align="left", font="boldLabelFont")
    cmds.rowLayout(numberOfColumns=2, columnWidth2=(145, 145), columnAlign=[(1, "center"), (2, "center")])
    cmds.button(label="All ON", 
                command=lambda x: toggle_all_selection_masks(True),
                backgroundColor=[0.3, 0.7, 0.3])
    cmds.button(label="All OFF", 
                command=lambda x: toggle_all_selection_masks(False),
                backgroundColor=[0.7, 0.3, 0.3])
    cmds.setParent("..")
    
    cmds.separator(height=15, style="in")
    
    # Preset buttons
    cmds.text(label="Quick Presets:", align="left", font="boldLabelFont")
    cmds.button(label="Joints Only", 
                command=lambda x: enable_only_joints(),
                backgroundColor=[0.4, 0.5, 0.6])
    cmds.button(label="Curves Only", 
                command=lambda x: enable_only_curves(),
                backgroundColor=[0.4, 0.5, 0.6])
    cmds.button(label="Meshes Only", 
                command=lambda x: enable_only_meshes(),
                backgroundColor=[0.4, 0.5, 0.6])
    cmds.button(label="Animation Controls (Curves + Joints + Handles)", 
                command=lambda x: enable_common_anim(),
                backgroundColor=[0.5, 0.6, 0.4])
    
    cmds.separator(height=15, style="in")
    
    # Individual toggles
    cmds.text(label="Toggle Individual:", align="left", font="boldLabelFont")
    
    cmds.rowLayout(numberOfColumns=2, columnWidth2=(145, 145), columnAlign=[(1, "center"), (2, "center")])
    cmds.button(label="Joints", 
                command=lambda x: toggle_specific_masks(joints=True))
    cmds.button(label="X Joints", 
                command=lambda x: toggle_specific_masks(joints=False),
                backgroundColor=[0.5, 0.3, 0.3])
    cmds.setParent("..")
    
    cmds.rowLayout(numberOfColumns=2, columnWidth2=(145, 145), columnAlign=[(1, "center"), (2, "center")])
    cmds.button(label="Curves", 
                command=lambda x: toggle_specific_masks(curves=True))
    cmds.button(label="X Curves", 
                command=lambda x: toggle_specific_masks(curves=False),
                backgroundColor=[0.5, 0.3, 0.3])
    cmds.setParent("..")
    
    cmds.rowLayout(numberOfColumns=2, columnWidth2=(145, 145), columnAlign=[(1, "center"), (2, "center")])
    cmds.button(label="Meshes", 
                command=lambda x: toggle_specific_masks(meshes=True))
    cmds.button(label="X Meshes", 
                command=lambda x: toggle_specific_masks(meshes=False),
                backgroundColor=[0.5, 0.3, 0.3])
    cmds.setParent("..")
    
    cmds.rowLayout(numberOfColumns=2, columnWidth2=(145, 145), columnAlign=[(1, "center"), (2, "center")])
    cmds.button(label="Locators", 
                command=lambda x: toggle_specific_masks(locators=True))
    cmds.button(label="X Locators", 
                command=lambda x: toggle_specific_masks(locators=False),
                backgroundColor=[0.5, 0.3, 0.3])
    cmds.setParent("..")
    
    cmds.rowLayout(numberOfColumns=2, columnWidth2=(145, 145), columnAlign=[(1, "center"), (2, "center")])
    cmds.button(label="Handles", 
                command=lambda x: toggle_specific_masks(handles=True))
    cmds.button(label="X Handles", 
                command=lambda x: toggle_specific_masks(handles=False),
                backgroundColor=[0.5, 0.3, 0.3])
    cmds.setParent("..")
    
    cmds.rowLayout(numberOfColumns=2, columnWidth2=(145, 145), columnAlign=[(1, "center"), (2, "center")])
    cmds.button(label="Cameras", 
                command=lambda x: toggle_specific_masks(cameras=True))
    cmds.button(label="X Cameras", 
                command=lambda x: toggle_specific_masks(cameras=False),
                backgroundColor=[0.5, 0.3, 0.3])
    cmds.setParent("..")
    
    cmds.rowLayout(numberOfColumns=2, columnWidth2=(145, 145), columnAlign=[(1, "center"), (2, "center")])
    cmds.button(label="Lights", 
                command=lambda x: toggle_specific_masks(lights=True))
    cmds.button(label="X Lights", 
                command=lambda x: toggle_specific_masks(lights=False),
                backgroundColor=[0.5, 0.3, 0.3])
    cmds.setParent("..")
    
    cmds.separator(height=10, style="none")
    
    cmds.showWindow(window)


# Quick execute functions
def all_on():
    """Quick function to enable all selection masks."""
    toggle_all_selection_masks(True)


def all_off():
    """Quick function to disable all selection masks."""
    toggle_all_selection_masks(False)


# Execute when script is run directly
if __name__ == "__main__":
    create_ui()

"""
Hide Wing Finger Controls
Hides intermediate wing finger controls (numbers 2, 4, 6) for cleaner viewport display.
Works on both left and right wings across all five fingers.
"""

import maya.cmds as cmds


def hide_wing_controls(rig_prefix="TyrantDragon_rig_Jaw_Control:", show=False):
    """
    Hide or show wing finger control shapes.
    
    Args:
        rig_prefix (str): The rig namespace/prefix (default: "TyrantDragon_rig_Jaw_Control:")
        show (bool): If True, shows the controls. If False, hides them. (default: False)
    """
    # Wing finger names
    fingers = [
        "FKwingFirst",
        "FKwingIndex",
        "FKwingMiddle",
        "FKwingRing",
        "FKwingPinky"
    ]
    
    # Sides
    sides = ["_L", "_R"]
    
    # Control numbers to hide (even numbers)
    control_numbers = [2, 4, 6]
    
    # Visibility value (0 = hide, 1 = show)
    visibility_value = 1 if show else 0
    action = "Showing" if show else "Hiding"
    
    hidden_count = 0
    skipped_count = 0
    
    print(f"\n{action} wing finger controls...")
    print(f"Rig Prefix: {rig_prefix}")
    print("-" * 60)
    
    for finger in fingers:
        for side in sides:
            for num in control_numbers:
                # Build the control and shape names
                # Shape name is the same as control name + "Shape" suffix
                control_name = f"{rig_prefix}{finger}{num}{side}"
                shape_name = f"{rig_prefix}{finger}{num}{side}Shape"
                
                # Check if control exists
                if cmds.objExists(control_name):
                    # Check if shape exists
                    if cmds.objExists(shape_name):
                        try:
                            cmds.setAttr(f"{shape_name}.visibility", visibility_value)
                            print(f"  ✓ {action}: {shape_name}")
                            hidden_count += 1
                        except Exception as e:
                            print(f"  ✗ Failed to modify {shape_name}: {e}")
                            skipped_count += 1
                    else:
                        print(f"  ⚠ Shape not found: {shape_name}")
                        skipped_count += 1
                else:
                    print(f"  ⚠ Control not found: {control_name}")
                    skipped_count += 1
    
    print("-" * 60)
    print(f"Complete! {action}: {hidden_count} controls")
    if skipped_count > 0:
        print(f"Skipped: {skipped_count} controls (not found or locked)")
    print()


def show_wing_controls(rig_prefix="TyrantDragon_rig_Jaw_Control:"):
    """
    Show previously hidden wing finger controls.
    
    Args:
        rig_prefix (str): The rig namespace/prefix (default: "TyrantDragon_rig_Jaw_Control:")
    """
    hide_wing_controls(rig_prefix=rig_prefix, show=True)


def toggle_wing_controls(rig_prefix="TyrantDragon_rig_Jaw_Control:"):
    """
    Toggle wing finger controls visibility based on current state.
    
    Args:
        rig_prefix (str): The rig namespace/prefix (default: "TyrantDragon_rig_Jaw_Control:")
    """
    # Check the first control to determine current state
    test_shape = f"{rig_prefix}FKwingFirst3_LShape"
    
    if cmds.objExists(test_shape):
        current_visibility = cmds.getAttr(f"{test_shape}.visibility")
        # If currently visible, hide them. If hidden, show them.
        hide_wing_controls(rig_prefix=rig_prefix, show=(current_visibility == 0))
    else:
        print(f"Cannot find test control: {test_shape}")
        print("Attempting to hide controls anyway...")
        hide_wing_controls(rig_prefix=rig_prefix, show=False)


# Quick execute functions
def hide():
    """Quick function to hide wing controls with default prefix."""
    hide_wing_controls()


def show():
    """Quick function to show wing controls with default prefix."""
    show_wing_controls()


def toggle():
    """Quick function to toggle wing controls with default prefix."""
    toggle_wing_controls()


# UI
def create_ui():
    """Create a simple UI for hiding/showing wing controls."""
    window_name = "hideWingControlsWindow"
    
    # Delete existing window if it exists
    if cmds.window(window_name, exists=True):
        cmds.deleteUI(window_name)
    
    # Create window
    window = cmds.window(window_name, title="Hide Wing Controls", widthHeight=(400, 150))
    
    main_layout = cmds.columnLayout(adjustableColumn=True, rowSpacing=5)
    
    cmds.separator(height=10, style="none")
    cmds.text(label="Wing Finger Control Visibility", font="boldLabelFont", align="center")
    cmds.separator(height=10, style="none")
    
    # Rig prefix field
    cmds.rowLayout(numberOfColumns=2, columnWidth2=(100, 280), adjustableColumn=2)
    cmds.text(label="Rig Prefix:", align="right")
    prefix_field = cmds.textField(text="TyrantDragon_rig_Jaw_Control:")
    cmds.setParent("..")
    
    cmds.separator(height=15, style="none")
    
    # Buttons
    cmds.rowLayout(numberOfColumns=3, columnWidth3=(130, 130, 130), columnAlign=[(1, "center"), (2, "center"), (3, "center")])
    cmds.button(label="Hide Controls", 
                command=lambda x: hide_wing_controls(rig_prefix=cmds.textField(prefix_field, query=True, text=True)),
                backgroundColor=[0.7, 0.3, 0.3])
    cmds.button(label="Show Controls", 
                command=lambda x: show_wing_controls(rig_prefix=cmds.textField(prefix_field, query=True, text=True)),
                backgroundColor=[0.3, 0.7, 0.3])
    cmds.button(label="Toggle", 
                command=lambda x: toggle_wing_controls(rig_prefix=cmds.textField(prefix_field, query=True, text=True)),
                backgroundColor=[0.4, 0.4, 0.7])
    cmds.setParent("..")
    
    cmds.separator(height=10, style="none")
    cmds.text(label="Hides shape visibility for controls 2, 4, 6 on all wing fingers", 
              font="smallPlainLabelFont", align="center")
    
    cmds.showWindow(window)


# Execute when script is run directly
if __name__ == "__main__":
    create_ui()

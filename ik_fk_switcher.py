#!/usr/bin/env python
"""
Maya IK/FK Switcher Tool for Dragon Rig
A Python tool for Autodesk Maya that automates IK/FK switching across the entire timeline.

Features:
- Switch from IK to FK (bakes IK animation to FK controls)
- Switch from FK to IK (bakes FK animation to IK controls)
- Automatic left/right leg detection
- Maintains all poses accurately throughout the timeline
- Works with dragon rig control naming convention

Usage:
1. Select the IK or FK controls you want to switch
2. Run the tool UI
3. Choose "IK to FK" or "FK to IK"
4. The tool will automatically bake the animation across your timeline

Author: GitHub Copilot
Date: October 28, 2025
"""

import maya.cmds as cmds
import maya.mel as mel

class IKFKSwitcher:
    """
    IK/FK Switcher for Dragon Rig
    """
    
    def __init__(self, namespace=""):
        """
        Initialize the IK/FK Switcher with dragon rig control names.
        
        Args:
            namespace (str): The rig namespace (e.g., "Proxy_Version_But_Bined_Skin_Instead:")
        """
        self.namespace = namespace
        
        # Control naming for dragon rig
        self.ik_controls = {
            'L': {
                'ik_handle': 'IKLeg_L',
                'pole_vector': 'PoleLeg_L',
                'switch_attr': 'FKIKLeg_L.FKIKBlend'
            },
            'R': {
                'ik_handle': 'IKLeg_R',
                'pole_vector': 'PoleLeg_R',
                'switch_attr': 'FKIKLeg_R.FKIKBlend'
            }
        }
        
        self.fk_controls = {
            'L': ['FKHip_L', 'FKKnee_L', 'FKKnee1_L', 'FKAnkle_L', 'FKToes_L'],
            'R': ['FKHip_R', 'FKKnee_R', 'FKKnee1_R', 'FKAnkle_R', 'FKToes_R']
        }
        
        self.joints = {
            'L': ['Hip_L', 'Knee_L', 'Knee1_L', 'Ankle_L'],
            'R': ['Hip_R', 'Knee_R', 'Knee1_R', 'Ankle_R']
        }
        
        # Switch values
        self.fk_value = 0
        self.ik_value = 10
        
        # IK control attributes
        self.ik_attrs = ['roll', 'rock', 'swivel']
    
    def get_namespaced_name(self, name):
        """
        Add namespace to a control or joint name.
        
        Args:
            name (str): The base name without namespace
            
        Returns:
            str: The full name with namespace
        """
        if self.namespace:
            return f"{self.namespace}{name}"
        return name
    
    def get_available_namespaces(self):
        """
        Get all available namespaces in the scene.
        
        Returns:
            list: List of namespace strings
        """
        namespaces = cmds.namespaceInfo(listOnlyNamespaces=True, recurse=True) or []
        # Filter out Maya default namespaces
        filtered = [ns for ns in namespaces if ns not in ['UI', 'shared']]
        # Add colon suffix for dropdown display
        return [f"{ns}:" for ns in filtered] + ["(No Namespace)"]
    
    def detect_namespace_from_selection(self):
        """
        Detect namespace from current selection.
        
        Returns:
            str: Detected namespace or empty string
        """
        selection = cmds.ls(selection=True)
        if not selection:
            return ""
        
        for obj in selection:
            if ':' in obj:
                # Extract namespace (everything before the last colon)
                parts = obj.split(':')
                if len(parts) > 1:
                    namespace = ':'.join(parts[:-1]) + ':'
                    return namespace
        
        return ""
    
    def detect_side_from_selection(self):
        """
        Detect which side (L or R) is selected.
        Returns 'L', 'R', or None if nothing relevant is selected.
        """
        selection = cmds.ls(selection=True)
        if not selection:
            cmds.warning("Nothing selected. Please select an IK or FK control.")
            return None
        
        for obj in selection:
            if '_L' in obj:
                return 'L'
            elif '_R' in obj:
                return 'R'
        
        cmds.warning("Could not detect side from selection. Please select a control with _L or _R suffix.")
        return None
    
    def get_time_range(self):
        """Get the current timeline range."""
        start = cmds.playbackOptions(query=True, minTime=True)
        end = cmds.playbackOptions(query=True, maxTime=True)
        return start, end
    
    def switch_ik_to_fk(self, side):
        """
        Switch from IK to FK by baking IK animation to FK controls.
        
        Args:
            side (str): 'L' or 'R' for left or right leg
        """
        if side not in ['L', 'R']:
            cmds.error("Invalid side. Must be 'L' or 'R'")
            return
        
        # Get controls and joints with namespace
        fk_ctrls = [self.get_namespaced_name(ctrl) for ctrl in self.fk_controls[side]]
        joints = [self.get_namespaced_name(jnt) for jnt in self.joints[side]]
        switch_attr = self.get_namespaced_name(self.ik_controls[side]['switch_attr'])
        
        # Check if controls exist
        missing = [ctrl for ctrl in fk_ctrls if not cmds.objExists(ctrl)]
        if missing:
            cmds.warning(f"Missing FK controls: {missing}")
            return
        
        missing_joints = [jnt for jnt in joints if not cmds.objExists(jnt)]
        if missing_joints:
            cmds.warning(f"Missing joints: {missing_joints}")
            return
        
        # Get time range
        start, end = self.get_time_range()
        
        print(f"Switching IK to FK for {side} side from frame {start} to {end}")
        
        # Store current time
        current_time = cmds.currentTime(query=True)
        
        # Create a temporary locator for matching
        temp_locators = []
        
        try:
            # Step 1: Set switch to IK mode first
            cmds.setAttr(switch_attr, self.ik_value)
            
            # Step 2: Bake FK controls to match IK animation
            for frame in range(int(start), int(end) + 1):
                cmds.currentTime(frame)
                
                # Match each FK control to its corresponding joint
                for fk_ctrl, joint in zip(fk_ctrls[:4], joints):  # Skip toes for now
                    if cmds.objExists(fk_ctrl) and cmds.objExists(joint):
                        # Get joint rotation in object space
                        joint_rot = cmds.getAttr(f"{joint}.rotate")[0]
                        
                        # Set FK control rotation
                        cmds.setAttr(f"{fk_ctrl}.rotateX", joint_rot[0])
                        cmds.setAttr(f"{fk_ctrl}.rotateY", joint_rot[1])
                        cmds.setAttr(f"{fk_ctrl}.rotateZ", joint_rot[2])
                        
                        # Set keyframe on FK control
                        cmds.setKeyframe(fk_ctrl, attribute='rotate')
            
            # Step 3: Switch to FK mode
            cmds.setKeyframe(switch_attr, time=start, value=self.fk_value)
            
            # Step 4: Delete keys on IK controls (optional - keeps them by default)
            # Uncomment the following lines if you want to clean up IK keys after switching
            # ik_handle = self.ik_controls[side]['ik_handle']
            # pole_vector = self.ik_controls[side]['pole_vector']
            # cmds.cutKey(ik_handle, clear=True, time=(start, end))
            # cmds.cutKey(pole_vector, clear=True, time=(start, end))
            
            print(f"Successfully switched IK to FK for {side} side")
            cmds.confirmDialog(title="Success", message=f"IK to FK switch complete for {side} side!", button="OK")
            
        except Exception as e:
            cmds.error(f"Error during IK to FK switch: {e}")
        
        finally:
            # Clean up temp locators
            for loc in temp_locators:
                if cmds.objExists(loc):
                    cmds.delete(loc)
            
            # Restore current time
            cmds.currentTime(current_time)
    
    def switch_fk_to_ik(self, side):
        """
        Switch from FK to IK by baking FK animation to IK controls.
        
        Args:
            side (str): 'L' or 'R' for left or right leg
        """
        if side not in ['L', 'R']:
            cmds.error("Invalid side. Must be 'L' or 'R'")
            return
        
        # Get controls and joints with namespace
        ik_handle = self.get_namespaced_name(self.ik_controls[side]['ik_handle'])
        pole_vector = self.get_namespaced_name(self.ik_controls[side]['pole_vector'])
        switch_attr = self.get_namespaced_name(self.ik_controls[side]['switch_attr'])
        joints = [self.get_namespaced_name(jnt) for jnt in self.joints[side]]
        
        # Check if controls exist
        if not cmds.objExists(ik_handle):
            cmds.warning(f"IK handle not found: {ik_handle}")
            return
        
        if not cmds.objExists(pole_vector):
            cmds.warning(f"Pole vector not found: {pole_vector}")
            return
        
        missing_joints = [jnt for jnt in joints if not cmds.objExists(jnt)]
        if missing_joints:
            cmds.warning(f"Missing joints: {missing_joints}")
            return
        
        # Get time range
        start, end = self.get_time_range()
        
        print(f"Switching FK to IK for {side} side from frame {start} to {end}")
        
        # Store current time
        current_time = cmds.currentTime(query=True)
        
        try:
            # Step 1: Set switch to FK mode first
            cmds.setAttr(switch_attr, self.fk_value)
            
            # Step 2: Bake IK controls to match FK animation
            for frame in range(int(start), int(end) + 1):
                cmds.currentTime(frame)
                
                # Match IK handle to ankle joint
                ankle_joint = joints[3]  # Ankle is the 4th joint
                knee_joint = joints[1]   # Knee is the 2nd joint
                
                if cmds.objExists(ankle_joint):
                    # Get ankle world position
                    ankle_pos = cmds.xform(ankle_joint, query=True, worldSpace=True, translation=True)
                    
                    # Set IK handle position
                    cmds.xform(ik_handle, worldSpace=True, translation=ankle_pos)
                    
                    # Match IK handle rotation to ankle joint using matrix for accurate orientation
                    # First, create a temporary constraint to match orientation
                    temp_constraint = cmds.orientConstraint(ankle_joint, ik_handle, maintainOffset=False)[0]
                    cmds.delete(temp_constraint)
                    
                    # Set keyframe on IK handle
                    cmds.setKeyframe(ik_handle, attribute=['translate', 'rotate'])
                
                # Match pole vector to knee position with offset
                if cmds.objExists(knee_joint):
                    knee_pos = cmds.xform(knee_joint, query=True, worldSpace=True, translation=True)
                    
                    # Calculate pole vector position (offset in front of knee)
                    # This is a simple offset - you may need to adjust for your rig
                    hip_joint = joints[0]
                    ankle_joint = joints[3]
                    
                    hip_pos = cmds.xform(hip_joint, query=True, worldSpace=True, translation=True)
                    ankle_pos = cmds.xform(ankle_joint, query=True, worldSpace=True, translation=True)
                    
                    # Calculate pole vector offset
                    import maya.api.OpenMaya as om
                    hip_vec = om.MVector(hip_pos)
                    knee_vec = om.MVector(knee_pos)
                    ankle_vec = om.MVector(ankle_pos)
                    
                    # Calculate the plane normal
                    leg_vec = ankle_vec - hip_vec
                    to_knee = knee_vec - hip_vec
                    
                    # Project knee onto leg line
                    proj_length = to_knee * leg_vec / leg_vec.length()
                    proj_point = hip_vec + (leg_vec.normal() * proj_length)
                    
                    # Pole vector is offset from knee perpendicular to leg
                    pole_dir = (knee_vec - proj_point).normal()
                    pole_offset = 5.0  # Adjust this distance as needed
                    pole_pos = knee_vec + (pole_dir * pole_offset)
                    
                    # Set pole vector position
                    cmds.xform(pole_vector, worldSpace=True, translation=[pole_pos.x, pole_pos.y, pole_pos.z])
                    
                    # Set keyframe on pole vector
                    cmds.setKeyframe(pole_vector, attribute='translate')
                
                # Reset IK control attributes to default
                for attr in self.ik_attrs:
                    attr_name = f"{ik_handle}.{attr}"
                    if cmds.objExists(attr_name):
                        cmds.setAttr(attr_name, 0)
                        cmds.setKeyframe(attr_name)
            
            # Step 3: Switch to IK mode
            cmds.setKeyframe(switch_attr, time=start, value=self.ik_value)
            
            # Step 4: Delete keys on FK controls (optional - keeps them by default)
            # Uncomment the following lines if you want to clean up FK keys after switching
            # for fk_ctrl in self.fk_controls[side]:
            #     cmds.cutKey(fk_ctrl, clear=True, time=(start, end))
            
            print(f"Successfully switched FK to IK for {side} side")
            cmds.confirmDialog(title="Success", message=f"FK to IK switch complete for {side} side!", button="OK")
            
        except Exception as e:
            cmds.error(f"Error during FK to IK switch: {e}")
        
        finally:
            # Restore current time
            cmds.currentTime(current_time)
    
    def create_ui(self):
        """Create the UI for IK/FK switching."""
        # Check if window exists
        if cmds.window("ikfkSwitcherWindow", exists=True):
            cmds.deleteUI("ikfkSwitcherWindow")
        
        # Create window
        window = cmds.window("ikfkSwitcherWindow", title="IK/FK Switcher", widthHeight=(350, 280))
        
        # Create layout
        main_layout = cmds.columnLayout(adjustableColumn=True, rowSpacing=10, columnOffset=("both", 10))
        
        # Title
        cmds.text(label="Dragon Rig IK/FK Switcher", align="center", font="boldLabelFont", height=30)
        cmds.separator(style="in", height=10)
        
        # Namespace selection
        cmds.text(label="Rig Namespace:", align="left", font="boldLabelFont")
        cmds.rowLayout(numberOfColumns=2, columnWidth2=(250, 80), adjustableColumn=1)
        
        # Get available namespaces
        namespaces = self.get_available_namespaces()
        
        # Try to detect namespace from selection
        detected_ns = self.detect_namespace_from_selection()
        default_ns = detected_ns if detected_ns else (namespaces[0] if namespaces else "(No Namespace)")
        
        # Create dropdown
        namespace_dropdown = cmds.optionMenu(label="", changeCommand=self.on_namespace_changed)
        for ns in namespaces:
            cmds.menuItem(label=ns)
        
        # Set default selection
        if default_ns in namespaces:
            cmds.optionMenu(namespace_dropdown, edit=True, value=default_ns)
        
        # Store dropdown reference
        self.namespace_dropdown = namespace_dropdown
        
        # Detect button
        cmds.button(
            label="Detect",
            command=lambda _: self.detect_and_set_namespace(),
            backgroundColor=[0.4, 0.6, 0.4],
            annotation="Detect namespace from selected control"
        )
        cmds.setParent('..')
        
        cmds.separator(style="in", height=10)
        
        # Instructions
        cmds.text(label="1. Select an IK or FK control (L or R)", align="left")
        cmds.text(label="2. Choose switch direction below", align="left")
        cmds.separator(style="in", height=10)
        
        # Time range display
        start, end = self.get_time_range()
        cmds.text(label=f"Timeline Range: {int(start)} to {int(end)}", align="center", font="smallPlainLabelFont")
        cmds.separator(style="in", height=10)
        
        # Switch buttons
        cmds.button(
            label="IK → FK (Bake to FK Controls)",
            command=lambda _: self.execute_switch("ik_to_fk"),
            height=40,
            backgroundColor=[0.3, 0.5, 0.8]
        )
        
        cmds.button(
            label="FK → IK (Bake to IK Controls)",
            command=lambda _: self.execute_switch("fk_to_ik"),
            height=40,
            backgroundColor=[0.5, 0.3, 0.8]
        )
        
        cmds.separator(style="in", height=10)
        
        # Close button
        cmds.button(
            label="Close",
            command=lambda _: cmds.deleteUI(window),
            height=30,
            backgroundColor=[0.8, 0.5, 0.5]
        )
        
        # Show window
        cmds.showWindow(window)
    
    def on_namespace_changed(self, selected_namespace):
        """
        Callback when namespace dropdown changes.
        
        Args:
            selected_namespace (str): The selected namespace from dropdown
        """
        if selected_namespace == "(No Namespace)":
            self.namespace = ""
        else:
            self.namespace = selected_namespace
        print(f"Namespace set to: '{self.namespace}'")
    
    def detect_and_set_namespace(self):
        """Detect namespace from selection and update the dropdown."""
        detected_ns = self.detect_namespace_from_selection()
        if detected_ns:
            self.namespace = detected_ns
            cmds.optionMenu(self.namespace_dropdown, edit=True, value=detected_ns)
            print(f"Detected and set namespace to: '{detected_ns}'")
        else:
            self.namespace = ""
            cmds.optionMenu(self.namespace_dropdown, edit=True, value="(No Namespace)")
            print("No namespace detected from selection")
        
        cmds.confirmDialog(
            title="Namespace Detection",
            message=f"Namespace: {self.namespace if self.namespace else '(None)'}",
            button=["OK"]
        )
    
    def execute_switch(self, direction):
        """
        Execute the IK/FK switch based on direction and selection.
        
        Args:
            direction (str): 'ik_to_fk' or 'fk_to_ik'
        """
        # Detect side from selection
        side = self.detect_side_from_selection()
        if not side:
            return
        
        # Confirm with user
        start, end = self.get_time_range()
        if direction == "ik_to_fk":
            result = cmds.confirmDialog(
                title="Confirm IK to FK Switch",
                message=f"Switch IK to FK for {side} side?\nFrames: {int(start)} to {int(end)}\n\nThis will bake animation to FK controls.",
                button=["Yes", "Cancel"],
                defaultButton="Yes",
                cancelButton="Cancel",
                dismissString="Cancel"
            )
            if result == "Yes":
                self.switch_ik_to_fk(side)
        
        elif direction == "fk_to_ik":
            result = cmds.confirmDialog(
                title="Confirm FK to IK Switch",
                message=f"Switch FK to IK for {side} side?\nFrames: {int(start)} to {int(end)}\n\nThis will bake animation to IK controls.",
                button=["Yes", "Cancel"],
                defaultButton="Yes",
                cancelButton="Cancel",
                dismissString="Cancel"
            )
            if result == "Yes":
                self.switch_fk_to_ik(side)


def launch_ik_fk_switcher():
    """Launch the IK/FK Switcher UI."""
    try:
        switcher = IKFKSwitcher()
        switcher.create_ui()
        print("IK/FK Switcher UI launched successfully!")
        return switcher
    except Exception as e:
        print(f"Error launching IK/FK Switcher: {e}")
        return None


# For direct execution in Maya
if __name__ == "__main__" or "maya" in globals():
    launch_ik_fk_switcher()

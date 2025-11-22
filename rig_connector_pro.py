"""
Professional Rig Connector for Maya
Blends multiple driver rigs to a target rig using constraints and custom attribute blending.

Features:
- Constraint-based blending for translate/rotate
- Direct connections for custom attributes
- Dynamic add/remove drivers with weight control
- Solo/Mute functionality per driver
- Control name mapping/retargeting
- Save/load configurations
- Smart baking
- Namespace support

Author: Generated with AI assistance
"""

import maya.cmds as cmds
import json
import os


class DriverRig:
    """Represents a single driver rig in the blend system."""
    
    def __init__(self, control_set, weight=0.5):
        self.control_set = control_set
        self.weight = weight
        self.muted = False
        self.controls = []
        self.namespace = ""
        
        # Extract controls from set
        if cmds.objExists(control_set):
            self.controls = sorted(cmds.sets(control_set, q=True) or [], key=str.lower)
            # Detect namespace from first control
            if self.controls and ':' in self.controls[0]:
                self.namespace = self.controls[0].split(':')[0]


class TargetRig:
    """Represents the target rig that receives blended animation."""
    
    def __init__(self, control_set):
        self.control_set = control_set
        self.controls = []
        self.namespace = ""
        
        if cmds.objExists(control_set):
            self.controls = sorted(cmds.sets(control_set, q=True) or [], key=str.lower)
            if self.controls and ':' in self.controls[0]:
                self.namespace = self.controls[0].split(':')[0]


class RigConnector:
    """Main class for managing rig blending operations."""
    
    def __init__(self):
        self.target = None
        self.drivers = []
        self.control_locator = None
        self.normalize_weights = True
        self.use_constraints = True
        self.control_mapping = {}  # {target_ctrl: [driver1_ctrl, driver2_ctrl, ...]}
        self.constraint_nodes = []
        self.blend_nodes = []
        self.blacklist_attrs = []  # Attributes to skip
        
    def set_target(self, control_set):
        """Set the target rig."""
        self.target = TargetRig(control_set)
        return len(self.target.controls) > 0
    
    def add_driver(self, control_set, weight=0.5):
        """Add a driver rig to the blend system."""
        driver = DriverRig(control_set, weight)
        if len(driver.controls) > 0:
            self.drivers.append(driver)
            return True
        return False
    
    def remove_driver(self, index):
        """Remove a driver rig by index."""
        if 0 <= index < len(self.drivers):
            del self.drivers[index]
            return True
        return False
    
    def auto_match_controls(self):
        """Automatically match controls by name (strips namespace)."""
        if not self.target or not self.drivers:
            return
        
        self.control_mapping = {}
        
        # Strip namespaces for comparison
        def strip_ns(name):
            return name.split(':')[-1].split('|')[-1]
        
        for target_ctrl in self.target.controls:
            target_name = strip_ns(target_ctrl)
            self.control_mapping[target_ctrl] = []
            
            # Try to find matching control in each driver
            for driver in self.drivers:
                matched = False
                for driver_ctrl in driver.controls:
                    if strip_ns(driver_ctrl) == target_name:
                        self.control_mapping[target_ctrl].append(driver_ctrl)
                        matched = True
                        break
                
                # If no match found, append None
                if not matched:
                    self.control_mapping[target_ctrl].append(None)
    
    def create_blend_controller(self):
        """Create the main blend control locator with weight attributes."""
        if cmds.objExists("rig_connector_CTRL"):
            cmds.delete("rig_connector_CTRL")
        
        self.control_locator = cmds.spaceLocator(name="rig_connector_CTRL")[0]
        
        # Lock and hide transform attributes
        for attr in ["tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz", "v"]:
            cmds.setAttr(f"{self.control_locator}.{attr}", lock=True, keyable=False, channelBox=False)
        
        # Add weight attributes for each driver
        for i, driver in enumerate(self.drivers):
            attr_name = f"driver_{i+1}_weight"
            cmds.addAttr(
                self.control_locator,
                longName=attr_name,
                attributeType="float",
                keyable=True,
                minValue=0.0,
                maxValue=1.0,
                defaultValue=driver.weight
            )
        
        # Add global controls
        cmds.addAttr(self.control_locator, longName="normalize_weights", attributeType="bool", keyable=True, defaultValue=self.normalize_weights)
        cmds.addAttr(self.control_locator, longName="global_enable", attributeType="bool", keyable=True, defaultValue=True)
        
        print(f"✓ Created blend controller: {self.control_locator}")
    
    def connect_rigs(self):
        """Main function to connect all rigs with blending."""
        if not self.target or not self.drivers:
            cmds.warning("Target or drivers not set")
            return False
        
        # Auto-match controls if mapping is empty
        if not self.control_mapping:
            self.auto_match_controls()
        
        # Create blend controller
        self.create_blend_controller()
        
        # Clear tracking lists
        self.constraint_nodes = []
        self.blend_nodes = []
        
        print(f"\n=== Connecting {len(self.drivers)} driver(s) to target ===")
        
        # Process each target control
        for target_ctrl in self.target.controls:
            driver_ctrls = self.control_mapping.get(target_ctrl, [])
            
            # Skip if no drivers mapped
            if not any(driver_ctrls):
                continue
            
            # Filter out None values
            valid_drivers = [ctrl for ctrl in driver_ctrls if ctrl is not None]
            
            if not valid_drivers:
                continue
            
            # Create constraints for translate/rotate if enabled
            if self.use_constraints:
                self._create_constraints_for_control(target_ctrl, valid_drivers)
            
            # Create blend nodes for custom attributes
            self._create_blend_connections_for_control(target_ctrl, valid_drivers)
        
        print(f"✓ Created {len(self.constraint_nodes)} constraints")
        print(f"✓ Created {len(self.blend_nodes)} blend nodes")
        return True
    
    def _create_constraints_for_control(self, target_ctrl, driver_ctrls):
        """Create point and orient constraints for a control."""
        try:
            # Point constraint for translation
            point_constraint = cmds.pointConstraint(
                driver_ctrls,
                target_ctrl,
                maintainOffset=True,
                name=f"pointConstraint_rig_connector_{target_ctrl.split(':')[-1].split('|')[-1]}"
            )[0]
            self.constraint_nodes.append(point_constraint)
            
            # Connect weight attributes
            for i, driver_ctrl in enumerate(driver_ctrls):
                driver_index = self._get_driver_index_for_control(driver_ctrl)
                if driver_index is not None:
                    weight_attr = f"driver_{driver_index+1}_weight"
                    target_attr = f"{point_constraint}.{driver_ctrl.split(':')[-1].split('|')[-1]}W{i}"
                    cmds.connectAttr(f"{self.control_locator}.{weight_attr}", target_attr, force=True)
            
            # Orient constraint for rotation
            orient_constraint = cmds.orientConstraint(
                driver_ctrls,
                target_ctrl,
                maintainOffset=True,
                name=f"orientConstraint_rig_connector_{target_ctrl.split(':')[-1].split('|')[-1]}"
            )[0]
            self.constraint_nodes.append(orient_constraint)
            
            # Connect weight attributes
            for i, driver_ctrl in enumerate(driver_ctrls):
                driver_index = self._get_driver_index_for_control(driver_ctrl)
                if driver_index is not None:
                    weight_attr = f"driver_{driver_index+1}_weight"
                    target_attr = f"{orient_constraint}.{driver_ctrl.split(':')[-1].split('|')[-1]}W{i}"
                    cmds.connectAttr(f"{self.control_locator}.{weight_attr}", target_attr, force=True)
        
        except Exception as e:
            print(f"Warning: Could not constrain {target_ctrl}: {e}")
    
    def _create_blend_connections_for_control(self, target_ctrl, driver_ctrls):
        """Create blend node connections for custom attributes."""
        try:
            # Get keyable attributes (excluding standard transform attrs)
            keyable_attrs = cmds.listAttr(target_ctrl, keyable=True, unlocked=True, visible=True) or []
            
            # Filter out translate, rotate, scale, visibility
            standard_attrs = ['tx', 'ty', 'tz', 'rx', 'ry', 'rz', 'sx', 'sy', 'sz', 'v']
            custom_attrs = [attr for attr in keyable_attrs if attr not in standard_attrs and attr not in self.blacklist_attrs]
            
            if not custom_attrs:
                return
            
            # Process each custom attribute
            for attr in custom_attrs:
                # Create multiply nodes for each driver
                multiply_nodes = []
                
                for i, driver_ctrl in enumerate(driver_ctrls):
                    # Check if driver has this attribute
                    if not cmds.attributeQuery(attr, node=driver_ctrl, exists=True):
                        continue
                    
                    # Create multiply node
                    mult_node = cmds.createNode('multiplyDivide', name=f"mult_rig_connector_{attr}")
                    multiply_nodes.append(mult_node)
                    self.blend_nodes.append(mult_node)
                    
                    # Connect driver attribute to multiply
                    cmds.connectAttr(f"{driver_ctrl}.{attr}", f"{mult_node}.input1X", force=True)
                    
                    # Connect weight to multiply
                    driver_index = self._get_driver_index_for_control(driver_ctrl)
                    if driver_index is not None:
                        weight_attr = f"driver_{driver_index+1}_weight"
                        cmds.connectAttr(f"{self.control_locator}.{weight_attr}", f"{mult_node}.input2X", force=True)
                
                # If we have multiply nodes, create plusMinusAverage to sum them
                if multiply_nodes:
                    plus_node = cmds.createNode('plusMinusAverage', name=f"plus_rig_connector_{attr}")
                    self.blend_nodes.append(plus_node)
                    
                    # Connect all multiply outputs to plus node
                    for i, mult_node in enumerate(multiply_nodes):
                        cmds.connectAttr(f"{mult_node}.outputX", f"{plus_node}.input1D[{i}]", force=True)
                    
                    # Connect plus output to target
                    cmds.connectAttr(f"{plus_node}.output1D", f"{target_ctrl}.{attr}", force=True)
        
        except Exception as e:
            print(f"Warning: Could not blend attributes for {target_ctrl}: {e}")
    
    def _get_driver_index_for_control(self, driver_ctrl):
        """Get the driver index that owns this control."""
        for i, driver in enumerate(self.drivers):
            if driver_ctrl in driver.controls:
                return i
        return None
    
    def solo_driver(self, index):
        """Solo a driver (set its weight to 1.0, others to 0.0)."""
        if not self.control_locator:
            return
        
        for i in range(len(self.drivers)):
            weight_attr = f"driver_{i+1}_weight"
            value = 1.0 if i == index else 0.0
            cmds.setAttr(f"{self.control_locator}.{weight_attr}", value)
    
    def mute_driver(self, index, mute=True):
        """Mute/unmute a driver."""
        if 0 <= index < len(self.drivers):
            self.drivers[index].muted = mute
            if self.control_locator:
                weight_attr = f"driver_{index+1}_weight"
                cmds.setAttr(f"{self.control_locator}.{weight_attr}", 0.0 if mute else self.drivers[index].weight)
    
    def cleanup(self):
        """Remove all blend connections and nodes."""
        nodes_to_delete = []
        
        # Collect all nodes to delete
        if self.control_locator and cmds.objExists(self.control_locator):
            nodes_to_delete.append(self.control_locator)
        
        nodes_to_delete.extend(self.constraint_nodes)
        nodes_to_delete.extend(self.blend_nodes)
        
        # Find any remaining rig_connector nodes
        all_nodes = cmds.ls()
        for node in all_nodes:
            if 'rig_connector' in node and cmds.objExists(node):
                nodes_to_delete.append(node)
        
        # Delete all collected nodes
        for node in set(nodes_to_delete):
            try:
                if cmds.objExists(node):
                    cmds.delete(node)
            except:
                pass
        
        print(f"✓ Cleaned up {len(set(nodes_to_delete))} nodes")
    
    def bake_and_cleanup(self, bake_set=None):
        """Bake animation to target rig and cleanup blend system."""
        if not self.target:
            cmds.warning("No target rig set")
            return
        
        # Determine which controls to bake
        if bake_set and cmds.objExists(bake_set):
            controls_to_bake = sorted(cmds.sets(bake_set, q=True) or [], key=str.lower)
        else:
            controls_to_bake = self.target.controls
        
        if not controls_to_bake:
            cmds.warning("No controls to bake")
            return
        
        print(f"\n=== Baking {len(controls_to_bake)} controls ===")
        
        # Select controls
        cmds.select(controls_to_bake, replace=True)
        
        # Get time range
        start_frame = cmds.playbackOptions(q=True, min=True)
        end_frame = cmds.playbackOptions(q=True, max=True)
        
        # Bake
        cmds.bakeResults(
            controls_to_bake,
            simulation=True,
            time=(start_frame, end_frame),
            sampleBy=1,
            oversamplingRate=1,
            disableImplicitControl=True,
            preserveOutsideKeys=True,
            sparseAnimCurveBake=False,
            removeBakedAttributeFromLayer=False,
            bakeOnOverrideLayer=False,
            minimizeRotation=True,
            controlPoints=False,
            shape=True
        )
        
        print(f"✓ Baked animation from frame {start_frame} to {end_frame}")
        
        # Cleanup
        self.cleanup()
        
        cmds.select(clear=True)
    
    def save_config(self, filepath):
        """Save the current setup to a JSON file."""
        config = {
            "target": self.target.control_set if self.target else None,
            "drivers": [driver.control_set for driver in self.drivers],
            "weights": [driver.weight for driver in self.drivers],
            "normalize_weights": self.normalize_weights,
            "use_constraints": self.use_constraints,
            "control_mapping": {k: v for k, v in self.control_mapping.items()},
            "blacklist_attrs": self.blacklist_attrs
        }
        
        with open(filepath, 'w') as f:
            json.dump(config, f, indent=4)
        
        print(f"✓ Saved configuration to: {filepath}")
    
    def load_config(self, filepath):
        """Load a setup from a JSON file."""
        if not os.path.exists(filepath):
            cmds.warning(f"Config file not found: {filepath}")
            return False
        
        with open(filepath, 'r') as f:
            config = json.load(f)
        
        # Clear current setup
        self.drivers = []
        
        # Load target
        if config.get("target"):
            self.set_target(config["target"])
        
        # Load drivers
        for i, driver_set in enumerate(config.get("drivers", [])):
            weight = config.get("weights", [])[i] if i < len(config.get("weights", [])) else 0.5
            self.add_driver(driver_set, weight)
        
        # Load settings
        self.normalize_weights = config.get("normalize_weights", True)
        self.use_constraints = config.get("use_constraints", True)
        self.control_mapping = config.get("control_mapping", {})
        self.blacklist_attrs = config.get("blacklist_attrs", [])
        
        print(f"✓ Loaded configuration from: {filepath}")
        return True


class RigConnectorUI:
    """UI for the Rig Connector tool."""
    
    def __init__(self):
        self.connector = RigConnector()
        self.window_name = "RigConnectorProUI"
        self.driver_ui_rows = []
        
    def create_ui(self):
        """Build the main UI window."""
        if cmds.window(self.window_name, exists=True):
            cmds.deleteUI(self.window_name, window=True)
        
        self.window = cmds.window(
            self.window_name,
            title="Rig Connector Pro",
            widthHeight=(800, 600),
            sizeable=True
        )
        
        main_layout = cmds.scrollLayout(childResizable=True)
        cmds.columnLayout(adjustableColumn=True, rowSpacing=5)
        
        # Header
        cmds.separator(height=10, style="none")
        cmds.text(label="RIG CONNECTOR PRO", font="boldLabelFont", height=30)
        cmds.separator(height=10, style="in")
        
        # Target Rig
        cmds.frameLayout(label="Target Rig", collapsable=True, collapse=False, marginHeight=5, marginWidth=5)
        cmds.columnLayout(adjustableColumn=True, rowSpacing=3)
        cmds.rowLayout(numberOfColumns=3, columnWidth3=(80, 600, 100))
        cmds.text(label="Rig:", align="right")
        self.target_field = cmds.textField()
        cmds.button(label="Load ⟲", command=self.load_target)
        cmds.setParent('..')
        cmds.setParent('..')
        cmds.setParent('..')
        
        # Drivers
        cmds.frameLayout(label="Driver Rigs", collapsable=True, collapse=False, marginHeight=5, marginWidth=5)
        self.drivers_column = cmds.columnLayout(adjustableColumn=True, rowSpacing=3)
        cmds.button(label="+ Add Driver", command=self.add_driver_row, backgroundColor=[0.3, 0.6, 0.3])
        cmds.setParent('..')
        cmds.setParent('..')
        
        # Options
        cmds.frameLayout(label="Options", collapsable=True, collapse=False, marginHeight=5, marginWidth=5)
        cmds.columnLayout(adjustableColumn=True, rowSpacing=3)
        self.normalize_cb = cmds.checkBox(label="Normalize Weights", value=True)
        self.constraints_cb = cmds.checkBox(label="Use Constraints (Translate/Rotate)", value=True)
        cmds.setParent('..')
        cmds.setParent('..')
        
        # Actions
        cmds.separator(height=10, style="in")
        cmds.rowLayout(numberOfColumns=2, columnWidth2=(395, 395))
        cmds.button(label="Connect Rigs", command=self.connect_rigs, height=40, backgroundColor=[0.3, 0.7, 0.5])
        cmds.button(label="Control Mapping", command=self.open_mapping_ui, height=40, backgroundColor=[0.5, 0.5, 0.7])
        cmds.setParent('..')
        
        cmds.rowLayout(numberOfColumns=2, columnWidth2=(395, 395))
        cmds.button(label="Bake & Cleanup", command=self.bake_and_cleanup, backgroundColor=[0.7, 0.5, 0.3])
        cmds.button(label="Cleanup Only", command=self.cleanup, backgroundColor=[0.7, 0.3, 0.3])
        cmds.setParent('..')
        
        cmds.separator(height=10, style="in")
        cmds.rowLayout(numberOfColumns=2, columnWidth2=(395, 395))
        cmds.button(label="Save Config", command=self.save_config)
        cmds.button(label="Load Config", command=self.load_config)
        cmds.setParent('..')
        
        cmds.separator(height=10, style="none")
        
        # Add initial driver rows
        self.add_driver_row()
        self.add_driver_row()
        
        # Auto-populate from current selection
        self.populate_from_selection()
        
        cmds.showWindow(self.window)
    
    def add_driver_row(self, *args):
        """Add a new driver rig row to the UI."""
        cmds.setParent(self.drivers_column)
        
        row_frame = cmds.frameLayout(
            label=f"Driver {len(self.driver_ui_rows) + 1}",
            collapsable=True,
            collapse=False,
            marginHeight=3,
            marginWidth=3
        )
        cmds.columnLayout(adjustableColumn=True, rowSpacing=2)
        
        # Control set field
        cmds.rowLayout(numberOfColumns=3, columnWidth3=(80, 600, 100))
        cmds.text(label="Rig:", align="right")
        set_field = cmds.textField()
        cmds.button(label="Load ⟲", command=lambda *args: self.load_driver_set(set_field))
        cmds.setParent('..')
        
        # Weight slider
        cmds.rowLayout(numberOfColumns=2, columnWidth2=(80, 700))
        cmds.text(label="Weight:", align="right")
        weight_slider = cmds.floatSliderGrp(
            field=True,
            minValue=0.0,
            maxValue=1.0,
            value=0.5,
            step=0.01,
            columnWidth=(1, 50)
        )
        cmds.setParent('..')
        
        # Solo/Mute buttons
        cmds.rowLayout(numberOfColumns=4, columnWidth4=(80, 150, 150, 100))
        cmds.text(label="")
        index = len(self.driver_ui_rows)
        solo_btn = cmds.button(label="Solo", command=lambda *args: self.solo_driver(index))
        mute_btn = cmds.button(label="Mute", command=lambda *args: self.mute_driver(index))
        remove_btn = cmds.button(label="Remove", command=lambda *args: self.remove_driver_row(row_frame, index), backgroundColor=[0.7, 0.3, 0.3])
        cmds.setParent('..')
        
        cmds.setParent('..')
        cmds.setParent('..')
        
        self.driver_ui_rows.append({
            'frame': row_frame,
            'set_field': set_field,
            'weight_slider': weight_slider,
            'solo_btn': solo_btn,
            'mute_btn': mute_btn
        })
    
    def remove_driver_row(self, frame, index):
        """Remove a driver row from the UI."""
        if cmds.frameLayout(frame, exists=True):
            cmds.deleteUI(frame)
        if 0 <= index < len(self.driver_ui_rows):
            self.driver_ui_rows.pop(index)
    
    def load_target(self, *args):
        """Load selected control sets: first as target, rest as drivers."""
        selection = cmds.ls(orderedSelection=True)
        if not selection:
            cmds.warning("Nothing selected")
            return
        
        # Process first selection as target
        first_item = selection[0]
        
        # Check if it's already an objectSet
        if cmds.objectType(first_item) == 'objectSet':
            target_set = first_item
        else:
            # Try to find ControlSet
            target_set = self._find_control_set(first_item)
        
        if target_set:
            cmds.textField(self.target_field, edit=True, text=target_set)
        else:
            cmds.warning(f"Could not find ControlSet for target: {first_item}")
            return
        
        # Process remaining selections as drivers
        if len(selection) > 1:
            # Ensure we have enough driver rows
            while len(self.driver_ui_rows) < len(selection) - 1:
                self.add_driver_row()
            
            # Fill driver fields
            for i, item in enumerate(selection[1:]):
                if i < len(self.driver_ui_rows):
                    if cmds.objectType(item) == 'objectSet':
                        driver_set = item
                    else:
                        driver_set = self._find_control_set(item)
                    
                    if driver_set:
                        cmds.textField(self.driver_ui_rows[i]['set_field'], edit=True, text=driver_set)
                    else:
                        cmds.warning(f"Could not find ControlSet for driver: {item}")
    
    def load_driver_set(self, field):
        """Load selected control set as driver or find it from top node."""
        selection = cmds.ls(selection=True)
        if not selection:
            cmds.warning("Nothing selected")
            return
        
        # Check if selection is already an objectSet
        if cmds.objectType(selection[0]) == 'objectSet':
            cmds.textField(field, edit=True, text=selection[0])
            return
        
        # Try to find ControlSet under namespace:Sets
        control_set = self._find_control_set(selection[0])
        if control_set:
            cmds.textField(field, edit=True, text=control_set)
        else:
            cmds.warning(f"Could not find ControlSet for {selection[0]}")
    
    def connect_rigs(self, *args):
        """Execute rig connection."""
        # Get target
        target_set = cmds.textField(self.target_field, query=True, text=True)
        if not target_set:
            cmds.warning("No target rig set")
            return
        
        # Clear and set target
        self.connector = RigConnector()
        if not self.connector.set_target(target_set):
            cmds.warning("Target rig has no controls")
            return
        
        # Add drivers
        for row in self.driver_ui_rows:
            driver_set = cmds.textField(row['set_field'], query=True, text=True)
            if driver_set:
                weight = cmds.floatSliderGrp(row['weight_slider'], query=True, value=True)
                self.connector.add_driver(driver_set, weight)
        
        if not self.connector.drivers:
            cmds.warning("No driver rigs added")
            return
        
        # Set options
        self.connector.normalize_weights = cmds.checkBox(self.normalize_cb, query=True, value=True)
        self.connector.use_constraints = cmds.checkBox(self.constraints_cb, query=True, value=True)
        
        # Connect
        if self.connector.connect_rigs():
            cmds.confirmDialog(
                title="Success",
                message=f"Connected {len(self.connector.drivers)} driver rig(s) to target!\n\nBlend controller: {self.connector.control_locator}",
                button=["OK"]
            )
    
    def solo_driver(self, index):
        """Solo a driver rig."""
        self.connector.solo_driver(index)
    
    def mute_driver(self, index):
        """Toggle mute on a driver."""
        if 0 <= index < len(self.connector.drivers):
            current_mute = self.connector.drivers[index].muted
            self.connector.mute_driver(index, not current_mute)
    
    def bake_and_cleanup(self, *args):
        """Bake animation and cleanup."""
        self.connector.bake_and_cleanup()
        cmds.confirmDialog(title="Success", message="Baked and cleaned up!", button=["OK"])
    
    def cleanup(self, *args):
        """Cleanup only."""
        self.connector.cleanup()
        cmds.confirmDialog(title="Success", message="Cleaned up blend system!", button=["OK"])
    
    def save_config(self, *args):
        """Save configuration to file."""
        filepath = cmds.fileDialog2(
            fileMode=0,
            caption="Save Rig Connector Config",
            fileFilter="JSON Files (*.json)"
        )
        if filepath:
            self.connector.save_config(filepath[0])
    
    def load_config(self, *args):
        """Load configuration from file."""
        filepath = cmds.fileDialog2(
            fileMode=1,
            caption="Load Rig Connector Config",
            fileFilter="JSON Files (*.json)"
        )
        if filepath:
            if self.connector.load_config(filepath[0]):
                # Update UI with loaded data
                if self.connector.target:
                    cmds.textField(self.target_field, edit=True, text=self.connector.target.control_set)
    
    def populate_from_selection(self):
        """Populate fields from current selection when UI launches."""
        try:
            selection = cmds.ls(orderedSelection=True)
            if not selection:
                print("No selection when launching UI")
                return
            
            print(f"Auto-populating from selection: {selection}")
            
            # Process first selection as target
            first_item = selection[0]
            
            # Check if it's already an objectSet
            if cmds.objectType(first_item) == 'objectSet':
                target_set = first_item
            else:
                # Try to find ControlSet
                target_set = self._find_control_set(first_item)
            
            if target_set:
                print(f"Setting target: {target_set}")
                cmds.textField(self.target_field, edit=True, text=target_set)
            else:
                print(f"Could not find ControlSet for target: {first_item}")
            
            # Process remaining selections as drivers
            if len(selection) > 1:
                # Ensure we have enough driver rows
                while len(self.driver_ui_rows) < len(selection) - 1:
                    self.add_driver_row()
                
                # Fill driver fields
                for i, item in enumerate(selection[1:]):
                    if i < len(self.driver_ui_rows):
                        if cmds.objectType(item) == 'objectSet':
                            driver_set = item
                        else:
                            driver_set = self._find_control_set(item)
                        
                        if driver_set:
                            print(f"Setting driver {i+1}: {driver_set}")
                            cmds.textField(self.driver_ui_rows[i]['set_field'], edit=True, text=driver_set)
                        else:
                            print(f"Could not find ControlSet for driver: {item}")
        except Exception as e:
            print(f"Error in populate_from_selection: {e}")
            import traceback
            traceback.print_exc()
    
    def _find_control_set(self, top_node):
        """Find ControlSet under namespace:Sets for a given top node."""
        print(f"Searching for ControlSet from top node: {top_node}")
        
        # Get namespace from top node if it exists
        namespace = ""
        if ':' in top_node:
            namespace = top_node.split(':')[0]
            print(f"Detected namespace: {namespace}")
        
        # Try direct patterns first
        possible_sets = [
            f"{namespace}:ControlSet" if namespace else "ControlSet",
            f"{namespace}:controlSet" if namespace else "controlSet",
            f"{namespace}:Controls" if namespace else "Controls"
        ]
        
        for set_name in possible_sets:
            if cmds.objExists(set_name):
                print(f"Found direct match: {set_name}")
                return set_name
        
        # Look for ControlSet as member of Sets
        sets_node = f"{namespace}:Sets" if namespace else "Sets"
        if cmds.objExists(sets_node) and cmds.objectType(sets_node) == 'objectSet':
            print(f"Found Sets node: {sets_node}, checking members...")
            members = cmds.sets(sets_node, q=True) or []
            for member in members:
                if cmds.objectType(member) == 'objectSet' and 'ControlSet' in member:
                    print(f"Found ControlSet as member: {member}")
                    return member
        
        # Search all sets for namespace:ControlSet pattern
        all_sets = cmds.ls(type='objectSet')
        print(f"Searching {len(all_sets)} objectSets for ControlSet...")
        for s in all_sets:
            if namespace:
                if s.startswith(f"{namespace}:") and 'ControlSet' in s:
                    print(f"Found matching set: {s}")
                    return s
            else:
                if 'ControlSet' in s:
                    print(f"Found matching set: {s}")
                    return s
        
        print(f"Could not find ControlSet for namespace: {namespace}")
        return None
    
    def open_mapping_ui(self, *args):
        """Open the control mapping interface."""
        cmds.warning("Control mapping UI coming soon...")


def show_rig_connector():
    """Launch the Rig Connector Pro UI."""
    ui = RigConnectorUI()
    ui.create_ui()


# Launch UI
if __name__ == "__main__":
    show_rig_connector()
else:
    show_rig_connector()

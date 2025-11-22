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
        
        # Add separator
        cmds.addAttr(self.control_locator, longName="weights_separator", attributeType="enum", enumName="===WEIGHTS===", keyable=True)
        cmds.setAttr(f"{self.control_locator}.weights_separator", lock=True)
        
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
        
        # Add visibility separator
        cmds.addAttr(self.control_locator, longName="visibility_separator", attributeType="enum", enumName="===VISIBILITY===", keyable=True)
        cmds.setAttr(f"{self.control_locator}.visibility_separator", lock=True)
        
        # Add visibility toggle for target rig
        cmds.addAttr(self.control_locator, longName="target_visibility", attributeType="bool", keyable=True, defaultValue=True)
        
        # Add visibility toggles for each driver
        for i, driver in enumerate(self.drivers):
            attr_name = f"driver_{i+1}_visibility"
            cmds.addAttr(
                self.control_locator,
                longName=attr_name,
                attributeType="bool",
                keyable=True,
                defaultValue=True
            )
        
        # Add global controls separator
        cmds.addAttr(self.control_locator, longName="global_separator", attributeType="enum", enumName="===GLOBAL===", keyable=True)
        cmds.setAttr(f"{self.control_locator}.global_separator", lock=True)
        
        # Add global controls
        cmds.addAttr(self.control_locator, longName="normalize_weights", attributeType="bool", keyable=True, defaultValue=self.normalize_weights)
        cmds.addAttr(self.control_locator, longName="global_enable", attributeType="bool", keyable=True, defaultValue=True)
        
        # Store rig connection data as string attributes (for reloading)
        cmds.addAttr(self.control_locator, longName="target_rig_set", dataType="string")
        cmds.setAttr(f"{self.control_locator}.target_rig_set", self.target.control_set, type="string")
        
        for i, driver in enumerate(self.drivers):
            attr_name = f"driver_{i+1}_rig_set"
            cmds.addAttr(self.control_locator, longName=attr_name, dataType="string")
            cmds.setAttr(f"{self.control_locator}.{attr_name}", driver.control_set, type="string")
        
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
        
        # Connect visibility toggles to Geometry nodes
        self._connect_visibility_toggles()
        
        # Select target rig top node
        self._select_target_rig()
        
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
    
    def _connect_visibility_toggles(self):
        """Connect visibility attributes to Geometry nodes for each rig."""
        if not self.control_locator:
            return
        
        # Connect target rig visibility
        if self.target and self.target.namespace:
            target_geo = f"{self.target.namespace}:Geometry"
            if cmds.objExists(target_geo):
                try:
                    cmds.connectAttr(
                        f"{self.control_locator}.target_visibility",
                        f"{target_geo}.visibility",
                        force=True
                    )
                    print(f"✓ Connected target visibility: {target_geo}")
                except Exception as e:
                    print(f"Warning: Could not connect target visibility: {e}")
        
        # Connect driver rig visibilities
        for i, driver in enumerate(self.drivers):
            if driver.namespace:
                driver_geo = f"{driver.namespace}:Geometry"
                if cmds.objExists(driver_geo):
                    try:
                        cmds.connectAttr(
                            f"{self.control_locator}.driver_{i+1}_visibility",
                            f"{driver_geo}.visibility",
                            force=True
                        )
                        print(f"✓ Connected driver {i+1} visibility: {driver_geo}")
                    except Exception as e:
                        print(f"Warning: Could not connect driver {i+1} visibility: {e}")
    
    def _select_target_rig(self):
        """Select the target rig top node after connecting."""
        if not self.target or not self.target.namespace:
            return
        
        # Try to find and select the top node
        possible_top_nodes = [
            f"{self.target.namespace}:Main",
            f"{self.target.namespace}:Root",
            f"{self.target.namespace}:Global",
            f"{self.target.namespace}:Geometry"
        ]
        
        for node in possible_top_nodes:
            if cmds.objExists(node):
                cmds.select(node, replace=True)
                print(f"✓ Selected target rig: {node}")
                return
        
        # If no common top node found, just select the control locator
        cmds.select(self.control_locator, replace=True)
        print(f"✓ Selected blend controller: {self.control_locator}")
    
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
        print("\n=== Cleaning up rig connector ===")
        
        # First, disconnect all visibility connections to Geometry nodes
        if self.control_locator and cmds.objExists(self.control_locator):
            # Disconnect target visibility
            if self.target and self.target.namespace:
                target_geo = f"{self.target.namespace}:Geometry"
                if cmds.objExists(target_geo):
                    try:
                        connections = cmds.listConnections(f"{target_geo}.visibility", source=True, plugs=True) or []
                        for conn in connections:
                            if 'rig_connector_CTRL' in conn:
                                cmds.disconnectAttr(conn, f"{target_geo}.visibility")
                                # Restore visibility
                                cmds.setAttr(f"{target_geo}.visibility", True)
                                print(f"✓ Restored target visibility: {target_geo}")
                    except Exception as e:
                        print(f"Warning: {e}")
            
            # Disconnect driver visibilities
            for i, driver in enumerate(self.drivers):
                if driver.namespace:
                    driver_geo = f"{driver.namespace}:Geometry"
                    if cmds.objExists(driver_geo):
                        try:
                            connections = cmds.listConnections(f"{driver_geo}.visibility", source=True, plugs=True) or []
                            for conn in connections:
                                if 'rig_connector_CTRL' in conn:
                                    cmds.disconnectAttr(conn, f"{driver_geo}.visibility")
                                    # Restore visibility
                                    cmds.setAttr(f"{driver_geo}.visibility", True)
                                    print(f"✓ Restored driver {i+1} visibility: {driver_geo}")
                        except Exception as e:
                            print(f"Warning: {e}")
        
        # Disconnect and delete constraints - store transforms first to prevent jumping
        for constraint in self.constraint_nodes:
            try:
                if cmds.objExists(constraint):
                    # Get the constrained object
                    constrained = cmds.listConnections(constraint, type='transform', destination=True)
                    if constrained and len(constrained) > 0:
                        target = constrained[0]
                        
                        # Store current transform values
                        stored_values = {}
                        for attr in ['tx', 'ty', 'tz', 'rx', 'ry', 'rz']:
                            try:
                                if cmds.getAttr(f"{target}.{attr}", settable=True):
                                    stored_values[attr] = cmds.getAttr(f"{target}.{attr}")
                            except:
                                pass
                        
                        # Delete constraint
                        cmds.delete(constraint)
                        
                        # Restore transform values to prevent jumping
                        for attr, value in stored_values.items():
                            try:
                                if cmds.getAttr(f"{target}.{attr}", settable=True):
                                    cmds.setAttr(f"{target}.{attr}", value)
                            except:
                                pass
            except Exception as e:
                print(f"Warning cleaning constraint {constraint}: {e}")
        
        # Disconnect and delete blend nodes - but first unlock and reset target attributes
        for blend_node in self.blend_nodes:
            try:
                if cmds.objExists(blend_node):
                    # Get output connections
                    outputs = cmds.listConnections(blend_node, source=False, plugs=True, destination=True) or []
                    
                    # For each output, store the current value, disconnect, then restore
                    for output in outputs:
                        try:
                            # Get current value before disconnect
                            current_value = cmds.getAttr(output)
                            
                            # Find the input connection
                            input_plugs = cmds.listConnections(output, source=True, plugs=True, destination=False) or []
                            
                            # Disconnect
                            for input_plug in input_plugs:
                                if 'rig_connector' in input_plug:
                                    cmds.disconnectAttr(input_plug, output)
                            
                            # Set back to the value it had (this prevents it from jumping)
                            cmds.setAttr(output, current_value)
                        except Exception as e:
                            print(f"  Warning disconnecting {output}: {e}")
                    
                    # Now delete the node
                    cmds.delete(blend_node)
            except Exception as e:
                print(f"Warning cleaning blend node {blend_node}: {e}")
        
        # Delete control locator
        if self.control_locator and cmds.objExists(self.control_locator):
            try:
                cmds.delete(self.control_locator)
            except Exception as e:
                print(f"Warning deleting control locator: {e}")
        
        # Find and clean any remaining rig_connector nodes
        all_nodes = cmds.ls()
        remaining = []
        for node in all_nodes:
            if 'rig_connector' in node and cmds.objExists(node):
                try:
                    cmds.delete(node)
                    remaining.append(node)
                except:
                    pass
        
        if remaining:
            print(f"✓ Cleaned up {len(remaining)} remaining nodes")
        
        # Clear tracking lists
        self.constraint_nodes = []
        self.blend_nodes = []
        self.control_locator = None
        
        print("✓ Cleanup complete")
    
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
        
        # Check if rig_connector_CTRL exists and load from it
        if cmds.objExists("rig_connector_CTRL"):
            self.load_from_controller()
        else:
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
        # If connector doesn't have target, try to load from UI/controller
        if not self.connector.target:
            target_set = cmds.textField(self.target_field, query=True, text=True)
            if target_set and cmds.objExists(target_set):
                self.connector.set_target(target_set)
            else:
                cmds.warning("No target rig set. Please set a target rig first.")
                return
        
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
    
    def load_from_controller(self):
        """Load rig sets from existing rig_connector_CTRL."""
        try:
            ctrl = "rig_connector_CTRL"
            if not cmds.objExists(ctrl):
                return
            
            print("Loading from existing rig_connector_CTRL...")
            
            # Load target rig
            if cmds.attributeQuery("target_rig_set", node=ctrl, exists=True):
                target_set = cmds.getAttr(f"{ctrl}.target_rig_set")
                if target_set and cmds.objExists(target_set):
                    cmds.textField(self.target_field, edit=True, text=target_set)
                    print(f"Loaded target: {target_set}")
            
            # Load driver rigs
            driver_index = 1
            while True:
                attr_name = f"driver_{driver_index}_rig_set"
                if cmds.attributeQuery(attr_name, node=ctrl, exists=True):
                    driver_set = cmds.getAttr(f"{ctrl}.{attr_name}")
                    if driver_set and cmds.objExists(driver_set):
                        # Ensure we have enough driver rows
                        while len(self.driver_ui_rows) < driver_index:
                            self.add_driver_row()
                        
                        # Set the driver field
                        if driver_index - 1 < len(self.driver_ui_rows):
                            cmds.textField(self.driver_ui_rows[driver_index - 1]['set_field'], edit=True, text=driver_set)
                            
                            # Load weight value
                            weight_attr = f"driver_{driver_index}_weight"
                            if cmds.attributeQuery(weight_attr, node=ctrl, exists=True):
                                weight = cmds.getAttr(f"{ctrl}.{weight_attr}")
                                cmds.floatSliderGrp(self.driver_ui_rows[driver_index - 1]['weight_slider'], edit=True, value=weight)
                            
                            print(f"Loaded driver {driver_index}: {driver_set}")
                    driver_index += 1
                else:
                    break
            
            # Load options
            if cmds.attributeQuery("normalize_weights", node=ctrl, exists=True):
                normalize = cmds.getAttr(f"{ctrl}.normalize_weights")
                cmds.checkBox(self.normalize_cb, edit=True, value=normalize)
            
            print("✓ Loaded configuration from rig_connector_CTRL")
            
        except Exception as e:
            print(f"Error loading from controller: {e}")
            import traceback
            traceback.print_exc()
    
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
        # Get target and drivers from UI
        target_set = cmds.textField(self.target_field, query=True, text=True)
        if not target_set or not cmds.objExists(target_set):
            cmds.warning("Please set a target rig first")
            return
        
        # Collect driver sets
        driver_sets = []
        for row in self.driver_ui_rows:
            driver_set = cmds.textField(row['set_field'], query=True, text=True)
            if driver_set and cmds.objExists(driver_set):
                driver_sets.append(driver_set)
        
        if not driver_sets:
            cmds.warning("Please add at least one driver rig")
            return
        
        # Set up connector with current rigs
        self.connector.set_target(target_set)
        self.connector.drivers = []
        for driver_set in driver_sets:
            weight = 0.5
            self.connector.add_driver(driver_set, weight)
        
        # Auto-match controls if not already done
        if not self.connector.control_mapping:
            self.connector.auto_match_controls()
        
        # Open mapping UI
        mapping_ui = ControlMappingUI(self.connector)
        mapping_ui.create_ui()


class ControlMappingUI:
    """UI for manually remapping controls between rigs."""
    
    def __init__(self, connector):
        self.connector = connector
        self.window_name = "ControlMappingUI"
        self.mapping_rows = []
        
    def create_ui(self):
        """Build the control mapping window."""
        if cmds.window(self.window_name, exists=True):
            cmds.deleteUI(self.window_name, window=True)
        
        self.window = cmds.window(
            self.window_name,
            title="Control Mapping / Retargeting",
            widthHeight=(1000, 600),
            sizeable=True
        )
        
        main_layout = cmds.scrollLayout(childResizable=True)
        cmds.columnLayout(adjustableColumn=True, rowSpacing=5)
        
        # Header
        cmds.separator(height=10, style="none")
        cmds.text(label="CONTROL MAPPING", font="boldLabelFont", height=30)
        cmds.text(label="Map target controls to driver controls. Use 'MISSING' for controls that don't exist.", align="left")
        cmds.separator(height=10, style="in")
        
        # Search/Filter
        cmds.rowLayout(numberOfColumns=5, columnWidth5=(100, 400, 150, 150, 150))
        cmds.text(label="Search/Filter:", align="right")
        self.search_field = cmds.textField(changeCommand=self.filter_rows, annotation="Type to filter controls")
        cmds.button(label="Show All", command=self.show_all)
        cmds.button(label="Show Missing Only", command=self.show_missing_only, backgroundColor=[0.7, 0.5, 0.3])
        cmds.button(label="Add to Search", command=self.add_selection_to_search, backgroundColor=[0.4, 0.6, 0.7], annotation="Add selected control name to search field")
        cmds.setParent('..')
        cmds.separator(height=5, style="none")
        
        # Column headers
        num_drivers = len(self.connector.drivers)
        header_widths = [40, 250] + [200] * num_drivers + [80]
        cmds.rowLayout(numberOfColumns=len(header_widths), columnWidth=[(i+1, w) for i, w in enumerate(header_widths)])
        cmds.text(label="#", font="boldLabelFont")
        cmds.text(label="Target Control", font="boldLabelFont", align="left")
        for i in range(num_drivers):
            cmds.text(label=f"Driver {i+1}", font="boldLabelFont", align="left")
        cmds.text(label="Action", font="boldLabelFont")
        cmds.setParent('..')
        
        cmds.separator(height=5, style="in")
        
        # Scroll layout for mappings
        self.mapping_scroll = cmds.scrollLayout(childResizable=True, height=400)
        self.mapping_column = cmds.columnLayout(adjustableColumn=True, rowSpacing=2)
        
        # Build mapping rows
        self._build_mapping_rows()
        
        cmds.setParent('..')
        cmds.setParent('..')
        
        # Action buttons
        cmds.separator(height=10, style="in")
        cmds.rowLayout(numberOfColumns=4, columnWidth4=(245, 245, 245, 245))
        cmds.button(label="Auto-Match All", command=self.auto_match_all, backgroundColor=[0.3, 0.6, 0.5])
        cmds.button(label="Clear All", command=self.clear_all, backgroundColor=[0.6, 0.4, 0.3])
        cmds.button(label="Apply Mapping", command=self.apply_mapping, height=40, backgroundColor=[0.3, 0.7, 0.5])
        cmds.button(label="Close", command=self.close_window, backgroundColor=[0.5, 0.5, 0.5])
        cmds.setParent('..')
        
        cmds.separator(height=10, style="none")
        
        cmds.showWindow(self.window)
    
    def _build_mapping_rows(self):
        """Build a row for each target control."""
        cmds.setParent(self.mapping_column)
        
        self.mapping_rows = []
        num_drivers = len(self.connector.drivers)
        
        for idx, (target_ctrl, driver_ctrls) in enumerate(self.connector.control_mapping.items()):
            # Strip namespace for display
            target_display = target_ctrl.split(':')[-1].split('|')[-1]
            
            # Create row
            row_widths = [40, 250] + [200] * num_drivers + [80]
            row_layout = cmds.rowLayout(numberOfColumns=len(row_widths), columnWidth=[(i+1, w) for i, w in enumerate(row_widths)])
            
            # Index
            cmds.text(label=f"{idx+1}", align="center")
            
            # Target control (non-editable)
            cmds.textField(text=target_display, editable=False, backgroundColor=[0.2, 0.2, 0.2])
            
            # Driver control fields
            driver_fields = []
            for i, driver_ctrl in enumerate(driver_ctrls):
                if driver_ctrl and cmds.objExists(driver_ctrl):
                    driver_display = driver_ctrl.split(':')[-1].split('|')[-1]
                else:
                    driver_display = "MISSING"
                
                field = cmds.textField(text=driver_display, annotation=f"Driver {i+1} control for {target_display}")
                driver_fields.append(field)
            
            # Create row data first
            row_data = {
                'target_ctrl': target_ctrl,
                'target_display': target_display,
                'target_field': None,  # Not needed, it's read-only
                'driver_fields': driver_fields,
                'original_drivers': driver_ctrls,
                'row_layout': row_layout,
                'visible': True
            }
            
            # Replace with Selection button - use row_data directly
            cmds.button(label="Replace", command=lambda *args, r=row_data: self.replace_with_selection(r), backgroundColor=[0.4, 0.7, 0.5], annotation="Replace MISSING driver fields with current selection")
            
            cmds.setParent('..')
            
            # Add to list
            self.mapping_rows.append(row_data)
    
    def replace_with_selection(self, row):
        """Replace MISSING driver fields with currently selected control."""
        if not row:
            return
        
        selection = cmds.ls(selection=True)
        if not selection:
            cmds.warning("Nothing selected. Please select a control first.")
            return
        
        selected_ctrl = selection[0]
        ctrl_name = selected_ctrl.split(':')[-1].split('|')[-1]
        
        # Find which driver this control belongs to
        driver_index = None
        for i, driver in enumerate(self.connector.drivers):
            if selected_ctrl in driver.controls:
                driver_index = i
                break
        
        if driver_index is not None:
            # Replace the field for this driver
            if driver_index < len(row['driver_fields']):
                field = row['driver_fields'][driver_index]
                current_value = cmds.textField(field, query=True, text=True)
                
                cmds.textField(field, edit=True, text=ctrl_name)
                print(f"✓ Replaced '{current_value}' with '{ctrl_name}' in {row['target_display']} -> Driver {driver_index + 1}")
                
                cmds.inViewMessage(
                    amg=f"Replaced <hl>{current_value}</hl> with <hl>{ctrl_name}</hl>",
                    pos='topCenter',
                    fade=True,
                    fadeStayTime=2000
                )
        else:
            # Control not found in any driver - ask which driver field to replace
            cmds.warning(f"Selected control '{ctrl_name}' not found in any driver rig. It may not be a valid control.")
    
    def add_selection_to_search(self, *args):
        """Add selected control name to search field."""
        selection = cmds.ls(selection=True)
        if not selection:
            cmds.warning("Nothing selected")
            return
        
        selected_ctrl = selection[0]
        ctrl_name = selected_ctrl.split(':')[-1].split('|')[-1]
        
        # Set search field and trigger filter
        cmds.textField(self.search_field, edit=True, text=ctrl_name)
        self.filter_rows()
        
        print(f"✓ Added '{ctrl_name}' to search filter")
    
    def auto_match_all(self, *args):
        """Re-run auto matching."""
        self.connector.auto_match_controls()
        self._rebuild_rows()
        print("✓ Auto-matched all controls")
    
    def clear_all(self, *args):
        """Clear all driver mappings."""
        for target_ctrl in self.connector.control_mapping:
            self.connector.control_mapping[target_ctrl] = [None] * len(self.connector.drivers)
        self._rebuild_rows()
        print("✓ Cleared all mappings")
    
    def _rebuild_rows(self):
        """Rebuild the mapping rows."""
        # Delete old rows
        if cmds.columnLayout(self.mapping_column, exists=True):
            children = cmds.columnLayout(self.mapping_column, query=True, childArray=True) or []
            for child in children:
                cmds.deleteUI(child)
        
        # Rebuild
        self._build_mapping_rows()
    
    def apply_mapping(self, *args):
        """Apply the manual mappings and reconnect changed controls."""
        print("\n=== Applying control mapping ===")
        
        # Store old mapping for comparison
        old_mapping = dict(self.connector.control_mapping)
        
        # Read new mappings from UI
        for row in self.mapping_rows:
            target_ctrl = row['target_ctrl']
            
            # Read driver fields
            new_drivers = []
            for i, field in enumerate(row['driver_fields']):
                driver_display = cmds.textField(field, query=True, text=True).strip()
                
                if driver_display == "MISSING" or driver_display == "":
                    # Keep as None
                    new_drivers.append(None)
                else:
                    # Try to find the control in the driver rig
                    driver = self.connector.drivers[i]
                    found = None
                    
                    # Search in driver controls
                    for ctrl in driver.controls:
                        ctrl_name = ctrl.split(':')[-1].split('|')[-1]
                        if ctrl_name == driver_display:
                            found = ctrl
                            break
                    
                    if found:
                        new_drivers.append(found)
                    else:
                        # Try with namespace
                        full_name = f"{driver.namespace}:{driver_display}" if driver.namespace else driver_display
                        if cmds.objExists(full_name):
                            new_drivers.append(full_name)
                        else:
                            print(f"Warning: Could not find driver control '{driver_display}' in driver {i+1}")
                            new_drivers.append(None)
            
            # Update mapping
            self.connector.control_mapping[target_ctrl] = new_drivers
        
        # Check if connection already exists
        if not self.connector.control_locator:
            # Try to find existing controller
            if cmds.objExists("rig_connector_CTRL"):
                self.connector.control_locator = "rig_connector_CTRL"
                print("Found existing rig_connector_CTRL")
            else:
                print("✓ Applied control mapping")
                cmds.confirmDialog(title="Success", message="Control mapping applied!\n\nNow click 'Connect Rigs' to connect with the new mapping.", button=["OK"])
                return
        
        if not cmds.objExists(self.connector.control_locator):
            print("✓ Applied control mapping (no active connection)")
            cmds.confirmDialog(title="Success", message="Control mapping applied!\n\nNow click 'Connect Rigs' to connect with the new mapping.", button=["OK"])
            return
        
        # Reconnect changed controls
        print("\n=== Reconnecting changed controls ===")
        print(f"Comparing {len(self.connector.control_mapping)} controls")
        changes_made = 0
        
        for target_ctrl, new_drivers in self.connector.control_mapping.items():
            old_drivers = old_mapping.get(target_ctrl, [])
            
            # Check if mapping changed
            if old_drivers != new_drivers:
                changes_made += 1
                print(f"\nReconnecting: {target_ctrl.split(':')[-1]}")
                print(f"  Old: {[d.split(':')[-1] if d else 'None' for d in old_drivers]}")
                print(f"  New: {[d.split(':')[-1] if d else 'None' for d in new_drivers]}")
                
                # Remove old constraints for this control
                self._remove_constraints_for_control(target_ctrl)
                
                # Remove old blend connections for this control
                self._remove_blend_connections_for_control(target_ctrl)
                
                # Create new connections
                valid_drivers = [ctrl for ctrl in new_drivers if ctrl is not None]
                
                if valid_drivers:
                    # Create constraints for translate/rotate
                    if self.connector.use_constraints:
                        self.connector._create_constraints_for_control(target_ctrl, valid_drivers)
                    
                    # Create blend nodes for custom attributes
                    self.connector._create_blend_connections_for_control(target_ctrl, valid_drivers)
                    
                    print(f"✓ Reconnected {target_ctrl.split(':')[-1]} with {len(valid_drivers)} driver(s)")
        
        if changes_made > 0:
            print(f"\n✓ Applied mapping and reconnected {changes_made} control(s)")
            cmds.confirmDialog(title="Success", message=f"Control mapping applied and {changes_made} control(s) reconnected!", button=["OK"])
        else:
            print("✓ No changes detected")
            cmds.confirmDialog(title="Info", message="No mapping changes detected.", button=["OK"])
    
    def _remove_constraints_for_control(self, target_ctrl):
        """Remove constraints affecting a specific control."""
        # Get all constraints on the target control
        constraints = cmds.listConnections(target_ctrl, type='constraint') or []
        
        for constraint in constraints:
            if 'rig_connector' in constraint:
                try:
                    # Remove from tracking list
                    if constraint in self.connector.constraint_nodes:
                        self.connector.constraint_nodes.remove(constraint)
                    
                    # Delete constraint
                    if cmds.objExists(constraint):
                        cmds.delete(constraint)
                        print(f"  Removed constraint: {constraint}")
                except Exception as e:
                    print(f"  Warning: Could not remove constraint {constraint}: {e}")
    
    def _remove_blend_connections_for_control(self, target_ctrl):
        """Remove blend node connections for a specific control."""
        try:
            # Get keyable attributes
            keyable_attrs = cmds.listAttr(target_ctrl, keyable=True, unlocked=True, visible=True) or []
            
            # Filter to custom attributes
            standard_attrs = ['tx', 'ty', 'tz', 'rx', 'ry', 'rz', 'sx', 'sy', 'sz', 'v']
            custom_attrs = [attr for attr in keyable_attrs if attr not in standard_attrs]
            
            for attr in custom_attrs:
                # Get input connections to this attribute
                connections = cmds.listConnections(f"{target_ctrl}.{attr}", source=True, plugs=True, destination=False) or []
                
                for conn in connections:
                    node = conn.split('.')[0]
                    if 'rig_connector' in node:
                        # Disconnect
                        cmds.disconnectAttr(conn, f"{target_ctrl}.{attr}")
                        print(f"  Disconnected: {conn} -> {target_ctrl}.{attr}")
                        
                        # Delete the node if it exists
                        if cmds.objExists(node):
                            # Remove from tracking
                            if node in self.connector.blend_nodes:
                                self.connector.blend_nodes.remove(node)
                            
                            cmds.delete(node)
        
        except Exception as e:
            print(f"  Warning: Error removing blend connections for {target_ctrl}: {e}")
    
    def filter_rows(self, *args):
        """Filter rows based on search text - searches target and all driver controls."""
        search_text = cmds.textField(self.search_field, query=True, text=True).lower().strip()
        
        for row in self.mapping_rows:
            if not search_text:
                # Show all if search is empty
                self._show_row(row)
            else:
                # Check if search text matches target control
                target_match = search_text in row['target_display'].lower()
                
                # Check if search text matches any driver control
                driver_match = False
                for field in row['driver_fields']:
                    driver_text = cmds.textField(field, query=True, text=True).lower()
                    if search_text in driver_text and driver_text != "missing":
                        driver_match = True
                        break
                
                # Check actual driver control names in the rig
                actual_driver_match = False
                for driver_ctrl in row['original_drivers']:
                    if driver_ctrl:
                        driver_display = driver_ctrl.split(':')[-1].split('|')[-1].lower()
                        if search_text in driver_display:
                            actual_driver_match = True
                            break
                
                if target_match or driver_match or actual_driver_match:
                    self._show_row(row)
                else:
                    self._hide_row(row)
    
    def show_all(self, *args):
        """Show all rows."""
        cmds.textField(self.search_field, edit=True, text="")
        for row in self.mapping_rows:
            self._show_row(row)
    
    def show_missing_only(self, *args):
        """Show only rows with missing driver controls."""
        cmds.textField(self.search_field, edit=True, text="")
        
        for row in self.mapping_rows:
            has_missing = False
            for field in row['driver_fields']:
                driver_text = cmds.textField(field, query=True, text=True)
                if driver_text == "MISSING" or not driver_text.strip():
                    has_missing = True
                    break
            
            if has_missing:
                self._show_row(row)
            else:
                self._hide_row(row)
    
    def _show_row(self, row):
        """Show a mapping row."""
        if cmds.rowLayout(row['row_layout'], exists=True):
            cmds.rowLayout(row['row_layout'], edit=True, visible=True, manage=True)
            row['visible'] = True
    
    def _hide_row(self, row):
        """Hide a mapping row."""
        if cmds.rowLayout(row['row_layout'], exists=True):
            cmds.rowLayout(row['row_layout'], edit=True, visible=False, manage=False)
            row['visible'] = False
    
    def add_selection_to_field(self, *args):
        """Add selected control to the currently focused driver field."""
        selection = cmds.ls(selection=True)
        if not selection:
            cmds.warning("Nothing selected. Please select a control first.")
            return
        
        selected_ctrl = selection[0]
        ctrl_name = selected_ctrl.split(':')[-1].split('|')[-1]
        
        # Try to find which field has focus by checking all text fields
        focused_field = None
        focused_row = None
        focused_driver_index = None
        
        for row in self.mapping_rows:
            for i, field in enumerate(row['driver_fields']):
                if cmds.textField(field, exists=True):
                    # Check if this field was recently edited or could accept the control
                    focused_field = field
                    focused_row = row
                    focused_driver_index = i
                    # Don't break - we want the last one that exists
        
        # If we found a field, use the most recently created one or ask user
        if focused_field:
            # For now, let's search for the control name in driver lists
            # and auto-assign to the matching driver if possible
            assigned = False
            
            for row_idx, row in enumerate(self.mapping_rows):
                target_name = row['target_display']
                
                # Check if selected control matches or is similar to target
                for driver_idx, driver in enumerate(self.connector.drivers):
                    if selected_ctrl in driver.controls or ctrl_name in [c.split(':')[-1] for c in driver.controls]:
                        # Found it in this driver's control list
                        if driver_idx < len(row['driver_fields']):
                            cmds.textField(row['driver_fields'][driver_idx], edit=True, text=ctrl_name)
                            print(f"✓ Assigned '{ctrl_name}' to {target_name} -> Driver {driver_idx + 1}")
                            assigned = True
                            
                            # If this matches the target name, we're done
                            if ctrl_name.lower() == target_name.lower():
                                cmds.confirmDialog(
                                    title="Control Added",
                                    message=f"Added '{ctrl_name}' to matching target control '{target_name}'",
                                    button=["OK"]
                                )
                                return
            
            if assigned:
                cmds.confirmDialog(
                    title="Control Added",
                    message=f"Added '{ctrl_name}' to driver field(s)",
                    button=["OK"]
                )
            else:
                # Control not found in any driver, offer to add manually
                result = cmds.promptDialog(
                    title="Add Control",
                    message=f"Which row should '{ctrl_name}' be added to?\n\nEnter row number (1-{len(self.mapping_rows)}):",
                    button=["OK", "Cancel"],
                    defaultButton="OK",
                    cancelButton="Cancel",
                    dismissString="Cancel"
                )
                
                if result == "OK":
                    row_num_text = cmds.promptDialog(query=True, text=True)
                    try:
                        row_num = int(row_num_text) - 1
                        if 0 <= row_num < len(self.mapping_rows):
                            row = self.mapping_rows[row_num]
                            
                            # Ask which driver
                            driver_result = cmds.promptDialog(
                                title="Select Driver",
                                message=f"Which driver field? (1-{len(row['driver_fields'])}):",
                                button=["OK", "Cancel"],
                                defaultButton="OK",
                                cancelButton="Cancel",
                                dismissString="Cancel"
                            )
                            
                            if driver_result == "OK":
                                driver_num_text = cmds.promptDialog(query=True, text=True)
                                driver_num = int(driver_num_text) - 1
                                if 0 <= driver_num < len(row['driver_fields']):
                                    cmds.textField(row['driver_fields'][driver_num], edit=True, text=ctrl_name)
                                    print(f"✓ Manually assigned '{ctrl_name}' to row {row_num + 1}, driver {driver_num + 1}")
                        else:
                            cmds.warning(f"Row number out of range: {row_num + 1}")
                    except ValueError:
                        cmds.warning("Invalid row number")
        else:
            cmds.warning("No driver fields found")
    
    def close_window(self, *args):
        """Close the mapping window."""
        if cmds.window(self.window_name, exists=True):
            cmds.deleteUI(self.window_name, window=True)


def show_rig_connector():
    """Launch the Rig Connector Pro UI."""
    ui = RigConnectorUI()
    ui.create_ui()


# Launch UI
if __name__ == "__main__":
    show_rig_connector()
else:
    show_rig_connector()

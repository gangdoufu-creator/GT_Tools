import maya.cmds as cmds
import maya.mel as mel
import re

class CycleMakerUI:
    """
    Maya Animation Cycle Maker Tool
    
    A comprehensive tool for creating seamless animation cycles with automatic left/right 
    mirroring, X-axis inversion detection, spine processing, and infinity management.
    
    MAIN FEATURES:
    - Automatic rig prefix detection
    - Left/Right control pairing and mirroring  
    - Intelligent X-axis inversion detection for different rig conventions
    - Cycle infinity application with multiple fallback strategies
    - Spine/centerline inversion for rotateY/Z channels
    - Time and value offset support for layered animation
    
    FILE ORGANIZATION:
    ==================
    SECTION 1: INITIALIZATION & SETUP (lines ~30-150)
        - __init__() - Initialize variables and UI
        - setup_ui() - Create the main interface
        
    SECTION 2: CONTROL MANAGEMENT (lines ~150-250) 
        - add_selected_controls() - Add controls to left/right lists
        - remove_selected_controls() - Remove selected controls
        - load_biped_defaults() / load_quad_defaults() - Preset control lists
        
    SECTION 3: UTILITY FUNCTIONS (lines ~250-350)
        - String manipulation (is_left, is_right, get_other_side)
        - Rig prefix extraction
        - Animation curve helpers
        
    SECTION 4: X-AXIS INVERSION DETECTION (lines ~350-550)
        - detect_x_inversion_needed() - Main detection logic
        - _analyze_translate_x_patterns() - TranslateX movement analysis  
        - _analyze_rotation_patterns() - Rotation fallback analysis
        - analyze_all_control_pairs() - Batch analysis
        
    SECTION 5: INFINITY MANAGEMENT (lines ~550-750)
        - _apply_cycle_infinity_mel() - MEL-based infinity application
        - _apply_cycle_infinity_advanced() - Multi-strategy fallback system
        - apply_cycle_infinity_for_selection() - Manual infinity application
        
    SECTION 6: ANIMATION CORE FUNCTIONS (lines ~750-950)
        - copy_keys() - Main key copying with auto-inversion
        - get_key_options() - Paste options configuration
        - _keyed_attributes() - Find animated attributes
        
    SECTION 7: COPY OPERATIONS (lines ~950-1050)
        - copy_left_to_right() / copy_right_to_left() - Directional copying
        
    SECTION 8: SPINE/CENTERLINE PROCESSING (lines ~1050-1150)
        - invert_spine_channels() - Manual spine inversion
        - _should_invert_for_spine() - Spine keyword matching
        - _rebuild_second_half_antiphase() - Antiphase animation creation
        
    SECTION 9: UI CALLBACKS & HELPERS (lines ~1150-end)
        - Event handlers for buttons and checkboxes
        - Analysis result displays

    """
    def __init__(self):
        self.window = "cycleMakerWin"
        self.left_controls = []
        self.right_controls = []
        # Per-control inversion settings: [{tx: bool, ty: bool, tz: bool, rx: bool, ry: bool, rz: bool}, ...]
        self.control_inversions = []

        self.left_list_field = None  # Keep for backward compatibility
        self.right_list_field = None  # Keep for backward compatibility
        self.control_pairs_scroll = None
        self.prefix_field = None
        # Spine/centerline inversion UI handles and defaults
        self.spine_controls_list = None
        self.wing_controls_list = None  # Keep for backward compatibility
        self.wing_pairs_scroll = None
        # Wing control pairs data (similar to main control pairs)
        self.wing_left_controls = []
        self.wing_right_controls = []
        self.wing_control_inversions = []

        self.spine_keywords_default = [
            'spine', 'chest', 'torso', 'back', 'hip', 'pelvis', 'waist', 'abdomen',
            'cog', 'root', 'body', 'head', 'tail'
        ]
        self.spine_invert_y_default = True
        self.spine_invert_z_default = True
        # Auto-detection system for X-axis inversion
        self.auto_detect_x_inversion = True
        
        # Spine control data structures (like left/right controls)
        self.spine_controls = []  # List of spine control names
        self.spine_control_inversions = []  # Channel inversions for each spine control
        
        # Copy with Offset tab data structures
        self.copy_offset_objects = []  # List of selected objects in order
        self.copy_offset_time_offsets = []  # Time offset for each object
        self.copy_offset_value_offsets = []  # Value offset for each object  
        self.copy_offset_channel_settings = []  # Channel settings for each object
        self.copy_offset_scroll = None  # Scroll layout for object list
        
        # Legacy fields for backward compatibility (if needed)
        self.time_offset_copy_field = None
        self.value_offset_copy_field = None
        
        # Settings/Preferences
        self.forward_direction = 'Z'  # Default forward direction (X, Y, or Z)
        self.forward_rotation_axis = 'X'  # Default spine rotation axis (X, Y, or Z)
        self.fit_curve_default = True  # Default state for "Fit Curve to Timeline"
        self.auto_detect_inversions = True  # Default state for auto-detecting mirrored axis alignments
        
        self.setup_ui()

    # =========================================================================
    # SECTION 1: INITIALIZATION & UI SETUP
    # =========================================================================

    def setup_ui(self):
        if cmds.window(self.window, exists=True):
            cmds.deleteUI(self.window)
        self.window = cmds.window(self.window, title="Cycle Maker Tool", widthHeight=(520, 450), menuBar=True)
        
        # Create menu bar
        cmds.menu(label='File')
        cmds.menuItem(label='Settings...', command=self.open_settings_dialog)
        cmds.menuItem(divider=True)
        cmds.menuItem(label='Save Presets', command=self.save_presets)
        cmds.menuItem(label='Load Presets', command=self.load_presets)
        
        # Create main tab layout
        main_tabs = cmds.tabLayout(innerMarginWidth=5, innerMarginHeight=5)
        
        # TAB 1: Cycle Maker (original functionality)
        tab1 = cmds.columnLayout(adjustableColumn=True, parent=main_tabs)
        self.setup_cycle_maker_tab()
        
        # TAB 2: Copy with Offset
        tab2 = cmds.columnLayout(adjustableColumn=True, parent=main_tabs)
        self.setup_copy_offset_tab()
        
        # TAB 3: IK/FK Switcher
        tab3 = cmds.columnLayout(adjustableColumn=True, parent=main_tabs)
        self.setup_ik_fk_switcher_tab()
        
        # Set tab labels
        cmds.tabLayout(main_tabs, edit=True, tabLabel=((tab1, 'Cycle Maker'), (tab2, 'Copy with Offset'), (tab3, 'IK/FK Switcher')))
        
        cmds.showWindow(self.window)
    
    def setup_cycle_maker_tab(self):
        """Setup the original Cycle Maker functionality tab."""
        # Hidden prefix field (functionality preserved, UI hidden)
        self.prefix_field = cmds.textField(text="tigerA_rigMain_01_:", visible=False)
        
        # Advanced control pair management with per-pair inversion settings
        cmds.frameLayout(label="Left/Right Control Pairs with Inversion Settings", collapsable=False, 
                        marginHeight=8, marginWidth=8, borderVisible=True,
                        backgroundColor=(0.45, 0.42, 0.38))  # Muted orange for main sections
        cmds.columnLayout(adjustableColumn=True, rowSpacing=3)
        
        # Headers row - matching the individual control pair layout structure
        cmds.rowLayout(numberOfColumns=2, columnWidth2=(320, 120), height=22)
        # Controls header section
        cmds.rowLayout(numberOfColumns=3, columnWidth3=(135, 50, 135))
        cmds.text(label="", align="center", height=20)
        cmds.text(label="", width=50)  # Empty space above swap button
        cmds.text(label="", align="center", height=20)
        cmds.setParent('..')  # controls header
        # Channel headers section - matching individual row structure
        cmds.rowLayout(numberOfColumns=6, columnWidth6=(3, 20, 20, 20, 20, 60))
        cmds.text(label="", width=3)  # 3 pixel spacer
        cmds.text(label="TX", align="center", font="smallPlainLabelFont", height=20,
                 backgroundColor=(0.4, 0.4, 0.4))
        cmds.text(label="TY", align="center", font="smallPlainLabelFont", height=20,
                 backgroundColor=(0.4, 0.4, 0.4))
        cmds.text(label="TZ", align="center", font="smallPlainLabelFont", height=20,
                 backgroundColor=(0.4, 0.4, 0.4))
        cmds.text(label="RX", align="center", font="smallPlainLabelFont", height=20,
                 backgroundColor=(0.4, 0.4, 0.4))
        cmds.rowLayout(numberOfColumns=4, columnWidth4=(1, 20, 20, 20))
        cmds.text(label="", width=1)  # 1 pixel spacer
        cmds.text(label="RY", align="center", font="smallPlainLabelFont", height=20,
                 backgroundColor=(0.4, 0.4, 0.4))
        cmds.text(label="RZ", align="center", font="smallPlainLabelFont", height=20,
                 backgroundColor=(0.4, 0.4, 0.4))
        cmds.text(label="", width=20)  # Space above remove button
        cmds.setParent('..')  # RY RZ space layout
        cmds.setParent('..')  # channel headers
        cmds.setParent('..')  # headers row
        
        # Bulk editing controls - using EXACT same structure as individual rows
        cmds.rowLayout(numberOfColumns=2, columnWidth2=(320, 120), height=22)
        # Controls section - same structure as individual pairs
        cmds.rowLayout(numberOfColumns=3, columnWidth3=(138, 50, 135))
        cmds.text(label="", align="center", height=20)
        cmds.button(label="→", width=50, height=20,
                   backgroundColor=(0.6, 0.4, 0.6),
                   annotation="Swap all left/right control pairs",
                   command=self._swap_all_control_pairs)
        cmds.text(label="", align="center", height=20)
        cmds.setParent('..')  # bulk controls section
        # Checkboxes section - matching individual row structure exactly
        cmds.rowLayout(numberOfColumns=6, columnWidth6=(3, 20, 20, 20, 20, 60))
        cmds.text(label="", width=3)  # 3 pixel spacer
        self.bulk_tx_chk = cmds.checkBox(label='', value=False, height=20,
                                        changeCommand=lambda x: self._set_all_inversions('tx', x))
        self.bulk_ty_chk = cmds.checkBox(label='', value=False, height=20,
                                        changeCommand=lambda x: self._set_all_inversions('ty', x))
        self.bulk_tz_chk = cmds.checkBox(label='', value=False, height=20,
                                        changeCommand=lambda x: self._set_all_inversions('tz', x))
        self.bulk_rx_chk = cmds.checkBox(label='', value=False, height=20,
                                        changeCommand=lambda x: self._set_all_inversions('rx', x))
        cmds.rowLayout(numberOfColumns=4, columnWidth4=(1, 20, 20, 20))
        cmds.text(label="", width=1)  # 1 pixel spacer
        self.bulk_ry_chk = cmds.checkBox(label='', value=False, height=20,
                                        changeCommand=lambda x: self._set_all_inversions('ry', x))
        self.bulk_rz_chk = cmds.checkBox(label='', value=False, height=20,
                                        changeCommand=lambda x: self._set_all_inversions('rz', x))
        cmds.button(label="✕", width=20, height=20,
                   command=self.clear_all_control_pairs,
                   backgroundColor=(0.7, 0.5, 0.5),
                   annotation="Clear all control pairs")
        cmds.setParent('..')  # RY RZ X layout
        cmds.setParent('..')  # checkboxes section  
        cmds.setParent('..')  # bulk controls row
        
        # Scrollable area for control pairs with improved styling
        self.control_pairs_scroll = cmds.scrollLayout(height=160, childResizable=True, 
                                                     backgroundColor=(0.85, 0.85, 0.85))
        cmds.columnLayout(adjustableColumn=True, rowSpacing=3)
        # Control pairs will be added here dynamically
        cmds.setParent('..')  # columnLayout
        cmds.setParent('..')  # scrollLayout
        
        cmds.setParent('..')  # columnLayout
        cmds.setParent('..')  # frameLayout
        
        cmds.separator(height=12, style="in")
        # Add Selected and Copy buttons on one line
        cmds.rowLayout(numberOfColumns=2, columnWidth2=(200, 200), adjustableColumn=1,
                      columnAttach=[(1, 'both', 2), (2, 'both', 2)])
        cmds.button(label="Add Selected", command=self.add_selected_controls, height=28,
                   backgroundColor=(0.42, 0.48, 0.42))  # Muted green for add actions
        cmds.button(label="Copy Across", command=self.copy_with_direction, height=28,
                   backgroundColor=(0.42, 0.48, 0.42))  # Muted green for primary action
        cmds.setParent('..')  # rowLayout
        
        cmds.separator(height=15, style="in")
        
        # Spine/centerline inversion options
        cmds.frameLayout(label="Spine/Centerline Inversion", collapsable=True, collapse=False, 
                        marginHeight=8, marginWidth=8, borderVisible=True,
                        backgroundColor=(0.46, 0.38, 0.46))  # Muted purple for spine controls
        cmds.columnLayout(adjustableColumn=True, rowSpacing=3)
        
        # Headers row for spine controls
        cmds.rowLayout(numberOfColumns=6, columnWidth6=(250, 20, 20, 20, 20, 72), height=22)
        cmds.text(label="", width=250)  # Empty space above control name
        cmds.text(label="TX", align="center", font="smallPlainLabelFont", height=22)
        cmds.text(label="TY", align="center", font="smallPlainLabelFont", height=22)
        cmds.text(label="TZ", align="center", font="smallPlainLabelFont", height=22)
        cmds.text(label="RX", align="center", font="smallPlainLabelFont", height=22)
        cmds.text(label="RY    RZ", align="center", font="smallPlainLabelFont", height=22)
        cmds.setParent('..')  # headers row
        
        # Scrollable area for spine controls
        self.spine_controls_scroll = cmds.scrollLayout(height=120, childResizable=True, 
                                                      backgroundColor=(0.85, 0.85, 0.85))
        cmds.columnLayout(adjustableColumn=True, rowSpacing=3)
        # Spine control items will be added here dynamically
        cmds.setParent('..')  # columnLayout
        cmds.setParent('..')  # scrollLayout
        
        # Add Selected and Cycle Spine buttons on one line
        cmds.rowLayout(numberOfColumns=2, columnWidth2=(200, 200), adjustableColumn=1,
                      columnAttach=[(1, 'both', 2), (2, 'both', 2)])
        cmds.button(label="Add Selected", command=self.add_selected_to_spine_list, height=28,
                   backgroundColor=(0.42, 0.48, 0.42))  # Muted green for add
        cmds.button(label="Cycle Spine Control", command=self.invert_spine_channels, height=28,
                   backgroundColor=(0.46, 0.38, 0.46))  # Muted purple to match spine theme
        cmds.setParent('..')  # rowLayout
        
        cmds.setParent('..')  # columnLayout
        cmds.setParent('..')  # frameLayout



        cmds.separator(height=15, style="in")
        
        # Auto-detection options (moved to bottom)

        

        

    
    def _refresh_control_pairs_ui(self):
        """Refresh the dynamic control pairs UI."""
        # Clear existing UI elements
        children = cmds.scrollLayout(self.control_pairs_scroll, query=True, childArray=True) or []
        for child in children:
            cmds.deleteUI(child)
        
        # Set parent to scroll layout's column
        cmds.setParent(self.control_pairs_scroll)
        cmds.columnLayout(adjustableColumn=True, rowSpacing=2)
        
        # Create a row for each control pair
        for i, (left_ctrl, right_ctrl) in enumerate(zip(self.left_controls, self.right_controls)):
            # Ensure we have inversion data for this pair
            while len(self.control_inversions) <= i:
                # Default inversion settings - all unchecked by default
                self.control_inversions.append({
                    'tx': False, 'ty': False, 'tz': False,
                    'rx': False, 'ry': False, 'rz': False
                })
            
            inversion = self.control_inversions[i]
            self._create_control_pair_row(i, left_ctrl, right_ctrl, inversion)
        
        cmds.setParent('..')  # columnLayout
    
    def _create_control_pair_row(self, index, left_ctrl, right_ctrl, inversion):
        """Create a single control pair row with inversion checkboxes (no offset field)."""
        cmds.rowLayout(numberOfColumns=2, columnWidth2=(320, 120))
        
        # Controls section - matching bulk operations structure exactly
        cmds.rowLayout(numberOfColumns=3, columnWidth3=(135, 50, 135))
        # Left control (read-only text) - truncate if too long
        left_display = left_ctrl.split(':')[-1] if ':' in left_ctrl else left_ctrl
        if len(left_display) > 18:
            left_display = left_display[:15] + "..."
        cmds.text(label=left_display, align="center", annotation=left_ctrl)
        
        # Direction swap button (shows bidirectional swap and allows swapping)
        cmds.button(label="→", width=50, height=20,
                   backgroundColor=(0.6, 0.4, 0.6),
                   annotation="Click to swap left/right controls",
                   command=lambda x, idx=index: self._swap_control_pair(idx))
        
        # Right control (read-only text) - truncate if too long
        right_display = right_ctrl.split(':')[-1] if ':' in right_ctrl else right_ctrl
        if len(right_display) > 18:
            right_display = right_display[:15] + "..."
        cmds.text(label=right_display, align="center", annotation=right_ctrl)
        cmds.setParent('..')  # controls section
        
        # Inversion checkboxes only (no offset field)
        cmds.rowLayout(numberOfColumns=5, columnWidth5=(20, 20, 20, 20, 60))
        tx_cb = cmds.checkBox(label='', value=inversion['tx'], height=20,
                              changeCommand=lambda x, idx=index, axis='tx': self._update_inversion(idx, axis, x))
        ty_cb = cmds.checkBox(label='', value=inversion['ty'], height=20,
                              changeCommand=lambda x, idx=index, axis='ty': self._update_inversion(idx, axis, x))
        tz_cb = cmds.checkBox(label='', value=inversion['tz'], height=20,
                              changeCommand=lambda x, idx=index, axis='tz': self._update_inversion(idx, axis, x))
        rx_cb = cmds.checkBox(label='', value=inversion['rx'], height=20,
                              changeCommand=lambda x, idx=index, axis='rx': self._update_inversion(idx, axis, x))
        # RY, RZ checkbox and Remove button in combined column
        cmds.rowLayout(numberOfColumns=3, columnWidth3=(20, 20, 20))
        ry_cb = cmds.checkBox(label='', value=inversion['ry'], height=20,
                              changeCommand=lambda x, idx=index, axis='ry': self._update_inversion(idx, axis, x))
        rz_cb = cmds.checkBox(label='', value=inversion['rz'], height=20,
                              changeCommand=lambda x, idx=index, axis='rz': self._update_inversion(idx, axis, x))
        cmds.button(label="✕", width=20, height=20,
                    command=lambda x, idx=index: self._remove_control_pair(idx),
                    backgroundColor=(0.7, 0.5, 0.5))  # Red for remove actions
        cmds.setParent('..')  # RY RZ X inner rowLayout  
        cmds.setParent('..')  # offset and checkboxes row
        cmds.setParent('..')  # main row
    
    def _update_inversion(self, index, axis, value):
        """Update inversion setting for a specific control pair and axis."""
        if index < len(self.control_inversions):
            self.control_inversions[index][axis] = value

    


    
    def _swap_control_pair(self, index):
        """Swap the left and right controls for a control pair"""
        if 0 <= index < len(self.left_controls) and 0 <= index < len(self.right_controls):
            # Swap the controls in the data structures
            self.left_controls[index], self.right_controls[index] = self.right_controls[index], self.left_controls[index]
            
            # Refresh the UI to show the swapped controls
            self._refresh_control_pairs_ui()
            
            print(f"Swapped controls: '{self.right_controls[index]}' <-> '{self.left_controls[index]}'")
    
    def _swap_all_control_pairs(self, *_):
        """Swap all left and right control pairs"""
        if len(self.left_controls) == len(self.right_controls):
            # Swap all pairs
            for i in range(len(self.left_controls)):
                self.left_controls[i], self.right_controls[i] = self.right_controls[i], self.left_controls[i]
            
            # Refresh the UI to show all swapped controls
            self._refresh_control_pairs_ui()
            
            print(f"Swapped all {len(self.left_controls)} control pairs")
        else:
            cmds.warning("Cannot swap all pairs - left and right lists have different lengths")
    
    def _remove_control_pair(self, index):
        """Remove a control pair and refresh the UI."""
        if 0 <= index < len(self.left_controls):
            left_ctrl = self.left_controls.pop(index)
            right_ctrl = self.right_controls.pop(index)
            if index < len(self.control_inversions):
                self.control_inversions.pop(index)

            self._refresh_control_pairs_ui()
    
    def setup_copy_offset_tab(self):
        """Setup the Copy with Offset functionality tab with per-object settings."""
        cmds.text(label="Copy with Time and Value Offset", font="boldLabelFont")
        cmds.separator(height=10)
        
        # Object list with per-object offset and channel settings
        cmds.frameLayout(label="Objects with Individual Offset Settings", collapsable=False, 
                        marginHeight=8, marginWidth=8, borderVisible=True,
                        backgroundColor=(0.42, 0.45, 0.48))  # Blue-gray theme
        cmds.columnLayout(adjustableColumn=True, rowSpacing=3)
        
        # Headers with improved styling using nested layouts
        cmds.rowLayout(numberOfColumns=4, columnWidth4=(120, 60, 60, 240), height=25)
        cmds.text(label="Object", align="center", font="boldLabelFont", height=22,
                 backgroundColor=(0.4, 0.45, 0.48))
        cmds.text(label="Time", align="center", font="boldLabelFont", height=22,
                 backgroundColor=(0.45, 0.4, 0.45))
        cmds.text(label="Value", align="center", font="boldLabelFont", height=22,
                 backgroundColor=(0.45, 0.4, 0.45))
        # Channel headers in nested layout
        cmds.rowLayout(numberOfColumns=6, columnWidth6=(35, 35, 35, 35, 35, 70))
        cmds.text(label="TX", align="center", font="smallPlainLabelFont", height=22,
                 backgroundColor=(0.4, 0.4, 0.4))
        cmds.text(label="TY", align="center", font="smallPlainLabelFont", height=22,
                 backgroundColor=(0.4, 0.4, 0.4))
        cmds.text(label="TZ", align="center", font="smallPlainLabelFont", height=22,
                 backgroundColor=(0.4, 0.4, 0.4))
        cmds.text(label="RX", align="center", font="smallPlainLabelFont", height=22,
                 backgroundColor=(0.4, 0.4, 0.4))
        cmds.text(label="RY", align="center", font="smallPlainLabelFont", height=22,
                 backgroundColor=(0.4, 0.4, 0.4))
        cmds.text(label="RZ", align="center", font="smallPlainLabelFont", height=22,
                 backgroundColor=(0.4, 0.4, 0.4))
        cmds.setParent('..')  # channel headers layout
        cmds.setParent('..')  # main header layout
        
        # Bulk editing controls positioned below headers
        cmds.rowLayout(numberOfColumns=4, columnWidth4=(120, 60, 60, 240), height=22)
        cmds.text(label="", width=120)  # Empty space above Object
        cmds.intField(value=1, width=55, annotation="Set this time offset for all objects",
                     changeCommand=self._set_all_copy_time_offsets)
        cmds.floatField(value=0.0, width=55, precision=2, annotation="Set this value offset for all objects",
                       changeCommand=self._set_all_copy_value_offsets)
        # Bulk checkboxes for channels
        cmds.rowLayout(numberOfColumns=6, columnWidth6=(35, 35, 35, 35, 35, 70))
        self.copy_bulk_tx_chk = cmds.checkBox(label='', value=True,
                                             changeCommand=lambda x: self._set_all_copy_channels('tx', x))
        self.copy_bulk_ty_chk = cmds.checkBox(label='', value=True,
                                             changeCommand=lambda x: self._set_all_copy_channels('ty', x))
        self.copy_bulk_tz_chk = cmds.checkBox(label='', value=True,
                                             changeCommand=lambda x: self._set_all_copy_channels('tz', x))
        self.copy_bulk_rx_chk = cmds.checkBox(label='', value=True,
                                             changeCommand=lambda x: self._set_all_copy_channels('rx', x))
        self.copy_bulk_ry_chk = cmds.checkBox(label='', value=True,
                                             changeCommand=lambda x: self._set_all_copy_channels('ry', x))
        cmds.rowLayout(numberOfColumns=2, columnWidth2=(35, 35))
        self.copy_bulk_rz_chk = cmds.checkBox(label='', value=True,
                                             changeCommand=lambda x: self._set_all_copy_channels('rz', x))
        cmds.button(label="X", width=30, height=18,
                   command=self.clear_all_copy_objects,
                   backgroundColor=(0.7, 0.5, 0.5),
                   annotation="Clear all objects")
        cmds.setParent('..')  # inner rowLayout
        cmds.setParent('..')  # bulk checkboxes layout
        cmds.setParent('..')  # bulk controls layout
        
        # Scrollable area for object list
        self.copy_offset_scroll = cmds.scrollLayout(height=160, childResizable=True, 
                                                   backgroundColor=(0.85, 0.85, 0.85))
        cmds.columnLayout(adjustableColumn=True, rowSpacing=3)
        # Object rows will be added here dynamically
        cmds.setParent('..')  # columnLayout
        cmds.setParent('..')  # scrollLayout
        
        cmds.setParent('..')  # columnLayout
        cmds.setParent('..')  # frameLayout
        
        cmds.separator(height=12, style="in")
        # Add button for object management  
        cmds.button(label="Add Selected Objects", command=self.add_selected_copy_objects, height=28,
                   backgroundColor=(0.42, 0.48, 0.42))  # Muted green for add actions
        
        cmds.separator(height=15, style="in")
        
        # Animation Layer option
        cmds.frameLayout(label="Animation Layer Options", collapsable=False,
                        marginHeight=8, marginWidth=8, borderVisible=True,
                        backgroundColor=(0.45, 0.42, 0.48))
        cmds.columnLayout(adjustableColumn=True, rowSpacing=5)
        
        cmds.rowLayout(numberOfColumns=2, columnWidth2=(200, 200), adjustableColumn=2)
        self.copy_to_layer_checkbox = cmds.checkBox(label="Copy to New Animation Layer", 
                                                     value=False,
                                                     changeCommand=self._toggle_layer_name_field,
                                                     annotation="Create a new animation layer for the offset animation")
        cmds.setParent('..')
        
        cmds.rowLayout(numberOfColumns=2, columnWidth2=(100, 300), adjustableColumn=2)
        cmds.text(label="Layer Name:", align="right", enable=False)
        self.layer_name_field = cmds.textField(text="OffsetLayer", enable=False,
                                               annotation="Name for the new animation layer")
        cmds.setParent('..')
        
        cmds.setParent('..')
        cmds.setParent('..')
        
        cmds.separator(height=15, style="in")
        
        # Copy button with improved styling
        cmds.button(label="Copy with Offset", command=self.copy_with_offset, height=35, 
                   backgroundColor=(0.42, 0.48, 0.42))  # Consistent muted green

    def setup_ik_fk_switcher_tab(self):
        """Setup the IK/FK Switcher functionality tab."""
        cmds.scrollLayout(horizontalScrollBarThickness=0, verticalScrollBarThickness=10)
        cmds.columnLayout(adjustableColumn=True, rowSpacing=10, columnOffset=("both", 10))
        
        # Title
        cmds.text(label="Dragon Rig IK/FK Switcher", align="center", font="boldLabelFont", height=30)
        cmds.separator(style="in", height=10)
        
        # Instructions
        cmds.frameLayout(label="Instructions", collapsable=True, collapse=False, 
                        marginHeight=8, marginWidth=8, borderVisible=True,
                        backgroundColor=(0.45, 0.42, 0.38))
        cmds.columnLayout(adjustableColumn=True, rowSpacing=5)
        cmds.text(label="1. Select an IK or FK control (L or R)", align="left")
        cmds.text(label="2. Set your timeline range", align="left")
        cmds.text(label="3. Click the appropriate button below", align="left")
        cmds.text(label="", height=5)
        cmds.text(label="The tool will automatically detect the side and", align="left", font="smallPlainLabelFont")
        cmds.text(label="bake animation across the entire timeline.", align="left", font="smallPlainLabelFont")
        cmds.setParent('..')
        cmds.setParent('..')
        
        cmds.separator(style="in", height=10)
        
        # Control naming reference
        cmds.frameLayout(label="Rig Controls (Reference)", collapsable=True, collapse=True,
                        marginHeight=8, marginWidth=8, borderVisible=True,
                        backgroundColor=(0.42, 0.45, 0.48))
        cmds.columnLayout(adjustableColumn=True, rowSpacing=3)
        cmds.text(label="IK Controls:", font="boldLabelFont", align="left")
        cmds.text(label="  • IK Handle: IKLeg_L / IKLeg_R", align="left", font="smallPlainLabelFont")
        cmds.text(label="  • Pole Vector: PoleLeg_L / PoleLeg_R", align="left", font="smallPlainLabelFont")
        cmds.text(label="  • Switch: FKIKLeg_L/R.FKIKBlend (0=FK, 10=IK)", align="left", font="smallPlainLabelFont")
        cmds.separator(height=5)
        cmds.text(label="FK Controls:", font="boldLabelFont", align="left")
        cmds.text(label="  • FKHip_L/R, FKKnee_L/R, FKKnee1_L/R", align="left", font="smallPlainLabelFont")
        cmds.text(label="  • FKAnkle_L/R, FKToes_L/R", align="left", font="smallPlainLabelFont")
        cmds.setParent('..')
        cmds.setParent('..')
        
        cmds.separator(style="in", height=10)
        
        # Timeline range display
        start = cmds.playbackOptions(query=True, minTime=True)
        end = cmds.playbackOptions(query=True, maxTime=True)
        cmds.text(label=f"Current Timeline: {int(start)} to {int(end)} frames", 
                 align="center", font="boldLabelFont",
                 backgroundColor=(0.3, 0.3, 0.3))
        
        cmds.separator(style="in", height=15)
        
        # Switch buttons
        cmds.frameLayout(label="Switching Operations", collapsable=False,
                        marginHeight=8, marginWidth=8, borderVisible=True,
                        backgroundColor=(0.45, 0.42, 0.38))
        cmds.columnLayout(adjustableColumn=True, rowSpacing=10)
        
        cmds.button(
            label="IK → FK (Bake to FK Controls)",
            command=lambda _: self.execute_ik_fk_switch("ik_to_fk"),
            height=45,
            backgroundColor=[0.3, 0.5, 0.8],
            annotation="Switch from IK animation to FK. Bakes IK poses to FK controls across timeline."
        )
        
        cmds.button(
            label="FK → IK (Bake to IK Controls)",
            command=lambda _: self.execute_ik_fk_switch("fk_to_ik"),
            height=45,
            backgroundColor=[0.5, 0.3, 0.8],
            annotation="Switch from FK animation to IK. Bakes FK poses to IK controls across timeline."
        )
        
        cmds.setParent('..')
        cmds.setParent('..')
        
        cmds.separator(style="in", height=15)
        
        # Status/Help text
        cmds.frameLayout(label="Tips", collapsable=True, collapse=False,
                        marginHeight=8, marginWidth=8, borderVisible=True,
                        backgroundColor=(0.42, 0.48, 0.42))
        cmds.columnLayout(adjustableColumn=True, rowSpacing=3)
        cmds.text(label="• Make sure your timeline is set correctly before switching", 
                 align="left", font="smallPlainLabelFont")
        cmds.text(label="• The tool preserves all animation keys by default", 
                 align="left", font="smallPlainLabelFont")
        cmds.text(label="• Undo (Ctrl+Z) works if you need to revert", 
                 align="left", font="smallPlainLabelFont")
        cmds.text(label="• You can switch back and forth as needed", 
                 align="left", font="smallPlainLabelFont")
        cmds.setParent('..')
        cmds.setParent('..')
        
        cmds.setParent('..')  # columnLayout
        cmds.setParent('..')  # scrollLayout

    def execute_ik_fk_switch(self, direction):
        """Execute IK/FK switch using the integrated switcher logic."""
        # Import the switcher functionality
        try:
            # Detect side from selection
            selection = cmds.ls(selection=True)
            if not selection:
                cmds.warning("Nothing selected. Please select an IK or FK control.")
                return
            
            side = None
            for obj in selection:
                if '_L' in obj:
                    side = 'L'
                    break
                elif '_R' in obj:
                    side = 'R'
                    break
            
            if not side:
                cmds.warning("Could not detect side from selection. Please select a control with _L or _R suffix.")
                return
            
            # Get time range
            start = cmds.playbackOptions(query=True, minTime=True)
            end = cmds.playbackOptions(query=True, maxTime=True)
            
            # Confirm with user
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
                    self.switch_ik_to_fk_integrated(side, start, end)
            
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
                    self.switch_fk_to_ik_integrated(side, start, end)
                    
        except Exception as e:
            cmds.error(f"Error during IK/FK switch: {e}")

    def switch_ik_to_fk_integrated(self, side, start, end):
        """Switch from IK to FK - integrated into Cycle Maker."""
        # Control definitions
        ik_controls = {
            'L': {'ik_handle': 'IKLeg_L', 'pole_vector': 'PoleLeg_L', 'switch_attr': 'FKIKLeg_L.FKIKBlend'},
            'R': {'ik_handle': 'IKLeg_R', 'pole_vector': 'PoleLeg_R', 'switch_attr': 'FKIKLeg_R.FKIKBlend'}
        }
        fk_controls = {
            'L': ['FKHip_L', 'FKKnee_L', 'FKKnee1_L', 'FKAnkle_L', 'FKToes_L'],
            'R': ['FKHip_R', 'FKKnee_R', 'FKKnee1_R', 'FKAnkle_R', 'FKToes_R']
        }
        joints = {
            'L': ['Hip_L', 'Knee_L', 'Knee1_L', 'Ankle_L'],
            'R': ['Hip_R', 'Knee_R', 'Knee1_R', 'Ankle_R']
        }
        
        fk_ctrls = fk_controls[side]
        jnts = joints[side]
        switch_attr = ik_controls[side]['switch_attr']
        
        # Check if controls exist
        missing = [ctrl for ctrl in fk_ctrls if not cmds.objExists(ctrl)]
        if missing:
            cmds.warning(f"Missing FK controls: {missing}")
            return
        
        missing_joints = [jnt for jnt in jnts if not cmds.objExists(jnt)]
        if missing_joints:
            cmds.warning(f"Missing joints: {missing_joints}")
            return
        
        print(f"Switching IK to FK for {side} side from frame {start} to {end}")
        current_time = cmds.currentTime(query=True)
        
        try:
            # Set switch to IK mode first
            cmds.setAttr(switch_attr, 10)
            
            # Bake FK controls to match IK animation
            for frame in range(int(start), int(end) + 1):
                cmds.currentTime(frame)
                
                for fk_ctrl, joint in zip(fk_ctrls[:4], jnts):
                    if cmds.objExists(fk_ctrl) and cmds.objExists(joint):
                        joint_rot = cmds.xform(joint, query=True, worldSpace=True, rotation=True)
                        try:
                            cmds.xform(fk_ctrl, worldSpace=True, rotation=joint_rot)
                        except:
                            joint_rot_local = cmds.getAttr(f"{joint}.rotate")[0]
                            cmds.setAttr(f"{fk_ctrl}.rotateX", joint_rot_local[0])
                            cmds.setAttr(f"{fk_ctrl}.rotateY", joint_rot_local[1])
                            cmds.setAttr(f"{fk_ctrl}.rotateZ", joint_rot_local[2])
                        
                        cmds.setKeyframe(fk_ctrl, attribute='rotate')
            
            # Switch to FK mode
            cmds.setKeyframe(switch_attr, time=start, value=0)
            
            print(f"Successfully switched IK to FK for {side} side")
            cmds.confirmDialog(title="Success", message=f"IK to FK switch complete for {side} side!", button="OK")
            
        except Exception as e:
            cmds.error(f"Error during IK to FK switch: {e}")
        finally:
            cmds.currentTime(current_time)

    def switch_fk_to_ik_integrated(self, side, start, end):
        """Switch from FK to IK - integrated into Cycle Maker."""
        # Control definitions
        ik_controls = {
            'L': {'ik_handle': 'IKLeg_L', 'pole_vector': 'PoleLeg_L', 'switch_attr': 'FKIKLeg_L.FKIKBlend'},
            'R': {'ik_handle': 'IKLeg_R', 'pole_vector': 'PoleLeg_R', 'switch_attr': 'FKIKLeg_R.FKIKBlend'}
        }
        joints = {
            'L': ['Hip_L', 'Knee_L', 'Knee1_L', 'Ankle_L'],
            'R': ['Hip_R', 'Knee_R', 'Knee1_R', 'Ankle_R']
        }
        ik_attrs = ['roll', 'rock', 'swivel']
        
        ik_handle = ik_controls[side]['ik_handle']
        pole_vector = ik_controls[side]['pole_vector']
        switch_attr = ik_controls[side]['switch_attr']
        jnts = joints[side]
        
        # Check if controls exist
        if not cmds.objExists(ik_handle):
            cmds.warning(f"IK handle not found: {ik_handle}")
            return
        
        if not cmds.objExists(pole_vector):
            cmds.warning(f"Pole vector not found: {pole_vector}")
            return
        
        missing_joints = [jnt for jnt in jnts if not cmds.objExists(jnt)]
        if missing_joints:
            cmds.warning(f"Missing joints: {missing_joints}")
            return
        
        print(f"Switching FK to IK for {side} side from frame {start} to {end}")
        current_time = cmds.currentTime(query=True)
        
        try:
            # Set switch to FK mode first
            cmds.setAttr(switch_attr, 0)
            
            # Bake IK controls to match FK animation
            for frame in range(int(start), int(end) + 1):
                cmds.currentTime(frame)
                
                ankle_joint = jnts[3]
                knee_joint = jnts[1]
                
                if cmds.objExists(ankle_joint):
                    # Get ankle world position
                    ankle_pos = cmds.xform(ankle_joint, query=True, worldSpace=True, translation=True)
                    cmds.xform(ik_handle, worldSpace=True, translation=ankle_pos)
                    
                    # Match IK handle rotation using constraint
                    temp_constraint = cmds.orientConstraint(ankle_joint, ik_handle, maintainOffset=False)[0]
                    cmds.delete(temp_constraint)
                    
                    cmds.setKeyframe(ik_handle, attribute=['translate', 'rotate'])
                
                # Match pole vector to knee position with offset
                if cmds.objExists(knee_joint):
                    knee_pos = cmds.xform(knee_joint, query=True, worldSpace=True, translation=True)
                    hip_joint = jnts[0]
                    ankle_joint = jnts[3]
                    
                    hip_pos = cmds.xform(hip_joint, query=True, worldSpace=True, translation=True)
                    ankle_pos = cmds.xform(ankle_joint, query=True, worldSpace=True, translation=True)
                    
                    # Calculate pole vector offset
                    import maya.api.OpenMaya as om
                    hip_vec = om.MVector(hip_pos)
                    knee_vec = om.MVector(knee_pos)
                    ankle_vec = om.MVector(ankle_pos)
                    
                    leg_vec = ankle_vec - hip_vec
                    to_knee = knee_vec - hip_vec
                    
                    proj_length = to_knee * leg_vec / leg_vec.length()
                    proj_point = hip_vec + (leg_vec.normal() * proj_length)
                    
                    pole_dir = (knee_vec - proj_point).normal()
                    pole_offset = 5.0
                    pole_pos = knee_vec + (pole_dir * pole_offset)
                    
                    cmds.xform(pole_vector, worldSpace=True, translation=[pole_pos.x, pole_pos.y, pole_pos.z])
                    cmds.setKeyframe(pole_vector, attribute='translate')
                
                # Reset IK control attributes to default
                for attr in ik_attrs:
                    attr_name = f"{ik_handle}.{attr}"
                    if cmds.objExists(attr_name):
                        cmds.setAttr(attr_name, 0)
                        cmds.setKeyframe(attr_name)
            
            # Switch to IK mode
            cmds.setKeyframe(switch_attr, time=start, value=10)
            
            print(f"Successfully switched FK to IK for {side} side")
            cmds.confirmDialog(title="Success", message=f"FK to IK switch complete for {side} side!", button="OK")
            
        except Exception as e:
            cmds.error(f"Error during FK to IK switch: {e}")
        finally:
            cmds.currentTime(current_time)

    # =========================================================================
    # SECTION 2: CONTROL MANAGEMENT
    # =========================================================================

    def add_selected_controls(self, *_):
        sel = cmds.ls(selection=True)
        if not sel:
            cmds.warning("No controls selected.")
            return
            
        # Auto-detect and update rig prefix from first selected control (hidden from UI)
        first_ctrl = sel[0]
        detected_prefix = self.extract_rig_prefix(first_ctrl)
        current_prefix = cmds.textField(self.prefix_field, query=True, text=True)
        
        # Update prefix if it's different from current or if current is default
        if detected_prefix != current_prefix or current_prefix == "tigerA_rigMain_01_:":
            cmds.textField(self.prefix_field, edit=True, text=detected_prefix)
        
        # Auto-detect and pair left/right controls
        processed_controls = set()
        
        for ctrl in sel:
            # Skip if already processed
            if ctrl in processed_controls:
                continue
                
            ctrl_short = ctrl.split(':')[-1] if ':' in ctrl else ctrl
            
            # Determine if this is a left or right control
            is_left_ctrl = self.is_left(ctrl_short)
            is_right_ctrl = self.is_right(ctrl_short)
            
            if is_left_ctrl or is_right_ctrl:
                # Try to find its opposite
                opposite_ctrl = None
                if is_left_ctrl:
                    opposite_ctrl = self.get_other_side(ctrl, left_to_right=True)
                    source_ctrl = ctrl
                    target_ctrl = opposite_ctrl
                else:  # is_right_ctrl
                    opposite_ctrl = self.get_other_side(ctrl, left_to_right=False)
                    source_ctrl = opposite_ctrl
                    target_ctrl = ctrl
                
                if opposite_ctrl:
                    # Check if opposite is also in the selection
                    if opposite_ctrl in sel:
                        # Both sides selected, mark both as processed
                        processed_controls.add(ctrl)
                        processed_controls.add(opposite_ctrl)
                    else:
                        # Only one side selected, mark it as processed
                        processed_controls.add(ctrl)
                    
                    # Check if this pair already exists
                    existing_pair_index = self._find_existing_pair(source_ctrl, target_ctrl)
                    
                    if existing_pair_index is not None:
                        # Replace existing pair
                        self.left_controls[existing_pair_index] = source_ctrl
                        self.right_controls[existing_pair_index] = target_ctrl
                        print(f"Replaced pair: {source_ctrl} (L) -> {target_ctrl} (R)")
                    else:
                        # Add new pair
                        self.left_controls.append(source_ctrl)
                        self.right_controls.append(target_ctrl)
                        # Initialize inversion settings for this pair
                        self.control_inversions.append({
                            'tx': False, 'ty': False, 'tz': False,
                            'rx': False, 'ry': False, 'rz': False
                        })
                        print(f"Added pair: {source_ctrl} (L) -> {target_ctrl} (R)")
                else:
                    cmds.warning(f"Cannot find opposite control for: {ctrl_short}")
                    processed_controls.add(ctrl)
            else:
                # Not a left/right control, skip it
                cmds.warning(f"Control {ctrl_short} doesn't appear to be a left or right control (no _L or _R suffix)")
                processed_controls.add(ctrl)
        
        # Refresh the UI to show new control pairs
        self._refresh_control_pairs_ui()

    def _find_existing_pair(self, ctrl1, ctrl2):
        """Find if either ctrl1 or ctrl2 already exists in the control pairs.
        Returns the index of the existing pair, or None if not found."""
        for i in range(len(self.left_controls)):
            left_ctrl = self.left_controls[i]
            right_ctrl = self.right_controls[i]
            
            # Check if either control is already in this pair
            if ctrl1 == left_ctrl or ctrl1 == right_ctrl or ctrl2 == left_ctrl or ctrl2 == right_ctrl:
                return i
        return None

    def remove_selected_controls(self, *_):
        # Note: Individual remove buttons are now handled by _remove_control_pair method
        # This method is kept for backward compatibility but currently does nothing
        # since removal is handled per-row in the new UI
        cmds.warning("Use the individual 'Remove' buttons next to each control pair.")

    # =========================================================================
    # SECTION 3: UTILITY FUNCTIONS & ANIMATION HELPERS
    # =========================================================================

    # ---------------------
    # String manipulation utilities  
    # ---------------------
    def is_left(self, name):
        """Check if control name indicates left side (L_ or _L patterns)."""
        return bool(re.search(r"(^|:|_)L(_|$)", name))

    def is_right(self, name):
        """Check if control name indicates right side (R_ or _R patterns)."""
        return bool(re.search(r"(^|:|_)R(_|$)", name))

    def get_other_side(self, name, left_to_right=True):
        """Convert left control name to right (or vice versa). Returns None if opposite doesn't exist."""
        original_name = name
        print(f"DEBUG: get_other_side called with: '{original_name}', left_to_right={left_to_right}")
        
        if left_to_right:
            # Handle both L_ and _L patterns
            name = re.sub(r"(^|:|_)L(_|$)", r"\1R\2", name)
        else:
            # Handle both R_ and _R patterns
            name = re.sub(r"(^|:|_)R(_|$)", r"\1L\2", name)
        
        print(f"DEBUG: Pattern conversion result: '{name}'")
        
        # Check if the conversion actually changed the name
        if name == original_name:
            # No L/R pattern found, return None
            print(f"DEBUG: No L/R pattern found in '{original_name}'")
            return None
            
        # Check if the opposite control actually exists in the scene
        if cmds.objExists(name):
            return name
        else:
            # Try Maya's symmetry selection as fallback
            try:
                print(f"DEBUG: Trying Maya symmetry for '{original_name}'")
                
                # Store current selection to restore later
                current_selection = cmds.ls(selection=True)
                
                # Check if the original control exists first
                if not cmds.objExists(original_name):
                    print(f"DEBUG: Original control '{original_name}' does not exist!")
                    return None
                
                # Select the original control first
                cmds.select(original_name, replace=True)
                print(f"DEBUG: Selected '{original_name}' successfully")
                
                # Use cmds.select with symmetry flag (more reliable than MEL)
                cmds.select(symmetry=True)
                
                # Get the symmetry selection result
                symmetry_selection = cmds.ls(selection=True)
                print(f"DEBUG: Symmetry selection result: {symmetry_selection}")
                
                # Find the symmetric counterpart (should be different from original)
                opposite_found = None
                for ctrl in symmetry_selection:
                    if ctrl != original_name and cmds.objExists(ctrl):
                        opposite_found = ctrl
                        break
                
                # Restore original selection
                if current_selection:
                    cmds.select(current_selection, replace=True)
                else:
                    cmds.select(clear=True)
                
                if opposite_found:
                    print(f"Found opposite using Maya symmetry: {original_name} -> {opposite_found}")
                    return opposite_found
                else:
                    print(f"DEBUG: No opposite found in symmetry selection")
                        
            except Exception as e:
                print(f"Maya symmetry selection failed: {e}")
                try:
                    # Restore selection even if symmetry failed
                    if current_selection:
                        cmds.select(current_selection, replace=True)
                    else:
                        cmds.select(clear=True)
                except:
                    pass
                
            # Final fallback: Try more aggressive pattern matching
            try:
                # Get all objects in scene that might be opposites
                all_objects = cmds.ls(type='transform')
                
                # Create pattern variations to search for
                search_patterns = []
                if 'R_' in original_name:
                    search_patterns.append(original_name.replace('R_', 'L_'))
                if '_R' in original_name:
                    search_patterns.append(original_name.replace('_R', '_L'))
                if ':R_' in original_name:
                    search_patterns.append(original_name.replace(':R_', ':L_'))
                if 'Right' in original_name:
                    search_patterns.append(original_name.replace('Right', 'Left'))
                if 'right' in original_name:
                    search_patterns.append(original_name.replace('right', 'left'))
                    
                # Check each pattern
                for pattern in search_patterns:
                    if pattern in all_objects:
                        print(f"Found opposite using pattern matching: {original_name} -> {pattern}")
                        return pattern
                        
            except Exception as e:
                print(f"Pattern matching fallback failed: {e}")
            
            print(f"Could not find opposite control for '{original_name}' (tried '{name}' and various patterns)")
            return None

    def extract_rig_prefix(self, control_name):
        """Extract the rig prefix/namespace from a control name.
        Examples: 
        - 'the_tyrant_rig:IKLeg_R' -> 'the_tyrant_rig:'
        - 'tigerA_rigMain_01_:L_arm_CTL' -> 'tigerA_rigMain_01_:'
        - 'IKLeg_R' -> ''
        """
        if ':' in control_name:
            return control_name.split(':', 1)[0] + ':'
        return ''

    # ---------------------
    # Animation curve utilities
    # ---------------------
    def _anim_curve_for_attr(self, attr_plug):
        """Return the first animCurve node connected to the given attribute plug.
        attr_plug is like 'node.attr'. Returns None if not found.
        """
        # Prefer robust query that traverses through utility nodes
        try:
            curves = cmds.keyframe(attr_plug, query=True, name=True) or []
            if curves:
                return curves[0]
        except Exception:
            pass

        # Fallback: direct connections
        conns = cmds.listConnections(attr_plug, s=True, d=False) or []
        for n in conns:
            try:
                nt = cmds.nodeType(n)
            except Exception:
                continue
            if isinstance(nt, str) and nt.startswith('animCurve'):
                return n
        return None

    def _apply_cycle_infinity_mel(self, curves):
        """Apply cycle infinity to animation curves using MEL commands.
        This is more reliable than the Python cmds.setInfinity approach.
        """
        if not curves:
            return

        # Normalize to list
        if isinstance(curves, str):
            curves = [curves]

        for curve in curves:
            if not curve or not cmds.objExists(curve):
                continue
            # Some animCurve types use preInfinity/postInfinity enum (int). 2 == cycle
            for attr_name, label in (("preInfinity", "pre"), ("postInfinity", "post")):
                try:
                    locked = cmds.getAttr(f"{curve}.{attr_name}", lock=True)
                except Exception:
                    locked = False
                if locked:
                    try:
                        cmds.setAttr(f"{curve}.{attr_name}", lock=False)
                    except Exception as e:
                        continue
                try:
                    before = cmds.getAttr(f"{curve}.{attr_name}")
                except Exception:
                    before = "?"
                # Direct setAttr (0=constant,1=linear,2=cycle,3=cycleRelative,4=oscillate)
                try:
                    cmds.setAttr(f"{curve}.{attr_name}", 3)
                except Exception as e:
                    # Fallback: attempt MEL targeted at curve
                    try:
                        import maya.mel as mel
                        mel.eval(f"select -r {curve};")
                        if label == 'pre':
                            mel.eval("setInfinity -pri cycle;")
                        else:
                            mel.eval("setInfinity -poi cycle;")
                    except Exception as me:
                        pass
                try:
                    after = cmds.getAttr(f"{curve}.{attr_name}")
                except Exception:
                    after = "?"
                # Relock if it was locked originally
                if locked:
                    try:
                        cmds.setAttr(f"{curve}.{attr_name}", lock=True)
                    except Exception:
                        pass

    # =========================================================================
    # SECTION 5: INFINITY MANAGEMENT
    # =========================================================================

    def _apply_cycle_infinity_advanced(self, curves, verbose=True):
        """Attempt to set pre/post infinity to cycle with multiple strategies and diagnostics.
        Strategies per curve:
          1. Direct setInfinity command with full parameter specification
          2. Direct setAttr (int 2)
          3. cmds.setInfinity(preInfinite='cycle', postInfinite='cycle')
          4. OpenMaya API plug set (setInt)
        Batch strategies (all curves):
          5. MEL batch: select all curves once, set both pri & poi simultaneously
        Diagnostics:
          - keyframe count & times
          - reference status & node lock state
          - original and final values
          - single-key warning (cycle visually meaningless with <2 keys)
        Returns (updated, failed) lists.
        """
        if not curves:
            return [], []
        # Normalize
        if isinstance(curves, str):
            curves = [curves]
        updated = []
        pending = []
        
        # Pre-pass collect info
        for c in curves:
            if not cmds.objExists(c):
                if verbose:
                    print(f"INFINITY_ADV: Curve missing {c}")
                continue
            
            # Try direct setInfinity command first with all parameters
            try:
                # This applies to all keyframe tangents on the curve
                cmds.setInfinity(c, preInfinite="cycle", postInfinite="cycle", 
                                controlPoints=True, shape=True, hierarchy="none")
                
                # Verify it worked
                pre_val = cmds.getAttr(c+'.preInfinity')
                post_val = cmds.getAttr(c+'.postInfinity')
                if pre_val == 3 and post_val == 3:
                    if verbose:
                        print(f"INFINITY_ADV: Direct setInfinity with params success {c}")
                    updated.append(c)
                    continue
            except Exception as e:
                if verbose:
                    print(f"INFINITY_ADV: Direct setInfinity with params failed {c}: {e}")
            
            try:
                kt = cmds.keyframe(c, query=True, timeChange=True) or []
            except Exception:
                kt = []
            kcount = len(kt)
            try:
                ref = cmds.referenceQuery(c, isNodeReferenced=True)
            except Exception:
                ref = False
            try:
                locked_node = cmds.lockNode(c, query=True, lock=True) or [False]
                locked_node = any(locked_node)
            except Exception:
                locked_node = False
            try:
                pre0 = cmds.getAttr(c+'.preInfinity')
                post0 = cmds.getAttr(c+'.postInfinity')
            except Exception:
                pre0 = post0 = '??'
            if verbose:
                rng = (min(kt), max(kt)) if kcount else (None, None)
                print(f"INFINITY_ADV: {c} type={cmds.nodeType(c)} keys={kcount} range={rng} ref={ref} lockedNode={locked_node} pre={pre0} post={post0}")
            # Try direct setAttr command first
            success_direct = False
            for attr in ('preInfinity','postInfinity'):
                try:
                    cmds.setAttr(f'{c}.{attr}', 3)
                except Exception as e:
                    if verbose:
                        print(f"INFINITY_ADV: setAttr failed {c}.{attr}: {e}")
            try:
                preA = cmds.getAttr(c+'.preInfinity')
                postA = cmds.getAttr(c+'.postInfinity')
                success_direct = (preA == 3 and postA == 3)
            except Exception:
                success_direct = False
            if success_direct:
                if verbose:
                    print(f"INFINITY_ADV: Direct setAttr success {c} -> (2,2)")
                updated.append(c)
                continue
            # Try cmds.setInfinity
            try:
                cmds.setInfinity(c, preInfinite='cycle', postInfinite='cycle')
            except Exception as e:
                if verbose:
                    print(f"INFINITY_ADV: cmds.setInfinity failed {c}: {e}")
            try:
                preB = cmds.getAttr(c+'.preInfinity')
                postB = cmds.getAttr(c+'.postInfinity')
                if preB == 3 and postB == 3:
                    if verbose:
                        print(f"INFINITY_ADV: cmds.setInfinity success {c}")
                    updated.append(c)
                    continue
            except Exception:
                pass
            # Try OpenMaya API
            try:
                import maya.api.OpenMaya as om
                sel = om.MSelectionList(); sel.add(c)
                mobj = sel.getDependNode(0)
                fn = om.MFnDependencyNode(mobj)
                for attr in ('preInfinity','postInfinity'):
                    plug = fn.findPlug(attr, False)
                    plug.setInt(3)
                preC = cmds.getAttr(c+'.preInfinity')
                postC = cmds.getAttr(c+'.postInfinity')
                if preC == 3 and postC == 3:
                    if verbose:
                        print(f"INFINITY_ADV: OpenMaya plug success {c}")
                    updated.append(c)
                    continue
            except Exception as e:
                if verbose:
                    print(f"INFINITY_ADV: OpenMaya attempt failed {c}: {e}")
            # Record for batch MEL attempt
            pending.append(c)
        # Batch MEL (single selection) if any pending
        if pending:
            if verbose:
                print(f"INFINITY_ADV: Batch MEL attempt on {len(pending)} pending curves")
            try:
                import maya.mel as mel
                mel.eval('select -r ' + ' '.join(pending) + ';')
                # Single call specifying both flags sometimes behaves differently than split calls
                mel.eval('setInfinity -pri 2 -poi 2;')  # numeric flags
                # Also try named for safety
                mel.eval('setInfinity -pri "cycle" -poi "cycle";')
            except Exception as e:
                if verbose:
                    print(f"INFINITY_ADV: Batch MEL failure: {e}")
            # Re-check
            recheck = []
            for c in list(pending):
                try:
                    if cmds.getAttr(c+'.preInfinity') == 3 and cmds.getAttr(c+'.postInfinity') == 3:
                        updated.append(c)
                    else:
                        recheck.append(c)
                except Exception:
                    recheck.append(c)
            pending = recheck
        # Single-key warning
        for c in list(pending):
            try:
                kcount = cmds.keyframe(c, query=True, keyframeCount=True)
                if kcount < 2:
                    if verbose:
                        print(f"INFINITY_ADV: {c} has <2 keys; cycling pre/post may be suppressed by Maya.")
            except Exception:
                pass
        return updated, pending

    # ---------------------
    # Manual infinity application
    # ---------------------
    def _collect_anim_curves_from_nodes(self, nodes):
        curves = []
        for node in nodes:
            if not cmds.objExists(node):
                continue
            # Method 1: keyframe query
            try:
                kcurves = cmds.keyframe(node, query=True, name=True) or []
                for c in kcurves:
                    if c not in curves:
                        curves.append(c)
            except Exception:
                pass
            # Method 2: listConnections by animCurve
            try:
                conns = cmds.listConnections(node, source=True, destination=False) or []
                for c in conns:
                    try:
                        if cmds.objExists(c) and cmds.nodeType(c).startswith('animCurve') and c not in curves:
                            curves.append(c)
                    except Exception:
                        continue
            except Exception:
                pass
        return curves

    def apply_cycle_infinity_for_selection(self, *_):
        sel = cmds.ls(selection=True) or []
        if not sel:
            cmds.warning("Select controls or animCurves to apply cycle infinity.")
            return

        # Ensure 2+ keys is now always enabled by default
        ensure_two_keys = True

        direct_curves = [s for s in sel if cmds.objExists(s) and cmds.nodeType(s).startswith('animCurve')]
        target_nodes = [s for s in sel if s not in direct_curves]
        curves = list(direct_curves)
        curves += self._collect_anim_curves_from_nodes(target_nodes)
        curves = list(dict.fromkeys(curves))  # unique preserve

        if ensure_two_keys:
            for curve in curves:
                self._ensure_two_keys(curve)

        if not curves:
            cmds.warning("No animCurves found on selection.")
            return

        updated, failed = self._apply_cycle_infinity_advanced(curves, verbose=False)

        # Always generate the manual script for all curves
        self.generate_manual_infinity_script(curves)

        if updated and not failed:
            cmds.inViewMessage(amg=f"Applied cycle infinity to {len(updated)} curve(s)", pos='midCenter', fade=True)
        elif updated:
            cmds.inViewMessage(amg=f"Cycle infinity partial: {len(updated)}/{len(curves)}", pos='midCenter', fade=True)

    def generate_manual_infinity_script(self, curves):
        """Generate a script to manually apply infinity settings to the given curves."""
        if not curves:
            print("No curves provided to generate a manual script.")
            return

        script_lines = []
        for curve in curves:
            if cmds.objExists(curve):
                script_lines.append(f"cmds.setAttr('{curve}.preInfinity', 3)")
                script_lines.append(f"cmds.setAttr('{curve}.postInfinity', 3)")

        if script_lines:
            print("\n# Generated script to manually apply infinity settings:\n")
            for line in script_lines:
                print(line)
            print("\n# End of script\n")
        else:
            print("No valid curves found to generate a script.")

    def _apply_infinity_from_source(self, source_curve, target_curve):
        """Copy pre/post infinity from source_curve to target_curve.
        If force_cycle is enabled, applies cycle infinity instead.
        """
        if not source_curve or not target_curve:
            return
            
        # Force cycle infinity is now always enabled by default
        force_cycle = True
            
        if force_cycle:
            # Force cycle using direct attr method
            self._apply_cycle_infinity_mel([target_curve])
            return
            
        try:
            pre_val = cmds.getAttr('{}.preInfinity'.format(source_curve))
            post_val = cmds.getAttr('{}.postInfinity'.format(source_curve))
        except Exception:
            return
        inf_map = {0: 'constant', 1: 'linear', 2: 'cycle', 3: 'cycleRelative', 4: 'oscillate'}
        pre_str = inf_map.get(pre_val, 'constant')
        post_str = inf_map.get(post_val, 'constant')

        try:
            # Select the curve and use MEL commands for reliability
            cmds.select(target_curve, replace=True)
            import maya.mel as mel
            mel.eval(f"setInfinity -pri {pre_str};")
            mel.eval(f"setInfinity -poi {post_str};")
        except Exception:
            # Fallback to direct attribute setting
            try:
                cmds.setAttr('{}.preInfinity'.format(target_curve), pre_val)
                cmds.setAttr('{}.postInfinity'.format(target_curve), post_val)
            except Exception:
                pass

    def _keyed_attributes(self, node):
        """Return a list of attribute names on node that have connected animCurves."""
        attrs = []
        try:
            curves = cmds.keyframe(node, query=True, name=True) or []
        except Exception:
            curves = []
        if not curves:
            return attrs
        for c in set(curves):
            try:
                dest_plugs = cmds.listConnections(c + '.output', s=False, d=True, p=True) or []
            except Exception:
                dest_plugs = []
            for plug in dest_plugs:
                if plug.startswith(node + '.'):
                    attrs.append(plug.split('.')[-1])
        return list(dict.fromkeys(attrs))  # unique, preserve order

    # =========================================================================
    # SECTION 8: SPINE/CENTERLINE PROCESSING
    # =========================================================================

    def _get_spine_controls(self):
        """Return list of spine controls from data structures."""
        return self.spine_controls[:]
    
    def add_selected_to_spine_list(self, *_):
        """Add currently selected objects to the spine controls list."""
        selected = cmds.ls(selection=True) or []
        if not selected:
            cmds.warning("No objects selected to add to spine controls list.")
            return
        
        added_count = 0
        for item in selected:
            if item not in self.spine_controls:
                self.spine_controls.append(item)
                # Add default channel inversions (RY and RZ inverted for spine)
                self.spine_control_inversions.append({
                    'tx': False, 'ty': False, 'tz': False,
                    'rx': False, 'ry': True, 'rz': True  # Default spine inversions
                })
                added_count += 1
        
        if added_count > 0:
            self._refresh_spine_controls_ui()
            print(f"Added {added_count} controls to spine list")
    
    def remove_spine_control(self, index, *_):
        """Remove a spine control by index."""
        if 0 <= index < len(self.spine_controls):
            removed_control = self.spine_controls.pop(index)
            self.spine_control_inversions.pop(index)
            self._refresh_spine_controls_ui()
            print(f"Removed spine control: {removed_control}")
    
    def _refresh_spine_controls_ui(self):
        """Refresh the spine controls UI display."""
        # Clear existing UI elements in the scroll layout
        if cmds.scrollLayout(self.spine_controls_scroll, exists=True):
            children = cmds.scrollLayout(self.spine_controls_scroll, query=True, childArray=True) or []
            for child in children:
                if cmds.layout(child, exists=True):
                    cmds.deleteUI(child)
        
        # Set parent to scroll layout's column layout
        cmds.setParent(self.spine_controls_scroll)
        cmds.columnLayout(adjustableColumn=True, rowSpacing=3)
        
        # Create UI for each spine control
        for i, control in enumerate(self.spine_controls):
            self._create_spine_control_row(i, control)
        
        cmds.setParent('..')  # columnLayout
        cmds.setParent('..')  # scrollLayout
    
    def _create_spine_control_row(self, index, control_name):
        """Create a UI row for a single spine control."""
        inversions = self.spine_control_inversions[index]
        
        # Main row layout
        cmds.rowLayout(numberOfColumns=6, columnWidth6=(250, 20, 20, 20, 20, 72), height=22)
        
        # Control name
        cmds.text(label=control_name, align="left", font="plainLabelFont", height=20)
        
        # Channel checkboxes
        cmds.checkBox(label='', value=inversions['tx'], height=20,
                     changeCommand=lambda x, idx=index, ch='tx': self._update_spine_inversion(idx, ch, x))
        cmds.checkBox(label='', value=inversions['ty'], height=20,
                     changeCommand=lambda x, idx=index, ch='ty': self._update_spine_inversion(idx, ch, x))
        cmds.checkBox(label='', value=inversions['tz'], height=20,
                     changeCommand=lambda x, idx=index, ch='tz': self._update_spine_inversion(idx, ch, x))
        cmds.checkBox(label='', value=inversions['rx'], height=20,
                     changeCommand=lambda x, idx=index, ch='rx': self._update_spine_inversion(idx, ch, x))
        
        # RY and RZ with remove button
        cmds.rowLayout(numberOfColumns=3, columnWidth3=(20, 20, 32))
        cmds.checkBox(label='', value=inversions['ry'], height=20,
                     changeCommand=lambda x, idx=index, ch='ry': self._update_spine_inversion(idx, ch, x))
        cmds.checkBox(label='', value=inversions['rz'], height=20,
                     changeCommand=lambda x, idx=index, ch='rz': self._update_spine_inversion(idx, ch, x))
        cmds.button(label="✕", width=30, height=20,
                   command=lambda x, idx=index: self.remove_spine_control(idx),
                   backgroundColor=(0.7, 0.5, 0.5),
                   annotation=f"Remove {control_name}")
        cmds.setParent('..')  # RY RZ X layout
        cmds.setParent('..')  # main row
    
    def _update_spine_inversion(self, index, channel, value):
        """Update inversion setting for a spine control channel."""
        if 0 <= index < len(self.spine_control_inversions):
            self.spine_control_inversions[index][channel] = value

    def clear_all_control_pairs(self, *_):
        """Clear all left/right control pairs."""
        # Clear the data arrays
        self.left_controls.clear()
        self.right_controls.clear()
        self.control_inversions.clear()
        
        # Refresh the UI to remove all rows
        self._refresh_control_pairs_ui()
        print("Cleared all left/right control pairs")



    def _set_all_inversions(self, axis, value):
        """Set the same inversion value for all control pairs for a specific axis."""
        for i in range(len(self.control_inversions)):
            self.control_inversions[i][axis] = value
        self._refresh_control_pairs_ui()
        print(f"Set all {axis} inversions to {value}")

    def _set_all_copy_time_offsets(self, value):
        """Set the same time offset value for all objects in Copy with Offset tab."""
        for i in range(len(self.copy_offset_time_offsets)):
            self.copy_offset_time_offsets[i] = value
        self._refresh_copy_offset_ui()
        print(f"Set all time offsets to {value}")

    def _set_all_copy_value_offsets(self, value):
        """Set the same value offset for all objects in Copy with Offset tab."""
        for i in range(len(self.copy_offset_value_offsets)):
            self.copy_offset_value_offsets[i] = value
        self._refresh_copy_offset_ui()
        print(f"Set all value offsets to {value}")

    def _set_all_copy_channels(self, channel, value):
        """Set the same channel setting for all objects in Copy with Offset tab."""
        for i in range(len(self.copy_offset_channel_settings)):
            self.copy_offset_channel_settings[i][channel] = value
        self._refresh_copy_offset_ui()
        print(f"Set all {channel} channels to {value}")

    def add_selected_copy_objects(self, *_):
        """Add selected objects to the Copy with Offset list."""
        selection = cmds.ls(selection=True)
        if not selection:
            cmds.warning("Please select objects to add to the Copy with Offset list.")
            return
        
        added_count = 0
        for obj in selection:
            if obj not in self.copy_offset_objects:
                # Add object data
                self.copy_offset_objects.append(obj)
                self.copy_offset_time_offsets.append(1)    # Default time offset
                self.copy_offset_value_offsets.append(0.0)  # Default value offset
                
                # Default channel settings - all enabled by default
                self.copy_offset_channel_settings.append({
                    'tx': True, 'ty': True, 'tz': True,
                    'rx': True, 'ry': True, 'rz': True
                })
                added_count += 1
        
        # Refresh UI to show new objects
        self._refresh_copy_offset_ui()
        
        if added_count > 0:
            print(f"Added {added_count} objects to Copy with Offset list")
        else:
            cmds.warning("Selected objects are already in the list.")

    def clear_all_copy_objects(self, *_):
        """Clear all objects from the Copy with Offset list."""
        self.copy_offset_objects.clear()
        self.copy_offset_time_offsets.clear()
        self.copy_offset_value_offsets.clear()
        self.copy_offset_channel_settings.clear()
        
        # Refresh the UI to remove all rows
        self._refresh_copy_offset_ui()
        print("Cleared all Copy with Offset objects")

    def _refresh_copy_offset_ui(self):
        """Refresh the dynamic Copy with Offset objects UI."""
        # Clear existing UI elements
        children = cmds.scrollLayout(self.copy_offset_scroll, query=True, childArray=True) or []
        for child in children:
            cmds.deleteUI(child)
        
        # Set parent to scroll layout
        cmds.setParent(self.copy_offset_scroll)
        cmds.columnLayout(adjustableColumn=True, rowSpacing=3)
        
        # Create rows for each object
        for i, obj in enumerate(self.copy_offset_objects):
            time_offset = self.copy_offset_time_offsets[i] if i < len(self.copy_offset_time_offsets) else 10
            value_offset = self.copy_offset_value_offsets[i] if i < len(self.copy_offset_value_offsets) else 0.0
            channels = self.copy_offset_channel_settings[i] if i < len(self.copy_offset_channel_settings) else {
                'tx': True, 'ty': True, 'tz': True, 'rx': True, 'ry': True, 'rz': True
            }
            
            self._create_copy_offset_row(i, obj, time_offset, value_offset, channels)

    def _create_copy_offset_row(self, index, obj_name, time_offset, value_offset, channels):
        """Create a single object row with offset fields and channel checkboxes."""
        cmds.rowLayout(numberOfColumns=4, columnWidth4=(120, 60, 60, 240))
        
        # Object name (read-only text)
        display_name = obj_name.split(':')[-1] if ':' in obj_name else obj_name
        if len(display_name) > 15:
            display_name = display_name[:12] + "..."
        cmds.text(label=display_name, align="left", annotation=obj_name)
        
        # Time offset field
        time_field = cmds.intField(value=time_offset, width=55,
                                  changeCommand=lambda x, idx=index: self._update_copy_time_offset(idx, x))
        
        # Value offset field
        value_field = cmds.floatField(value=value_offset, width=55, precision=2,
                                     changeCommand=lambda x, idx=index: self._update_copy_value_offset(idx, x))
        
        # Channel checkboxes in nested layout
        cmds.rowLayout(numberOfColumns=6, columnWidth6=(35, 35, 35, 35, 35, 70))
        tx_cb = cmds.checkBox(label='', value=channels['tx'], 
                              changeCommand=lambda x, idx=index, ch='tx': self._update_copy_channel(idx, ch, x))
        ty_cb = cmds.checkBox(label='', value=channels['ty'],
                              changeCommand=lambda x, idx=index, ch='ty': self._update_copy_channel(idx, ch, x))
        tz_cb = cmds.checkBox(label='', value=channels['tz'],
                              changeCommand=lambda x, idx=index, ch='tz': self._update_copy_channel(idx, ch, x))
        rx_cb = cmds.checkBox(label='', value=channels['rx'],
                              changeCommand=lambda x, idx=index, ch='rx': self._update_copy_channel(idx, ch, x))
        ry_cb = cmds.checkBox(label='', value=channels['ry'],
                              changeCommand=lambda x, idx=index, ch='ry': self._update_copy_channel(idx, ch, x))
        
        # RZ checkbox and Remove button in combined column
        cmds.rowLayout(numberOfColumns=2, columnWidth2=(35, 35))
        rz_cb = cmds.checkBox(label='', value=channels['rz'],
                              changeCommand=lambda x, idx=index, ch='rz': self._update_copy_channel(idx, ch, x))
        cmds.button(label="X", width=30,
                    command=lambda x, idx=index: self._remove_copy_object(idx),
                    backgroundColor=(0.7, 0.5, 0.5))  # Red for remove actions
        cmds.setParent('..')  # inner rowLayout (RZ + Remove button)
        cmds.setParent('..')  # channel checkboxes layout
        
        cmds.setParent('..')  # main rowLayout

    def _update_copy_time_offset(self, index, value):
        """Update time offset for a specific copy object."""
        if index < len(self.copy_offset_time_offsets):
            self.copy_offset_time_offsets[index] = value

    def _update_copy_value_offset(self, index, value):
        """Update value offset for a specific copy object."""
        if index < len(self.copy_offset_value_offsets):
            self.copy_offset_value_offsets[index] = value

    def _update_copy_channel(self, index, channel, value):
        """Update channel setting for a specific copy object."""
        if index < len(self.copy_offset_channel_settings):
            self.copy_offset_channel_settings[index][channel] = value

    def _remove_copy_object(self, index):
        """Remove a copy object from the list."""
        if 0 <= index < len(self.copy_offset_objects):
            obj_name = self.copy_offset_objects[index]
            self.copy_offset_objects.pop(index)
            self.copy_offset_time_offsets.pop(index)
            self.copy_offset_value_offsets.pop(index)
            self.copy_offset_channel_settings.pop(index)
            
            # Refresh UI
            self._refresh_copy_offset_ui()
            print(f"Removed {obj_name} from Copy with Offset list")

    def _should_invert_for_spine(self, node_name, attr):
        """True if node matches spine controls list and attr should be asymmetrical (based on forward direction)."""
        spine_controls = self._get_spine_controls()
        if node_name not in spine_controls:
            return False
        
        # Use intelligent channel categorization based on settings
        rotation_axis = self.forward_rotation_axis  # From settings: 'X', 'Y', or 'Z'
        
        # Translation channels: X is always asymmetrical, Y and Z are double cycle
        if attr == 'translateX':
            return True
        if attr in ['translateY', 'translateZ']:
            return False
            
        # Rotation channels based on forward rotation axis:
        # - Forward rotation axis: Double cycle (not inverted)
        # - Other two axes: Asymmetrical (inverted)
        if rotation_axis == 'X':
            return attr in ['rotateY', 'rotateZ']  # Y and Z are asymmetrical
        elif rotation_axis == 'Y':
            return attr in ['rotateX', 'rotateZ']  # X and Z are asymmetrical
        else:  # rotation_axis == 'Z'
            return attr in ['rotateX', 'rotateY']  # X and Y are asymmetrical
            
        return False

    # =========================================================================
    # SECTION 9: WING/PURE MIRROR CONTROLS MANAGEMENT
    # =========================================================================
    
    def add_selected_to_wing_list(self, *_):
        """Add selected controls to the wing controls list as pairs."""
        sel = cmds.ls(selection=True)
        if not sel:
            cmds.warning("No controls selected.")
            return
        
        added_count = 0
        for ctrl in sel:
            # Use full control name (with namespace) for wing controls
            if self.is_left(ctrl):
                right_ctrl = self.get_other_side(ctrl, left_to_right=True)
                if ctrl not in self.wing_left_controls and right_ctrl not in self.wing_right_controls:
                    self.wing_left_controls.append(ctrl)
                    self.wing_right_controls.append(right_ctrl)
                    added_count += 1

            elif self.is_right(ctrl):
                left_ctrl = self.get_other_side(ctrl, left_to_right=False)
                if ctrl not in self.wing_right_controls and left_ctrl not in self.wing_left_controls:
                    self.wing_right_controls.append(ctrl)
                    self.wing_left_controls.append(left_ctrl)
                    added_count += 1

            else:
                # Add as single control (for backward compatibility with old wing list)
                current_items = cmds.textScrollList(self.wing_controls_list, query=True, allItems=True) or []
                if ctrl not in current_items:
                    cmds.textScrollList(self.wing_controls_list, edit=True, append=ctrl)
                    added_count += 1
        
        # Refresh the wing pairs UI
        self._refresh_wing_pairs_ui()

    
    def remove_selected_from_wing_list(self, *_):
        """Remove selected items from the wing controls list."""
        selected_items = cmds.textScrollList(self.wing_controls_list, query=True, selectItem=True) or []
        if not selected_items:
            cmds.warning("No items selected in the wing controls list to remove.")
            return
        
        for item in selected_items:
            cmds.textScrollList(self.wing_controls_list, edit=True, removeItem=item)
        

    
    def clear_wing_list(self, *_):
        """Clear all items from the wing controls list."""
        cmds.textScrollList(self.wing_controls_list, edit=True, removeAll=True)
        # Also clear wing pairs
        self.wing_left_controls = []
        self.wing_right_controls = []
        self.wing_control_inversions = []
        self._refresh_wing_pairs_ui()

    
    def _refresh_wing_pairs_ui(self):
        """Refresh the dynamic wing pairs UI."""
        # Clear existing UI elements
        children = cmds.scrollLayout(self.wing_pairs_scroll, query=True, childArray=True) or []
        for child in children:
            cmds.deleteUI(child)
        
        # Set parent to scroll layout's column
        cmds.setParent(self.wing_pairs_scroll)
        cmds.columnLayout(adjustableColumn=True, rowSpacing=2)
        
        # Add header row
        if self.wing_left_controls:
            cmds.rowLayout(numberOfColumns=4, columnWidth4=(150, 150, 180, 60))
            cmds.text(label="Left Wing", align="center", backgroundColor=(0.3, 0.3, 0.4))
            cmds.text(label="Right Wing", align="center", backgroundColor=(0.4, 0.3, 0.3))
            cmds.text(label="Invert: TX TY TZ RX RY RZ", align="center", backgroundColor=(0.35, 0.35, 0.35))
            cmds.text(label="Action", align="center", backgroundColor=(0.3, 0.35, 0.4))
            cmds.setParent('..')
        
        # Create a row for each wing pair
        for i, (left_ctrl, right_ctrl) in enumerate(zip(self.wing_left_controls, self.wing_right_controls)):
            # Ensure we have inversion data for this pair
            while len(self.wing_control_inversions) <= i:
                # Default wing inversion settings - all unchecked by default
                self.wing_control_inversions.append({
                    'tx': False, 'ty': False, 'tz': False,
                    'rx': False, 'ry': False, 'rz': False
                })
            
            inversion = self.wing_control_inversions[i]
            self._create_wing_pair_row(i, left_ctrl, right_ctrl, inversion)
        
        cmds.setParent('..')  # columnLayout
    
    def _create_wing_pair_row(self, index, left_ctrl, right_ctrl, inversion):
        """Create a single wing pair row with inversion checkboxes."""
        cmds.rowLayout(numberOfColumns=4, columnWidth4=(150, 150, 180, 60))
        
        # Left control (read-only text)
        cmds.text(label=left_ctrl, align="left")
        
        # Right control (read-only text)  
        cmds.text(label=right_ctrl, align="left")
        
        # Inversion checkboxes
        cmds.rowLayout(numberOfColumns=6, columnWidth6=(30, 30, 30, 30, 30, 30))
        tx_cb = cmds.checkBox(label='', value=inversion['tx'], 
                              changeCommand=lambda x, idx=index, axis='tx': self._update_wing_inversion(idx, axis, x))
        ty_cb = cmds.checkBox(label='', value=inversion['ty'],
                              changeCommand=lambda x, idx=index, axis='ty': self._update_wing_inversion(idx, axis, x))
        tz_cb = cmds.checkBox(label='', value=inversion['tz'],
                              changeCommand=lambda x, idx=index, axis='tz': self._update_wing_inversion(idx, axis, x))
        rx_cb = cmds.checkBox(label='', value=inversion['rx'],
                              changeCommand=lambda x, idx=index, axis='rx': self._update_wing_inversion(idx, axis, x))
        ry_cb = cmds.checkBox(label='', value=inversion['ry'],
                              changeCommand=lambda x, idx=index, axis='ry': self._update_wing_inversion(idx, axis, x))
        rz_cb = cmds.checkBox(label='', value=inversion['rz'],
                              changeCommand=lambda x, idx=index, axis='rz': self._update_wing_inversion(idx, axis, x))
        cmds.setParent('..')  # rowLayout (checkboxes)
        
        # Remove button
        cmds.button(label="X", width=30,
                    command=lambda x, idx=index: self._remove_wing_pair(idx),
                    backgroundColor=(0.7, 0.5, 0.5))
        
        cmds.setParent('..')  # rowLayout (main row)
    
    def _update_wing_inversion(self, index, axis, value):
        """Update inversion setting for a specific wing pair and axis."""
        if index < len(self.wing_control_inversions):
            self.wing_control_inversions[index][axis] = value

    
    def _remove_wing_pair(self, index):
        """Remove a wing pair and refresh the UI."""
        if 0 <= index < len(self.wing_left_controls):
            left_ctrl = self.wing_left_controls.pop(index)
            right_ctrl = self.wing_right_controls.pop(index)
            if index < len(self.wing_control_inversions):
                self.wing_control_inversions.pop(index)

            self._refresh_wing_pairs_ui()
    
    def mirror_wing_left_to_right(self, *_):
        """Mirror animation from left wing controls to right wing controls."""
        self._mirror_wing_controls(left_to_right=True)
    
    def mirror_wing_right_to_left(self, *_):
        """Mirror animation from right wing controls to left wing controls."""
        self._mirror_wing_controls(left_to_right=False)
    
    def _mirror_wing_controls(self, left_to_right=True):
        """Mirror wing controls with pure mirroring (offsets set to 0)."""
        wing_controls = cmds.textScrollList(self.wing_controls_list, query=True, allItems=True) or []
        if not wing_controls:
            cmds.warning("No wing controls defined. Add controls to the Wing Controls list first.")
            return

        direction = "Left → Right" if left_to_right else "Right → Left"


        processed = 0
        for control in wing_controls:
            try:
                # Get the opposite side - if control is left, get right; if control is right, get left
                if self.is_left(control):
                    other_control = self.get_other_side(control, left_to_right=True)  # L -> R
                else:
                    other_control = self.get_other_side(control, left_to_right=False)  # R -> L
        
                if other_control and other_control != control:
                    # Determine source and target based on the direction we want
                    if left_to_right:
                        # Left → Right: copy from left control to right control
                        if self.is_left(control):
                            source, target = control, other_control
                        else:
                            source, target = other_control, control
                    else:
                        # Right → Left: copy from right control to left control
                        if self.is_right(control):
                            source, target = control, other_control
                        else:
                            source, target = other_control, control
                    
                    self._copy_with_offset(source, target)
                    processed += 1
                else:
                    print(f"Could not find matching control for {control}")
            except Exception as e:
                print(f"Error mirroring {control}: {e}")

        if processed > 0:
            cmds.inViewMessage(amg=f"Mirrored {processed} wing control(s) {direction}", 
                             pos='midCenter', fade=True)
        else:
            cmds.warning("No wing controls were mirrored. Check control names and pairs.")
    
    def _copy_wing_animation(self, source_ctrl, target_ctrl):
        """Copy animation between wing controls with pure mirroring (no offset)."""
        # Wing controls are stored with their full namespace - use them as-is
        source_full = source_ctrl
        target_full = target_ctrl
        
        if not (cmds.objExists(source_full) and cmds.objExists(target_full)):
            print(f"Wing control not found: {source_full} or {target_full}")
            return
        
        # Get animated attributes from source
        source_keyed_attrs = self._keyed_attributes(source_full)
        if not source_keyed_attrs:
            print(f"No keyed attributes found on source wing control {source_full}")
            return
        
        # Copy each animated attribute
        for attr in source_keyed_attrs:
            source_attr = f"{source_full}.{attr}"
            target_attr = f"{target_full}.{attr}" 
            
            if not self._target_has_attribute(target_full, attr):
                continue
            
            # Get source curve
            source_curve = self._anim_curve_for_attr(source_attr)
            if not source_curve:
                continue
            
            # Copy keys (no offset applied)
            if self._copy_and_paste_keys(source_attr, target_attr, source_curve):
                # Apply successful tangent smoothing and cycle infinity
                self._smooth_cycle_transitions(target_attr)
                self._apply_cycle_infinity(target_attr)
                print(f"Mirrored wing animation: {source_attr} → {target_attr}")
        

    def _playback_cycle_range(self):
        """Return (start, end, mid) from playback options, fallback to (0,40,20)."""
        try:
            start = float(cmds.playbackOptions(query=True, min=True))
            end = float(cmds.playbackOptions(query=True, max=True))
        except Exception:
            start, end = 0.0, 40.0
        if end <= start:
            end = start + 40.0
        mid = (start + end) / 2.0
        return start, end, mid

    def _has_key_at(self, plug, t):
        """Return True if there's a key on plug at time t."""
        try:
            times = cmds.keyframe(plug, query=True, time=(t, t), timeChange=True) or []
            return any(abs(tt - t) < 1e-4 for tt in times)
        except Exception:
            return False

    def _ensure_key(self, plug, t, value=None):
        """Ensure a key exists at time t with a given value (or current eval if None)."""
        try:
            if value is None:
                value = cmds.getAttr(plug, time=t)
            cmds.setKeyframe(plug, time=t, value=value)
        except Exception:
            pass

    def _rebuild_second_half_antiphase(self, plug, start, mid, end):
        """Make [mid,end] equal to the negative of [start,mid] for the given plug."""
        # Validate that there are keyframes to work with
        try:
            all_keyframes = cmds.keyframe(plug, query=True, timeChange=True) or []
            if not all_keyframes:
                cmds.warning(f"No keyframes found on {plug}. Cannot perform antiphase operation.")
                return
            
            # Check if there are any keyframes in the first half to copy from
            first_half_keys = [t for t in all_keyframes if start <= t < mid]
            if not first_half_keys:
                cmds.warning(f"No keyframes found in first half [{start}, {mid}) on {plug}. Cannot perform antiphase operation.")
                return
                
        except Exception as e:
            cmds.warning(f"Error checking keyframes on {plug}: {e}")
            return
            
        # Anchor values
        try:
            v_start = cmds.getAttr(plug, time=start)
        except Exception:
            v_start = None
        if not self._has_key_at(plug, start):
            self._ensure_key(plug, start, v_start)
        if not self._has_key_at(plug, mid):
            # Create a temp key at mid to aid paste alignment
            self._ensure_key(plug, mid, v_start if v_start is not None else None)

        # Unlock if needed
        relock = False
        try:
            if cmds.getAttr(plug, lock=True):
                relock = True
                cmds.setAttr(plug, lock=False)
        except Exception:
            pass

        # Clear second half
        try:
            cmds.cutKey(plug, time=(mid, end))
        except Exception:
            pass

        # Copy first half [start, mid) and paste to [mid, end)
        try:
            cmds.copyKey(plug, time=(start, mid), includeUpperBound=False)
        except Exception as e:
            cmds.warning(f"copyKey failed on {plug} [{start},{mid}): {e}")
            return
        try:
            # Merge to avoid wiping existing keys in the first half
            cmds.pasteKey(plug, option='merge', timeOffset=(mid - start))
        except Exception as e:
            # Fallback minimal paste
            try:
                cmds.pasteKey(plug, option='merge')
            except Exception as e2:
                cmds.warning(f"pasteKey failed on {plug}: {e2}")
                return

        # Negate pasted second half
        try:
            cmds.scaleKey(plug, time=(mid, end), valueScale=-1.0)
        except Exception as e:
            cmds.warning(f"scaleKey invert failed on {plug}: {e}")

        # Enforce anchors for proper antiphase symmetry
        try:
            if v_start is None:
                v_start = cmds.getAttr(plug, time=start)
        except Exception:
            v_start = 0.0
        
        # For proper antiphase cycles: start and end have same value, midpoint is inverse
        # This creates perfect symmetrical inversion where mid is opposite of start/end
        self._ensure_key(plug, mid, float(-v_start))
        self._ensure_key(plug, end, float(v_start))

        # Apply tangent smoothing for spine antiphase cycles
        self._smooth_spine_transitions(plug, start, mid, end, is_antiphase=True)
        
        # Apply cycle infinity for seamless looping
        self._apply_cycle_infinity(plug)

        # Relock
        if relock:
            try:
                cmds.setAttr(plug, lock=True)
            except Exception:
                pass

    def _ensure_two_keys(self, curve):
        """Ensure the given curve has at least two keys."""
        try:
            key_times = cmds.keyframe(curve, query=True, timeChange=True) or []
            if len(key_times) < 2:
                value = cmds.keyframe(curve, query=True, valueChange=True)[0]
                playback_start = cmds.playbackOptions(query=True, min=True)
                playback_end = cmds.playbackOptions(query=True, max=True)
                cmds.setKeyframe(curve, time=playback_start, value=value)
                cmds.setKeyframe(curve, time=playback_end, value=value)
        except Exception:
            pass

    # =========================================================================
    # SECTION 6: ANIMATION CORE FUNCTIONS
    # =========================================================================

    def get_key_options(self):
        """Get common key options for copy/paste operations."""
        # Calculate time offset as half the cycle length (time range)
        try:
            start_time = cmds.playbackOptions(query=True, min=True)
            end_time = cmds.playbackOptions(query=True, max=True)
            time_offset = (end_time - start_time) / 2.0
        except Exception:
            time_offset = 20  # Default fallback
        
        return {
            "option": "replaceCompletely",
            "copies": 1,
            "timeOffset": time_offset,
            # Only include flags supported by pasteKey
        }

    def copy_keys(self, source_ctrl, target_ctrl):
        """Copy keys from source to target control with auto-inversion and infinity handling."""
        # Validate and get full control names
        source_full, target_full = self._get_full_control_names(source_ctrl, target_ctrl)
        if not source_full or not target_full:
            return
            
        # Safety check: don't copy to same control
        if source_full == target_full:
            cmds.warning(f"Source and target resolve to the same node '{source_full}'. Skipping.")
            return
        
        if not (cmds.objExists(source_full) and cmds.objExists(target_full)):
            cmds.warning(f"Control not found: {source_full} or {target_full}")
            return
            
        # Get animated attributes and copy each one
        source_keyed_attrs = self._keyed_attributes(source_full)
        if not source_keyed_attrs:
            cmds.warning(f"No keyed attributes found on source {source_full}.")
            return
            
        copied_any = False
        for attr in source_keyed_attrs:
            if self._copy_single_attribute(source_full, target_full, attr, source_ctrl, target_ctrl):
                copied_any = True
                
        if not copied_any:
            cmds.warning(f"No matching attributes on target {target_full} for source keyed attributes: {source_keyed_attrs}")

    def _get_full_control_names(self, source_ctrl, target_ctrl):
        """Get full control names including prefix."""
        prefix = cmds.textField(self.prefix_field, query=True, text=True)
        source_full = f"{prefix}{source_ctrl}" if not source_ctrl.startswith(prefix) else source_ctrl
        target_full = f"{prefix}{target_ctrl}" if not target_ctrl.startswith(prefix) else target_ctrl
        return source_full, target_full
        
    def _copy_single_attribute(self, source_full, target_full, attr, source_ctrl, target_ctrl):
        """Copy animation for a single attribute from source to target."""
        source_attr = f"{source_full}.{attr}"
        target_attr = f"{target_full}.{attr}"
        
        # Skip if target doesn't have this attribute
        if not self._target_has_attribute(target_full, attr):
            return False
            
        # Get source animation curve
        source_curve = self._anim_curve_for_attr(source_attr)
        if not source_curve:
            return False
            
        # Copy and paste the keys
        if not self._copy_and_paste_keys(source_attr, target_attr, source_curve):
            return False
            
        # Apply post-processing (inversion, infinity)
        self._apply_post_processing(target_attr, attr, source_ctrl, target_ctrl, source_curve)
        return True
        
    def _target_has_attribute(self, target_full, attr):
        """Check if target control has the specified attribute."""
        try:
            return cmds.attributeQuery(attr, node=target_full, exists=True)
        except Exception:
            return False
            
    def _copy_and_paste_keys(self, source_attr, target_attr, source_curve):
        """Copy keys from source to target attribute."""
        # Get time range
        time_range = cmds.keyframe(source_curve, query=True, timeChange=True)
        if not time_range:
            return False
            
        start_t = min(time_range)
        end_t = max(time_range)
        
        # Copy keys from source
        try:
            cmds.copyKey(source_attr, time=(start_t, end_t), includeUpperBound=True)
        except Exception as e:
            cmds.warning(f"copyKey failed on {source_attr}: {e}")
            return False
            
        # Handle locked attributes
        relock = self._handle_attribute_lock(target_attr, unlock=True)
        
        # Paste keys with fallback
        paste_success = self._paste_keys_with_fallback(target_attr)
        
        # Restore lock state
        if relock:
            self._handle_attribute_lock(target_attr, lock=True)
            
        return paste_success
    
    def _copy_with_offset(self, source_ctrl, target_ctrl, time_offset=0, value_offset=0.0):
        """Copy animation between controls with specified time and value offsets."""
        source_full = source_ctrl
        target_full = target_ctrl

        if not (cmds.objExists(source_full) and cmds.objExists(target_full)):
            print(f"Control not found: {source_full} or {target_full}")
            return

        # Get keyed attributes first
        source_keyed_attrs = self._keyed_attributes(source_full)
        
        # If no keyed attributes, get all animatable attributes and copy current values
        if not source_keyed_attrs:

            self._copy_current_values(source_full, target_full, time_offset, value_offset)
            return

        # First normalize source curves to fit timeline range
        print(f"DEBUG: Normalizing source curves for {source_full}")
        self._normalize_curves_to_timeline(source_full, source_keyed_attrs)

        # Copy keyed animation
        for attr in source_keyed_attrs:
            source_attr = f"{source_full}.{attr}"
            target_attr = f"{target_full}.{attr}"

            if not self._target_has_attribute(target_full, attr):
                continue

            source_curve = self._anim_curve_for_attr(source_attr)
            if not source_curve:
                continue

            if self._copy_and_paste_keys_with_offset(source_attr, target_attr, source_curve, time_offset, value_offset):
                # Apply wing control specific post-processing (always invert X for wings)
                self._apply_wing_post_processing(target_attr, attr, source_full, target_full, source_curve)
                
                # Set infinity to cycle for Copy with Offset functionality - ensure it's applied
                self._apply_cycle_infinity(target_attr)
                
                # Timeline fitting disabled - cycle infinity handles offset curves properly
                # Keyframes can extend beyond timeline when using cycle infinity

    
    def _smooth_cycle_transitions(self, target_attr):
        """Simple but effective tangent smoothing for cycle continuity."""
        try:
            # Get all keyframes for this attribute
            keyframes = cmds.keyframe(target_attr, query=True, timeChange=True)
            if not keyframes or len(keyframes) < 2:
                return
            
            keyframes = sorted(keyframes)
            first_time = keyframes[0]
            last_time = keyframes[-1]
            
            print(f"DEBUG: Smoothing cycle for {target_attr}: {len(keyframes)} keys")
            
            # DEBUG: Check tangent types BEFORE smoothing
            in_tangents = cmds.keyTangent(target_attr, query=True, inTangentType=True)
            out_tangents = cmds.keyTangent(target_attr, query=True, outTangentType=True)
            print(f"DEBUG: Before smoothing - in tangents: {in_tangents[:min(3, len(in_tangents))]}")
            print(f"DEBUG: Before smoothing - out tangents: {out_tangents[:min(3, len(out_tangents))]}")
            
            # Special case: 3 keys (beginning, middle, end) should all be flat
            if len(keyframes) == 3:
                print(f"DEBUG: 3-key cycle detected - applying flat tangents for smooth motion")
                for time in keyframes:
                    cmds.keyTangent(target_attr, time=(time,), edit=True,
                                   inTangentType='flat', outTangentType='flat')
                return
            
            # Simple and effective: just preserve existing tangent quality
            # Don't overthink it - if the original curve had good tangents, keep them
            # Only fix the cycle boundaries for seamless looping
            if len(keyframes) >= 3:
                # For cycle continuity, make first and last keyframes have matching tangents
                # But use the EXISTING tangent style, don't force new calculations
                
                # Get the current tangent at the first keyframe's out tangent
                first_out_tangent = cmds.keyTangent(target_attr, time=(first_time,), query=True, outTangentType=True)[0]
                last_in_tangent = cmds.keyTangent(target_attr, time=(last_time,), query=True, inTangentType=True)[0]
                
                # If they're already good tangent types, just ensure they match
                if first_out_tangent in ['spline', 'linear', 'auto'] and last_in_tangent in ['spline', 'linear', 'auto']:
                    # Keep the better tangent type for both boundaries
                    better_tangent = 'spline' if 'spline' in [first_out_tangent, last_in_tangent] else first_out_tangent
                    
                    cmds.keyTangent(target_attr, time=(first_time,), edit=True, outTangentType=better_tangent)
                    cmds.keyTangent(target_attr, time=(last_time,), edit=True, inTangentType=better_tangent)
                    
                    print(f"DEBUG: Simple cycle fix - using {better_tangent} tangents for boundaries")
            
            # Leave middle keyframes completely alone - they're fine as they are
            
            print(f"DEBUG: Applied cycle smoothing to {target_attr}")
            
            # DEBUG: Check final tangent types AFTER smoothing
            final_in_tangents = cmds.keyTangent(target_attr, query=True, inTangentType=True)
            final_out_tangents = cmds.keyTangent(target_attr, query=True, outTangentType=True)
            print(f"DEBUG: After smoothing - in tangents: {final_in_tangents[:min(3, len(final_in_tangents))]}")
            print(f"DEBUG: After smoothing - out tangents: {final_out_tangents[:min(3, len(final_out_tangents))]}")
                
        except Exception as e:
            print(f"DEBUG: Tangent smoothing failed for {target_attr}: {e}")
            # Fallback to spline
            try:
                cmds.keyTangent(target_attr, edit=True, inTangentType='spline', outTangentType='spline')
                print(f"DEBUG: Applied fallback spline smoothing to {target_attr}")
            except Exception as e2:
                pass


    def _smooth_spine_transitions(self, plug, start, mid, end, is_antiphase=False):
        """Advanced tangent smoothing for spine cycles with special handling for antiphase."""
        try:
            print(f"DEBUG: Smoothing spine transitions for {plug} ({'antiphase' if is_antiphase else 'standard'} cycle)")
            
            # Get all keyframes in the range
            keyframes = cmds.keyframe(plug, query=True, timeChange=True)
            if not keyframes or len(keyframes) < 3:
                return
            
            # Filter keyframes to our cycle range
            cycle_keys = [k for k in keyframes if start <= k <= end]
            cycle_keys = sorted(cycle_keys)
            
            if len(cycle_keys) < 3:
                return
            
            import math
            
            # For antiphase cycles: smooth the transition at mid point (where phase flips)
            if is_antiphase:
                # Find keyframe closest to mid point
                mid_key = min(cycle_keys, key=lambda x: abs(x - mid))
                mid_idx = cycle_keys.index(mid_key)
                
                if mid_idx > 0 and mid_idx < len(cycle_keys) - 1:
                    # Get surrounding keyframes
                    prev_time = cycle_keys[mid_idx - 1]
                    next_time = cycle_keys[mid_idx + 1]
                    
                    # Get values
                    prev_value = cmds.keyframe(plug, time=(prev_time,), query=True, valueChange=True)[0]
                    mid_value = cmds.keyframe(plug, time=(mid_key,), query=True, valueChange=True)[0]
                    next_value = cmds.keyframe(plug, time=(next_time,), query=True, valueChange=True)[0]
                    
                    # For antiphase, we want smooth transition through zero
                    # Calculate gentle slope that maintains the antiphase relationship
                    pre_slope = (mid_value - prev_value) / (mid_key - prev_time)
                    post_slope = (next_value - mid_value) / (next_time - mid_key)
                    
                    # Average the slopes for smoother transition
                    avg_slope = (pre_slope + post_slope) / 2.0
                    avg_angle = math.degrees(math.atan(avg_slope))
                    
                    # Apply gentle tangents at the phase transition point
                    cmds.keyTangent(plug, time=(mid_key,), edit=True,
                                   inTangentType='fixed', inAngle=avg_angle, inWeight=0.5,
                                   outTangentType='fixed', outAngle=avg_angle, outWeight=0.5)
            
            # For both types: smooth the cycle boundary (start/end points)
            start_key = cycle_keys[0]
            end_key = cycle_keys[-1]
            
            # Get values at boundaries
            start_value = cmds.keyframe(plug, time=(start_key,), query=True, valueChange=True)[0]
            end_value = cmds.keyframe(plug, time=(end_key,), query=True, valueChange=True)[0]
            
            # Calculate natural derivative for cycle continuity
            if len(cycle_keys) >= 3:
                second_key = cycle_keys[1]
                second_value = cmds.keyframe(plug, time=(second_key,), query=True, valueChange=True)[0]
                
                # Natural slope from start to second keyframe
                natural_slope = (second_value - start_value) / (second_key - start_key)
                natural_angle = math.degrees(math.atan(natural_slope))
                
                # Apply matching tangents at cycle boundaries for seamless looping
                cmds.keyTangent(plug, time=(start_key,), edit=True,
                               outTangentType='fixed', outAngle=natural_angle, outWeight=0.4)
                cmds.keyTangent(plug, time=(end_key,), edit=True,
                               inTangentType='fixed', inAngle=natural_angle, inWeight=0.4)
            
            # Apply spline smoothing to intermediate keyframes
            for i, key_time in enumerate(cycle_keys[1:-1], 1):
                if is_antiphase and abs(key_time - mid) < 0.1:
                    continue  # Skip the mid key as we handled it specially
                    
                cmds.keyTangent(plug, time=(key_time,), edit=True,
                               inTangentType='spline', outTangentType='spline')
            
            print(f"DEBUG: Applied spine tangent smoothing to {plug}")
                
        except Exception as e:
            print(f"DEBUG: Spine tangent smoothing failed for {plug}: {e}")

    def _apply_cycle_infinity(self, target_attr):
        """Apply cycle infinity to target attribute with reliable fallback methods."""
        print(f"DEBUG: Attempting to set cycle infinity on: {target_attr}")
        
        # Get the animation curve first (smoothing is done separately now)
        anim_curve = self._anim_curve_for_attr(target_attr)
        if not anim_curve:
            print(f"DEBUG: No animation curve found for {target_attr}")
            return
        
        print(f"DEBUG: Found animation curve: {anim_curve}")
        
        # Method 1: Try selecting keys and using MEL (most reliable)
        try:
            import maya.mel as mel
            print(f"DEBUG: Method 1 - Selecting keys and using MEL")
            
            # Select all keys on this attribute
            cmds.selectKey(target_attr, clear=True)
            cmds.selectKey(target_attr, add=True)
            
            # Use MEL setInfinity command
            mel.eval('setInfinity -pri "cycle" -poi "cycle";')
            
            print(f"DEBUG: Method 1 completed - MEL setInfinity executed")
            
        except Exception as e:
            print(f"DEBUG: Method 1 (MEL) failed: {e}")
            
            # Method 2: Direct attribute setting on animation curve
            try:
                print(f"DEBUG: Method 2 - Direct attribute setting on curve")
                cmds.setAttr(f"{anim_curve}.preInfinity", 3)
                cmds.setAttr(f"{anim_curve}.postInfinity", 3)
                print(f"DEBUG: Method 2 completed - Direct setAttr on curve")
                
            except Exception as e2:
                print(f"DEBUG: Method 2 (setAttr) failed: {e2}")
                
                # Method 3: Original cmds.setInfinity approach
                try:
                    print(f"DEBUG: Method 3 - Original cmds.setInfinity")
                    cmds.setInfinity(target_attr, preInfinite=3, postInfinite=3)
                    print(f"DEBUG: Method 3 completed - cmds.setInfinity executed")
                    
                except Exception as e3:
                    print(f"DEBUG: Method 3 failed: {e3}")
                    cmds.warning(f"All methods failed to set cycle infinity on {target_attr}")
        
        # Verify what was actually set by checking the animation curve
        try:
            # Get the animation curve for this attribute
            anim_curve = self._anim_curve_for_attr(target_attr)
            if anim_curve:
                pre_inf = cmds.getAttr(f"{anim_curve}.preInfinity")
                post_inf = cmds.getAttr(f"{anim_curve}.postInfinity")
                print(f"DEBUG: Verification - {anim_curve} preInfinity: {pre_inf}, postInfinity: {post_inf}")
                
                # Check if the values are what we expect (3 for cycle)
                if pre_inf == 3 and post_inf == 3:
                    print(f"DEBUG: SUCCESS - Cycle infinity correctly set on {target_attr}")
                else:
                    print(f"DEBUG: WARNING - Expected 3,3 but got {pre_inf},{post_inf} on {target_attr}")
            else:
                print(f"DEBUG: No animation curve found for {target_attr} - infinity not applicable")
        except Exception as e:
            print(f"DEBUG: Could not verify infinity settings: {e}")

    def _copy_current_values(self, source_ctrl, target_ctrl, time_offset=0, value_offset=0.0):
        """Copy current channel values from source to target control with mirroring logic."""
        # Common animatable attributes for transforms
        attrs_to_copy = ['translateX', 'translateY', 'translateZ', 
                        'rotateX', 'rotateY', 'rotateZ',
                        'scaleX', 'scaleY', 'scaleZ']
        
        copied_count = 0
        for attr in attrs_to_copy:
            source_attr = f"{source_ctrl}.{attr}"
            target_attr = f"{target_ctrl}.{attr}"
            
            # Check if both controls have this attribute
            if (self._target_has_attribute(source_ctrl, attr) and 
                self._target_has_attribute(target_ctrl, attr)):
                
                try:
                    # Get current value from source
                    current_value = cmds.getAttr(source_attr)
                    
                    # Apply mirroring logic - check if X-axis inversion is needed
                    final_value = current_value + value_offset
                    
                    # Apply axis inversion for translateX, rotateY, and rotateZ if this is a left<->right pair
                    if (attr in ['translateX', 'rotateY', 'rotateZ']) and self.auto_detect_x_inversion:
                        source_is_left = self.is_left(source_ctrl)
                        source_is_right = self.is_right(source_ctrl)
                        target_is_left = self.is_left(target_ctrl)
                        target_is_right = self.is_right(target_ctrl)
                        

                        
                        # Check if this is a left<->right pair
                        if (source_is_left and target_is_right) or (source_is_right and target_is_left):

                            # For wing controls, always apply axis inversion for proper mirroring
                            final_value = -final_value

                        else:
                            pass
                    
                    # Handle locked attributes
                    relock = self._handle_attribute_lock(target_attr, unlock=True)
                    
                    # Set the value on target
                    cmds.setAttr(target_attr, final_value)
                    
                    # Create a keyframe to enable infinity settings for Copy with Offset
                    try:
                        cmds.setKeyframe(target_attr)
                        # Apply cycle infinity for Copy with Offset functionality
                        self._apply_cycle_infinity(target_attr)
                    except Exception:
                        pass  # If keyframe creation fails, continue without infinity
                    
                    # Restore lock state
                    if relock:
                        self._handle_attribute_lock(target_attr, lock=True)
                    

                    copied_count += 1
                    
                except Exception as e:
                    print(f"Failed to copy current value for {attr}: {e}")
        

    
    def _apply_wing_post_processing(self, target_attr, attr, source_ctrl, target_ctrl, source_curve):
        """Apply wing-specific post-processing (always invert translateX and rotateZ for proper mirroring)."""
        # Apply axis inversion for translateX, rotateY, and rotateZ in wing controls (always invert for proper mirroring)
        if attr in ['translateX', 'rotateY', 'rotateZ']:
            source_is_left = self.is_left(source_ctrl)
            source_is_right = self.is_right(source_ctrl)
            target_is_left = self.is_left(target_ctrl)
            target_is_right = self.is_right(target_ctrl)
            
            # Check if this is a left<->right pair
            if (source_is_left and target_is_right) or (source_is_right and target_is_left):

                cmds.scaleKey(target_attr, valueScale=-1.0)

            
        # Apply successful tangent smoothing and cycle infinity
        self._smooth_cycle_transitions(target_attr)
        self._apply_cycle_infinity(target_attr)
    
    def _copy_and_paste_keys_with_offset(self, source_attr, target_attr, source_curve, time_offset=0, value_offset=0.0):
        """Copy keys from source to target attribute with time and value offsets."""
        # Get time range
        time_range = cmds.keyframe(source_curve, query=True, timeChange=True)
        if not time_range:
            return False
            
        start_t = min(time_range)
        end_t = max(time_range)
        
        # Copy keys from source
        try:
            cmds.copyKey(source_attr, time=(start_t, end_t), includeUpperBound=True)
        except Exception as e:
            cmds.warning(f"copyKey failed on {source_attr}: {e}")
            return False
            
        # Handle locked attributes
        relock = self._handle_attribute_lock(target_attr, unlock=True)
        
        # Paste keys with offset
        paste_success = self._paste_keys_with_offset(target_attr, time_offset, value_offset)
        
        # Restore lock state
        if relock:
            self._handle_attribute_lock(target_attr, lock=True)
            
        return paste_success
    
    def _paste_keys_with_offset(self, target_attr, time_offset=0, value_offset=0.0):
        """Paste keys with time and value offsets."""
        # Clear existing keys first to ensure complete replacement
        self._clear_existing_keys(target_attr)
        
        try:
            paste_opts = {'option': 'replaceCompletely'}
            if time_offset != 0:
                paste_opts['timeOffset'] = time_offset
            if value_offset != 0.0:
                paste_opts['valueOffset'] = value_offset
                
            cmds.pasteKey(target_attr, **paste_opts)
            cmds.refresh()  # Allow Maya to process
            return True
        except Exception as e:
            cmds.warning(f"pasteKey with offset failed on {target_attr}: {e}")
            return False
            
    def _fit_curve_to_timeline(self, target_attr, time_offset):
        """Fit offset curves to timeline range by wrapping overhanging keys while preserving timing."""
        try:
            # Get current timeline range
            start_time = cmds.playbackOptions(query=True, minTime=True)
            end_time = cmds.playbackOptions(query=True, maxTime=True)
            timeline_duration = end_time - start_time
            
            # Get current keyframes on the curve
            keyframes = cmds.keyframe(target_attr, query=True, timeChange=True)
            if not keyframes:
                return
                
            keyframes = sorted(keyframes)
            first_key_time = keyframes[0]
            last_key_time = keyframes[-1]
            
            print(f"DEBUG: Timeline fitting - range [{start_time}, {end_time}], keys [{first_key_time}, {last_key_time}]")
            
            # Check if keys extend beyond timeline
            keys_before_start = [t for t in keyframes if t < start_time]
            keys_after_end = [t for t in keyframes if t > end_time]
            
            if keys_before_start or keys_after_end:
                print(f"DEBUG: Found keys outside timeline - before: {len(keys_before_start)}, after: {len(keys_after_end)}")
                
                # Simple approach: wrap overhanging keys to the opposite end of timeline
                # This preserves the original keyframe timing and values
                
                if keys_after_end:
                    # Move keys that are past the end to the beginning
                    for key_time in keys_after_end:
                        # Get the key's value and tangent info
                        key_value = cmds.keyframe(target_attr, time=(key_time,), query=True, valueChange=True)[0]
                        in_tangent = cmds.keyTangent(target_attr, time=(key_time,), query=True, inTangentType=True)[0]
                        out_tangent = cmds.keyTangent(target_attr, time=(key_time,), query=True, outTangentType=True)[0]
                        
                        # Calculate where this key should go at the beginning
                        # Wrap it around to the start of timeline
                        offset_from_end = key_time - end_time
                        new_time = start_time + offset_from_end
                        
                        # Only move if the new position doesn't conflict with existing keys
                        if new_time <= end_time:
                            # Remove the old key
                            cmds.cutKey(target_attr, time=(key_time, key_time))
                            
                            # Set new key at wrapped position
                            cmds.setKeyframe(target_attr, time=new_time, value=key_value)
                            
                            # Restore tangent types
                            cmds.keyTangent(target_attr, time=(new_time,), edit=True,
                                          inTangentType=in_tangent, outTangentType=out_tangent)
                            
                            print(f"DEBUG: Wrapped key from {key_time:.1f} to {new_time:.1f}")
                
                if keys_before_start:
                    # Move keys that are before the start to the end
                    for key_time in keys_before_start:
                        # Get the key's value and tangent info
                        key_value = cmds.keyframe(target_attr, time=(key_time,), query=True, valueChange=True)[0]
                        in_tangent = cmds.keyTangent(target_attr, time=(key_time,), query=True, inTangentType=True)[0]
                        out_tangent = cmds.keyTangent(target_attr, time=(key_time,), query=True, outTangentType=True)[0]
                        
                        # Calculate where this key should go at the end
                        offset_from_start = start_time - key_time
                        new_time = end_time - offset_from_start
                        
                        # Only move if the new position doesn't conflict with existing keys
                        if new_time >= start_time:
                            # Remove the old key
                            cmds.cutKey(target_attr, time=(key_time, key_time))
                            
                            # Set new key at wrapped position
                            cmds.setKeyframe(target_attr, time=new_time, value=key_value)
                            
                            # Restore tangent types
                            cmds.keyTangent(target_attr, time=(new_time,), edit=True,
                                          inTangentType=in_tangent, outTangentType=out_tangent)
                            
                            print(f"DEBUG: Wrapped key from {key_time:.1f} to {new_time:.1f}")
                
                print(f"DEBUG: Timeline fitting completed - keys now wrapped within [{start_time}, {end_time}]")
                
                # Ensure cycle infinity is maintained after the reorganization
                self._apply_cycle_infinity(target_attr)
                
        except Exception as e:
            print(f"DEBUG: Timeline fitting failed for {target_attr}: {e}")
            
    def _normalize_curves_to_timeline(self, control_name, keyed_attrs):
        """Shift source curves to start at timeline beginning without changing shape."""
        try:
            # Get current timeline range
            start_time = cmds.playbackOptions(query=True, minTime=True)
            end_time = cmds.playbackOptions(query=True, maxTime=True)
            
            for attr in keyed_attrs:
                source_attr = f"{control_name}.{attr}"
                
                # Get current keyframes
                keyframes = cmds.keyframe(source_attr, query=True, timeChange=True)
                if not keyframes or len(keyframes) < 2:
                    continue
                    
                keyframes = sorted(keyframes)
                first_key_time = keyframes[0]
                last_key_time = keyframes[-1]
                
                # Check if ANY keys are outside the timeline range (not just first key)
                keys_outside = any(k < start_time or k > end_time for k in keyframes)
                
                if keys_outside or abs(first_key_time - start_time) > 0.001:
                    print(f"DEBUG: Keys outside timeline detected for {source_attr}")
                    print(f"DEBUG: Current range [{first_key_time:.1f}, {last_key_time:.1f}], timeline [{start_time}, {end_time}]")
                    
                    # Simple shift: move all keyframes so first key is at timeline start
                    time_shift = start_time - first_key_time
                    
                    print(f"DEBUG: Applying time shift {time_shift:.1f} to {source_attr}")
                    
                    # Apply time shift - this preserves exact curve shape and timing
                    cmds.keyframe(source_attr, edit=True, timeChange=time_shift, relative=True)
                    
                    # Verify the shift worked
                    new_keyframes = cmds.keyframe(source_attr, query=True, timeChange=True)
                    if new_keyframes:
                        new_first = min(new_keyframes)
                        new_last = max(new_keyframes)
                        print(f"DEBUG: After shift - curve spans [{new_first:.1f}, {new_last:.1f}]")
                        
                        # Double-check if there are still keys outside timeline
                        still_outside = any(k < start_time - 0.001 or k > end_time + 0.001 for k in new_keyframes)
                        if still_outside:
                            print(f"WARNING: Some keys still outside timeline after shift!")
                        else:
                            print(f"SUCCESS: All keys now within timeline range")
                    
                    # Ensure cycle infinity is maintained
                    self._apply_cycle_infinity(source_attr)
                else:
                    print(f"DEBUG: {source_attr} already within timeline range - no shift needed")
                    
        except Exception as e:
            print(f"DEBUG: Curve normalization failed for {control_name}: {e}")
        
    def _handle_attribute_lock(self, attr, unlock=False, lock=False):
        """Handle locking/unlocking of attributes. Returns True if attribute was locked."""
        try:
            is_locked = cmds.getAttr(attr, lock=True)
            if unlock and is_locked:
                cmds.setAttr(attr, lock=False)
                return True
            elif lock:
                cmds.setAttr(attr, lock=True)
        except Exception:
            pass
        return False
        
    def _clear_existing_keys(self, target_attr):
        """Clear all existing keyframes from the target attribute to ensure complete replacement."""
        try:
            # Check if attribute has keyframes
            if cmds.keyframe(target_attr, query=True, keyframeCount=True):
                cmds.cutKey(target_attr, clear=True)
        except Exception:
            # Attribute might not have keys or might not exist
            pass
    
    def _paste_keys_with_fallback(self, target_attr):
        """Paste keys with fallback options."""
        # Clear existing keys first to ensure complete replacement
        self._clear_existing_keys(target_attr)
        
        paste_opts = self.get_key_options()
        
        # Primary paste attempt
        try:
            cmds.pasteKey(target_attr, **paste_opts)
            cmds.refresh()  # Allow Maya to process
            return True
        except Exception as e:
            cmds.warning(f"pasteKey failed on {target_attr}: {e}")
            
        # Fallback paste attempt
        try:
            cmds.pasteKey(target_attr, option='replaceCompletely')
            cmds.refresh()
            return True
        except Exception as e2:
            cmds.warning(f"pasteKey fallback failed on {target_attr}: {e2}")
            return False
            
    def _apply_post_processing(self, target_attr, attr, source_ctrl, target_ctrl, source_curve):
        """Apply X-axis inversion and infinity settings after key paste."""
        # Apply auto-inversion for translateX
        if self.auto_detect_x_inversion and attr == 'translateX':
            self._apply_auto_x_inversion(target_attr, source_ctrl, target_ctrl)
            
        # Apply infinity settings
        self._apply_infinity_to_target(target_attr, source_curve)
        
    def _apply_auto_x_inversion(self, target_attr, source_ctrl, target_ctrl):
        """Apply automatic X-axis inversion if needed."""
        try:
            # Check if this is a left<->right pair
            source_is_left = self.is_left(source_ctrl)
            source_is_right = self.is_right(source_ctrl)
            target_is_left = self.is_left(target_ctrl)
            target_is_right = self.is_right(target_ctrl)
            
            if not ((source_is_left and target_is_right) or (source_is_right and target_is_left)):
                return  # Not a left<->right pair
                
            # Detect and apply inversion if needed
            inversion_needed = self.detect_x_inversion_needed(source_ctrl, target_ctrl)
            if inversion_needed:
                cmds.scaleKey(target_attr, valueScale=-1.0)
                print(f"Applied X-axis inversion to {target_attr}")
            else:
                print(f"No X-axis inversion needed for {target_attr}")
                
        except Exception as e:
            cmds.warning(f"Auto-inversion detection failed for {target_attr}: {e}")
            
    def _apply_infinity_to_target(self, target_attr, source_curve):
        """Apply infinity settings and tangent smoothing to target attribute curves."""
        target_curves = self._find_target_curves(target_attr)
        if not target_curves:
            print(f"DEBUG: WARNING - No curves found for {target_attr}")
            return
            
        # Force cycle infinity is now always enabled by default
        force_cycle = True
            
        if force_cycle:
            self._apply_cycle_infinity_mel(target_curves)
        else:
            for target_curve in target_curves:
                self._apply_infinity_from_source(source_curve, target_curve)
        
        # Apply tangent smoothing for seamless cycling
        self._apply_tangent_smoothing_to_curves(target_curves)
    
    def _apply_tangent_smoothing_to_curves(self, curves):
        """Apply tangent smoothing to curves using their full time range."""
        if not curves:
            return
            
        for curve in curves:
            if not curve or not cmds.objExists(curve):
                continue
                
            try:
                # Get the full time range of this curve
                key_times = cmds.keyframe(curve, query=True, timeChange=True) or []
                if len(key_times) < 2:
                    continue
                    
                start_time = min(key_times)
                end_time = max(key_times)
                
                # Apply smooth cycle tangents
                self._ensure_smooth_cycle_tangents([curve], start_time, end_time)
                
            except Exception as e:
                print(f"DEBUG: Error applying tangent smoothing to {curve}: {e}")
                
    def _find_target_curves(self, target_attr):
        """Find animation curves connected to target attribute using multiple methods."""
        # Method 1: keyframe query
        try:
            curves = cmds.keyframe(target_attr, query=True, name=True) or []
            if curves:
                return curves
        except Exception:
            pass
            
        # Method 2: listConnections with animCurve type filter
        try:
            conns = cmds.listConnections(target_attr, source=True, destination=False, type='animCurve') or []
            curves = [c for c in conns if c and cmds.objExists(c) and cmds.nodeType(c).startswith('animCurve')]
            if curves:
                return curves
        except Exception:
            pass
            
        # Method 3: General listConnections and filter
        try:
            all_conns = cmds.listConnections(target_attr, source=True, destination=False) or []
            curves = []
            for conn in all_conns:
                if conn and cmds.objExists(conn):
                    try:
                        if cmds.nodeType(conn).startswith('animCurve'):
                            curves.append(conn)
                    except Exception:
                        continue
            return curves
        except Exception:
            pass
            
        return []

    # =========================================================================
    # SECTION 7: COPY OPERATIONS
    # =========================================================================

    def copy_left_to_right(self, *_):
        """Copy animation from left controls to right controls using per-control settings."""
        print("DEBUG: copy_left_to_right called")
        
        # Check for selected objects first
        selected_objects = cmds.ls(selection=True, type='transform')
        
        # Debug: Also check selection without type filter
        all_selected = cmds.ls(selection=True)
        print(f"DEBUG: All selected objects: {all_selected}")
        print(f"DEBUG: Transform-filtered selected objects: {selected_objects}")
        
        if selected_objects:
            # Use selected objects only
            print(f"Processing selected objects: {selected_objects}")
            
            # Calculate offset as half the timeline length
            start_time = cmds.playbackOptions(query=True, minTime=True)
            end_time = cmds.playbackOptions(query=True, maxTime=True)
            offset = int((end_time - start_time + 1) / 2)
            
            for selected_ctrl in selected_objects:
                # Check if this control is in our left controls list
                if selected_ctrl in self.left_controls:
                    index = self.left_controls.index(selected_ctrl)
                    right_ctrl = self.right_controls[index] if index < len(self.right_controls) and self.right_controls[index] else self.get_other_side(selected_ctrl, left_to_right=True)
                    
                    if selected_ctrl == right_ctrl:
                        cmds.warning(f"Skipping pair with identical names: {selected_ctrl}")
                        continue
                    
                    # Get per-control inversion settings
                    inversion = self.control_inversions[index] if index < len(self.control_inversions) else {}
                    
                    # Copy with calculated offset and per-control settings
                    self._copy_with_per_control_settings(selected_ctrl, right_ctrl, offset, inversion)
                    print(f"Copied {selected_ctrl} -> {right_ctrl}")
                
                # Also check if this control is in our right controls list (reverse copy)
                elif selected_ctrl in self.right_controls:
                    print(f"DEBUG: Found '{selected_ctrl}' in right_controls list")
                    index = self.right_controls.index(selected_ctrl)
                    left_ctrl = self.left_controls[index] if index < len(self.left_controls) and self.left_controls[index] else self.get_other_side(selected_ctrl, left_to_right=False)
                    
                    if selected_ctrl == left_ctrl:
                        cmds.warning(f"Skipping pair with identical names: {selected_ctrl}")
                        continue
                    
                    # Get per-control inversion settings
                    inversion = self.control_inversions[index] if index < len(self.control_inversions) else {}
                    
                    # Copy with calculated offset and per-control settings (reverse direction)
                    self._copy_with_per_control_settings(selected_ctrl, left_ctrl, offset, inversion)
                    print(f"Copied {selected_ctrl} -> {left_ctrl} (reverse direction)")
                
                else:
                    # Control not in lists - try to find its opposite side automatically
                    print(f"DEBUG: '{selected_ctrl}' not found in control lists. Current lists:")
                    print(f"DEBUG: Left controls: {self.left_controls}")
                    print(f"DEBUG: Right controls: {self.right_controls}")
                    opposite_ctrl = self.get_other_side(selected_ctrl, left_to_right=True)
                    if opposite_ctrl and opposite_ctrl != selected_ctrl:
                        # Use default inversion settings (no specific inversions)
                        default_inversion = {}
                        
                        # Copy with calculated offset and default settings
                        self._copy_with_per_control_settings(selected_ctrl, opposite_ctrl, offset, default_inversion)
                        print(f"Copied {selected_ctrl} -> {opposite_ctrl} (auto-detected opposite)")
                    else:
                        cmds.warning(f"Could not find opposite side control for '{selected_ctrl}'. Consider adding it to the control lists for more precise control.")
            return
        
        # Fall back to full lists if nothing selected
        if not self.left_controls or not self.right_controls:
            cmds.warning("Left or Right list is empty. Please add paired controls first.")
            return

        print("No objects selected. Processing all left/right control pairs.")
        count = min(len(self.left_controls), len(self.right_controls))
        if len(self.left_controls) != len(self.right_controls):
            cmds.warning(f"Left/Right list lengths differ (L={len(self.left_controls)} R={len(self.right_controls)}). Using first {count} pairs.")

        for i in range(count):
            left_ctrl = self.left_controls[i]
            right_ctrl = self.right_controls[i] if i < len(self.right_controls) and self.right_controls[i] else self.get_other_side(left_ctrl, left_to_right=True)
            if left_ctrl == right_ctrl:
                cmds.warning(f"Skipping pair with identical names: {left_ctrl}")
                continue
            
            # Calculate offset as half the timeline length
            start_time = cmds.playbackOptions(query=True, minTime=True)
            end_time = cmds.playbackOptions(query=True, maxTime=True)
            offset = int((end_time - start_time + 1) / 2)
            
            # Get per-control inversion settings
            inversion = self.control_inversions[i] if i < len(self.control_inversions) else {}
            
            # Copy with calculated offset and per-control settings
            self._copy_with_per_control_settings(left_ctrl, right_ctrl, offset, inversion)

    def copy_right_to_left(self, *_):
        """Copy animation from right controls to left controls using per-control settings."""
        # Check for selected objects first
        selected_objects = cmds.ls(selection=True, type='transform')
        
        # Debug: Also check selection without type filter
        all_selected = cmds.ls(selection=True)
        print(f"DEBUG: All selected objects: {all_selected}")
        print(f"DEBUG: Transform-filtered selected objects: {selected_objects}")
        
        if selected_objects:
            # Use selected objects only
            print(f"Processing selected objects: {selected_objects}")
            
            # Calculate offset as half the timeline length
            start_time = cmds.playbackOptions(query=True, minTime=True)
            end_time = cmds.playbackOptions(query=True, maxTime=True)
            offset = int((end_time - start_time + 1) / 2)
            
            for selected_ctrl in selected_objects:
                # Check if this control is in our right controls list
                if selected_ctrl in self.right_controls:
                    index = self.right_controls.index(selected_ctrl)
                    left_ctrl = self.left_controls[index] if index < len(self.left_controls) and self.left_controls[index] else self.get_other_side(selected_ctrl, left_to_right=False)
                    
                    if selected_ctrl == left_ctrl:
                        cmds.warning(f"Skipping pair with identical names: {selected_ctrl}")
                        continue
                    
                    # Get per-control inversion settings
                    inversion = self.control_inversions[index] if index < len(self.control_inversions) else {}
                    
                    # Copy with calculated offset and per-control settings
                    self._copy_with_per_control_settings(selected_ctrl, left_ctrl, offset, inversion)
                    print(f"Copied {selected_ctrl} -> {left_ctrl}")
                
                # Also check if this control is in our left controls list (reverse copy)
                elif selected_ctrl in self.left_controls:
                    index = self.left_controls.index(selected_ctrl)
                    right_ctrl = self.right_controls[index] if index < len(self.right_controls) and self.right_controls[index] else self.get_other_side(selected_ctrl, left_to_right=True)
                    
                    if selected_ctrl == right_ctrl:
                        cmds.warning(f"Skipping pair with identical names: {selected_ctrl}")
                        continue
                    
                    # Get per-control inversion settings
                    inversion = self.control_inversions[index] if index < len(self.control_inversions) else {}
                    
                    # Copy with calculated offset and per-control settings (reverse direction)
                    self._copy_with_per_control_settings(selected_ctrl, right_ctrl, offset, inversion)
                    print(f"Copied {selected_ctrl} -> {right_ctrl} (reverse direction)")
                
                else:
                    # Control not in lists - try to find its opposite side automatically
                    opposite_ctrl = self.get_other_side(selected_ctrl, left_to_right=False)
                    if opposite_ctrl and opposite_ctrl != selected_ctrl:
                        # Use default inversion settings (no specific inversions)
                        default_inversion = {}
                        
                        # Copy with calculated offset and default settings
                        self._copy_with_per_control_settings(selected_ctrl, opposite_ctrl, offset, default_inversion)
                        print(f"Copied {selected_ctrl} -> {opposite_ctrl} (auto-detected opposite)")
                    else:
                        cmds.warning(f"Could not find opposite side control for '{selected_ctrl}'. Consider adding it to the control lists for more precise control.")
            return
        
        # Fall back to full lists if nothing selected
        if not self.left_controls or not self.right_controls:
            cmds.warning("Left or Right list is empty. Please add paired controls first.")
            return

        print("No objects selected. Processing all right/left control pairs.")
        count = min(len(self.left_controls), len(self.right_controls))
        if len(self.left_controls) != len(self.right_controls):
            cmds.warning(f"Left/Right list lengths differ (L={len(self.left_controls)} R={len(self.right_controls)}). Using first {count} pairs.")

        for i in range(count):
            right_ctrl = self.right_controls[i]
            left_ctrl = self.left_controls[i] if i < len(self.left_controls) and self.left_controls[i] else self.get_other_side(right_ctrl, left_to_right=False)
            if right_ctrl == left_ctrl:
                cmds.warning(f"Skipping pair with identical names: {right_ctrl}")
                continue
            
            # Calculate offset as half the timeline length
            start_time = cmds.playbackOptions(query=True, minTime=True)
            end_time = cmds.playbackOptions(query=True, maxTime=True)
            offset = int((end_time - start_time + 1) / 2)
            
            # Get per-control inversion settings
            inversion = self.control_inversions[i] if i < len(self.control_inversions) else {}
            
            # Copy with calculated offset and per-control settings
            self._copy_with_per_control_settings(right_ctrl, left_ctrl, offset, inversion)
    
    def _copy_with_per_control_settings(self, source_ctrl, target_ctrl, time_offset, inversion_settings):
        """Copy animation using per-control offset and inversion settings."""
        # Get full control names with prefix
        prefix = cmds.textField(self.prefix_field, query=True, text=True)
        source_full = f"{prefix}{source_ctrl}" if not source_ctrl.startswith(prefix) else source_ctrl
        target_full = f"{prefix}{target_ctrl}" if not target_ctrl.startswith(prefix) else target_ctrl

        if not (cmds.objExists(source_full) and cmds.objExists(target_full)):
            cmds.warning(f"Control not found: {source_full} or {target_full}")
            return

        # Get keyed attributes first
        source_keyed_attrs = self._keyed_attributes(source_full)
        
        # If no keyed attributes, copy current values
        if not source_keyed_attrs:
            self._copy_current_values_with_inversion(source_full, target_full, inversion_settings)
            return

        # First normalize source curves to fit timeline range
        print(f"DEBUG: Normalizing source curves for {source_full}")
        self._normalize_curves_to_timeline(source_full, source_keyed_attrs)

        # Copy keyed animation
        for attr in source_keyed_attrs:
            source_attr = f"{source_full}.{attr}"
            target_attr = f"{target_full}.{attr}"

            if not self._target_has_attribute(target_full, attr):
                continue

            source_curve = self._anim_curve_for_attr(source_attr)
            if not source_curve:
                continue

            # Copy keys with offset - ensure complete replacement
            if self._copy_and_paste_keys_with_offset(source_attr, target_attr, source_curve, time_offset, 0.0):
                # Apply per-control inversion settings with auto-detection
                if self._should_invert_attribute(attr, inversion_settings, source_full, target_full):
                    cmds.scaleKey(target_attr, valueScale=-1.0)
                
                # Apply successful tangent smoothing and cycle infinity
                print(f"DEBUG L→R: Applying tangent smoothing to {target_attr}")
                self._smooth_cycle_transitions(target_attr)
                self._apply_cycle_infinity(target_attr)
                
                # Apply curve fitting if enabled in settings
                if self.fit_curve_default:
                    print(f"DEBUG: Applying curve fitting to {target_attr}")
                    self.contain_curve_within_time_range(target_attr)
                
                # Timeline fitting disabled - cycle infinity handles offset curves properly
                # Keyframes can extend beyond timeline when using cycle infinity
    
    def _copy_current_values_with_inversion(self, source_ctrl, target_ctrl, inversion_settings):
        """Copy current channel values with per-control inversion settings."""
        attrs_to_copy = ['translateX', 'translateY', 'translateZ', 
                        'rotateX', 'rotateY', 'rotateZ',
                        'scaleX', 'scaleY', 'scaleZ']
        
        for attr in attrs_to_copy:
            source_attr = f"{source_ctrl}.{attr}"
            target_attr = f"{target_ctrl}.{attr}"
            
            # Check if both controls have this attribute
            if (self._target_has_attribute(source_ctrl, attr) and 
                self._target_has_attribute(target_ctrl, attr)):
                
                try:
                    # Get current value from source
                    current_value = cmds.getAttr(source_attr)
                    
                    # Apply inversion if set for this attribute or auto-detected
                    final_value = current_value
                    if self._should_invert_attribute(attr, inversion_settings, source_ctrl, target_ctrl):
                        final_value = -final_value
                    
                    # Handle locked attributes
                    relock = self._handle_attribute_lock(target_attr, unlock=True) 
                    
                    # Set the value on target
                    cmds.setAttr(target_attr, final_value)
                    
                    # Restore lock state
                    if relock:
                        self._handle_attribute_lock(target_attr, lock=True)
                        
                except Exception as e:
                    cmds.warning(f"Failed to copy current value for {attr}: {e}")
    
    def _should_invert_attribute(self, attr, inversion_settings, source_ctrl=None, target_ctrl=None):
        """Check if an attribute should be inverted based on per-control settings or auto-detection."""
        attr_map = {
            'translateX': 'tx', 'translateY': 'ty', 'translateZ': 'tz',
            'rotateX': 'rx', 'rotateY': 'ry', 'rotateZ': 'rz'
        }
        
        inversion_key = attr_map.get(attr)
        if not inversion_key:
            return False
            
        # If manual settings exist, use them (they override auto-detection)
        if inversion_settings and inversion_key in inversion_settings:
            return inversion_settings.get(inversion_key, False)
        
        # Auto-detect axis convention if enabled and controls are provided
        if (source_ctrl and target_ctrl and 
            hasattr(self, 'auto_detect_checkbox') and 
            cmds.checkBox(self.auto_detect_checkbox, query=True, value=True)):
            return self._auto_detect_inversion_needed(source_ctrl, target_ctrl, attr)
            
        return False
    
    def _auto_detect_inversion_needed(self, source_ctrl, target_ctrl, attr):
        """
        Automatically detect if inversion is needed by analyzing existing animation data.
        
        Args:
            source_ctrl: Source control name (with full prefix)
            target_ctrl: Target control name (with full prefix) 
            attr: Attribute name (translateX, rotateY, etc.)
            
        Returns:
            bool: True if inversion is needed, False otherwise
        """
        try:
            # Get animation curves for both controls
            source_attr = f"{source_ctrl}.{attr}"
            target_attr = f"{target_ctrl}.{attr}"
            
            source_curve = self._anim_curve_for_attr(source_attr)
            target_curve = self._anim_curve_for_attr(target_attr)
            
            # If either control has no animation, use anatomical defaults
            if not source_curve or not target_curve:
                return self._get_anatomical_inversion_default(attr, source_ctrl, target_ctrl)
            
            # Analyze correlation between source and target animation
            correlation = self._analyze_animation_correlation(source_curve, target_curve)
            
            # Positive correlation = same direction movement (need inversion)
            # Negative correlation = opposite direction movement (no inversion needed)
            inversion_needed = correlation > 0.1  # Small threshold to handle noise
            
            # Visual feedback for user
            source_short = source_ctrl.split(':')[-1] if ':' in source_ctrl else source_ctrl
            target_short = target_ctrl.split(':')[-1] if ':' in target_ctrl else target_ctrl
            action = "INVERTING" if inversion_needed else "SAME DIR"
            print(f"🤖 Auto-detect {attr}: {source_short}→{target_short} ({action}, correlation={correlation:.2f})")
            return inversion_needed
            
        except Exception as e:
            print(f"Auto-detection failed for {attr}: {e}")
            return self._get_anatomical_inversion_default(attr, source_ctrl, target_ctrl)
    
    def _analyze_animation_correlation(self, source_curve, target_curve):
        """
        Analyze the correlation between two animation curves to determine movement relationship.
        
        Returns:
            float: Correlation coefficient (-1 to 1)
                   +1 = perfect positive correlation (same direction)
                   -1 = perfect negative correlation (opposite direction)
                    0 = no correlation
        """
        try:
            # Get time range from both curves
            source_times = self._get_curve_key_times(source_curve)
            target_times = self._get_curve_key_times(target_curve)
            
            if not source_times or not target_times:
                return 0.0
            
            # Sample both curves at regular intervals
            min_time = max(min(source_times), min(target_times))
            max_time = min(max(source_times), max(target_times))
            
            if max_time <= min_time:
                return 0.0
            
            # Sample at 10 points across the overlap
            sample_count = min(10, len(source_times), len(target_times))
            sample_times = [min_time + i * (max_time - min_time) / (sample_count - 1) 
                           for i in range(sample_count)]
            
            source_values = []
            target_values = []
            
            for time in sample_times:
                source_val = cmds.keyframe(source_curve, query=True, time=(time, time), valueChange=True)
                target_val = cmds.keyframe(target_curve, query=True, time=(time, time), valueChange=True)
                
                if source_val and target_val:
                    source_values.append(source_val[0])
                    target_values.append(target_val[0])
            
            if len(source_values) < 3:  # Need at least 3 points for meaningful correlation
                return 0.0
            
            # Calculate Pearson correlation coefficient
            return self._calculate_correlation(source_values, target_values)
            
        except Exception as e:
            print(f"Correlation analysis failed: {e}")
            return 0.0
    
    def _calculate_correlation(self, x_values, y_values):
        """Calculate Pearson correlation coefficient between two value lists."""
        if len(x_values) != len(y_values) or len(x_values) < 2:
            return 0.0
        
        n = len(x_values)
        sum_x = sum(x_values)
        sum_y = sum(y_values)
        sum_xy = sum(x * y for x, y in zip(x_values, y_values))
        sum_x2 = sum(x * x for x in x_values)
        sum_y2 = sum(y * y for y in y_values)
        
        numerator = n * sum_xy - sum_x * sum_y
        denominator = ((n * sum_x2 - sum_x * sum_x) * (n * sum_y2 - sum_y * sum_y)) ** 0.5
        
        if denominator == 0:
            return 0.0
        
        return numerator / denominator
    
    def _get_curve_key_times(self, curve):
        """Get all key times from an animation curve."""
        try:
            return cmds.keyframe(curve, query=True, timeChange=True) or []
        except:
            return []
    
    def _get_anatomical_inversion_default(self, attr, source_ctrl, target_ctrl):
        """
        Get anatomical default inversion based on attribute and control names.
        This is used as fallback when no animation data is available.
        """
        # Conservative defaults - no inversions by default
        # Let animation analysis or manual settings drive inversion decisions
        anatomical_defaults = {
            'translateX': False,  # No inversion by default
            'translateY': False,  # No inversion by default
            'translateZ': False,  # No inversion by default
            'rotateX': False,     # No inversion by default
            'rotateY': False,     # No inversion by default
            'rotateZ': False      # No inversion by default
        }
        
        # Check for special control types that might have different conventions
        source_lower = source_ctrl.lower()
        
        # Eyes often have different conventions
        if any(eye_part in source_lower for eye_part in ['eye', 'look', 'gaze']):
            if attr in ['rotateX', 'rotateY']:
                return False  # Eye controls often don't need rotation mirroring
        
        # Fingers and toes often follow anatomical patterns
        if any(digit in source_lower for digit in ['finger', 'thumb', 'toe']):
            if attr == 'rotateY':
                return False  # Finger curling usually same direction
        
        return anatomical_defaults.get(attr, False)
    
    def test_axis_detection(self, *_):
        """Test the auto-detection system on current control pairs and display results."""
        if not self.left_controls or not self.right_controls:
            cmds.warning("Please add some left/right control pairs first.")
            return
        
        prefix = cmds.textField(self.prefix_field, query=True, text=True)
        results = []
        
        # Test first few pairs
        test_count = min(3, len(self.left_controls), len(self.right_controls))
        
        for i in range(test_count):
            left_ctrl = self.left_controls[i]
            right_ctrl = self.right_controls[i]
            
            left_full = f"{prefix}{left_ctrl}" if not left_ctrl.startswith(prefix) else left_ctrl
            right_full = f"{prefix}{right_ctrl}" if not right_ctrl.startswith(prefix) else right_ctrl
            
            if not (cmds.objExists(left_full) and cmds.objExists(right_full)):
                continue
            
            results.append(f"\n=== {left_ctrl} → {right_ctrl} ===")
            
            # Test each attribute
            for attr in ['translateX', 'translateY', 'translateZ', 'rotateX', 'rotateY', 'rotateZ']:
                invert_needed = self._auto_detect_inversion_needed(left_full, right_full, attr)
                status = "INVERT" if invert_needed else "SAME"
                results.append(f"  {attr}: {status}")
        
        if results:
            message = ("Auto-Detection Preview Results:\n" +
                      "(These are NOT applied yet - use 'Apply Detection' to apply them)" + 
                      "".join(results))
            cmds.confirmDialog(title="Axis Convention Detection Preview", 
                             message=message, 
                             button=['OK'])
        else:
            cmds.warning("No valid control pairs found for testing.")
    
    def apply_axis_detection(self, *_):
        """Apply auto-detection results to the inversion checkboxes for all control pairs."""
        if not self.left_controls or not self.right_controls:
            cmds.warning("Please add some left/right control pairs first.")
            return
        
        prefix = cmds.textField(self.prefix_field, query=True, text=True)
        applied_count = 0
        
        # Apply detection to all pairs
        pair_count = min(len(self.left_controls), len(self.right_controls))
        
        for i in range(pair_count):
            left_ctrl = self.left_controls[i]
            right_ctrl = self.right_controls[i]
            
            left_full = f"{prefix}{left_ctrl}" if not left_ctrl.startswith(prefix) else left_ctrl
            right_full = f"{prefix}{right_ctrl}" if not right_ctrl.startswith(prefix) else right_ctrl
            
            if not (cmds.objExists(left_full) and cmds.objExists(right_full)):
                continue
            
            # Detect inversion for each attribute and update the data
            attr_map = {
                'translateX': 'tx', 'translateY': 'ty', 'translateZ': 'tz',
                'rotateX': 'rx', 'rotateY': 'ry', 'rotateZ': 'rz'
            }
            
            for attr, key in attr_map.items():
                invert_needed = self._auto_detect_inversion_needed(left_full, right_full, attr)
                if i < len(self.control_inversions):
                    self.control_inversions[i][key] = invert_needed
            
            applied_count += 1
        
        # Refresh the UI to show updated checkboxes
        self._refresh_control_pairs_ui()
        
        if applied_count > 0:
            cmds.confirmDialog(title="Auto-Detection Applied", 
                             message=f"Applied auto-detection to {applied_count} control pairs.\n\n"
                                   f"The inversion checkboxes have been updated based on\n"
                                   f"analysis of existing animation data.\n\n"
                                   f"Manual changes to checkboxes will override these settings.",
                             button=['OK'])
            print(f"🤖 Applied auto-detection to {applied_count} control pairs")
        else:
            cmds.warning("No valid control pairs found for auto-detection.")

    # =========================================================================
    # SECTION 4: X-AXIS INVERSION DETECTION SYSTEM
    # =========================================================================

    def detect_x_inversion_needed(self, left_ctrl, right_ctrl, verbose=False):
        """
        Analyze existing animation on left/right control pair to determine if X-axis inversion is needed.
        
        Returns:
            bool: True if X-axis values should be inverted when copying, False if they should stay the same
            
        Logic:
        - If left moves +X and right moves +X at the same time -> need inversion (opposite rig convention)
        - If left moves +X and right moves -X at the same time -> no inversion needed (mirrored rig convention)
        """

        
        prefix = cmds.textField(self.prefix_field, query=True, text=True)
        left_full = f"{prefix}{left_ctrl}" if not left_ctrl.startswith(prefix) else left_ctrl
        right_full = f"{prefix}{right_ctrl}" if not right_ctrl.startswith(prefix) else right_ctrl
        
        if not (cmds.objExists(left_full) and cmds.objExists(right_full)):
            if verbose:
                print(f"Controls don't exist: {left_full} or {right_full}")
            return False
        
        # Analyze translateX patterns
        inversion_needed = self._analyze_translate_x_patterns(left_full, right_full, verbose)
        
        # If translateX analysis is inconclusive, try rotation analysis
        if inversion_needed is None:
            inversion_needed = self._analyze_rotation_patterns(left_full, right_full, verbose)
        
        # Default to False if still inconclusive
        if inversion_needed is None:
            inversion_needed = False
            if verbose:
                print(f"Analysis inconclusive for {left_ctrl}<->{right_ctrl}, defaulting to no inversion")
        
        if verbose:
            print(f"X-inversion analysis for {left_ctrl}<->{right_ctrl}: {'INVERT' if inversion_needed else 'NO INVERSION'}")
        
        return inversion_needed
    
    def _analyze_translate_x_patterns(self, left_full, right_full, verbose=False):
        """Analyze translateX animation patterns to detect inversion needs."""
        left_tx_attr = f"{left_full}.translateX"
        right_tx_attr = f"{right_full}.translateX"
        
        # Get animation curves for translateX
        left_curve = self._anim_curve_for_attr(left_tx_attr)
        right_curve = self._anim_curve_for_attr(right_tx_attr)
        
        if not (left_curve and right_curve):
            if verbose:
                print(f"Missing translateX animation: L={bool(left_curve)} R={bool(right_curve)}")
            return None
        
        # Get keyframe times that exist on both curves
        try:
            left_times = set(cmds.keyframe(left_curve, query=True, timeChange=True) or [])
            right_times = set(cmds.keyframe(right_curve, query=True, timeChange=True) or [])
            common_times = sorted(left_times.intersection(right_times))
            
            if len(common_times) < 2:
                if verbose:
                    print(f"Not enough common keyframes for analysis: {len(common_times)}")
                return None
            
            # Sample values at common times
            correlation_samples = []
            for time in common_times[:10]:  # Limit to first 10 samples for performance
                try:
                    left_val = cmds.getAttr(left_tx_attr, time=time)
                    right_val = cmds.getAttr(right_tx_attr, time=time)
                    correlation_samples.append((left_val, right_val))
                except Exception:
                    continue
            
            if len(correlation_samples) < 2:
                if verbose:
                    print("Not enough valid samples for correlation analysis")
                return None
            
            # Calculate correlation direction
            # If left and right move in same direction -> need inversion
            # If left and right move in opposite directions -> no inversion needed
            same_direction_count = 0
            opposite_direction_count = 0
            
            for i in range(1, len(correlation_samples)):
                left_prev, right_prev = correlation_samples[i-1]
                left_curr, right_curr = correlation_samples[i]
                
                left_delta = left_curr - left_prev
                right_delta = right_curr - right_prev
                
                # Skip if no significant movement
                if abs(left_delta) < 0.001 and abs(right_delta) < 0.001:
                    continue
                
                # Check if movements are in same direction or opposite
                if (left_delta > 0 and right_delta > 0) or (left_delta < 0 and right_delta < 0):
                    same_direction_count += 1
                elif (left_delta > 0 and right_delta < 0) or (left_delta < 0 and right_delta > 0):
                    opposite_direction_count += 1
            
            if verbose:
                print(f"TranslateX analysis: Same direction={same_direction_count}, Opposite direction={opposite_direction_count}")
            
            # Determine result based on predominant pattern
            if same_direction_count > opposite_direction_count:
                return True  # Need inversion - they move the same way but should be mirrored
            elif opposite_direction_count > same_direction_count:
                return False  # No inversion - already mirrored correctly
            else:
                return None  # Inconclusive
                
        except Exception as e:
            if verbose:
                print(f"Error in translateX analysis: {e}")
            return None
    
    def _analyze_rotation_patterns(self, left_full, right_full, verbose=False):
        """Analyze rotation patterns as fallback to translateX analysis."""
        # Check rotateY patterns (often the most telling for left/right differences)
        left_ry_attr = f"{left_full}.rotateY"
        right_ry_attr = f"{right_full}.rotateY"
        
        left_curve = self._anim_curve_for_attr(left_ry_attr)
        right_curve = self._anim_curve_for_attr(right_ry_attr)
        
        if not (left_curve and right_curve):
            if verbose:
                print(f"Missing rotateY animation: L={bool(left_curve)} R={bool(right_curve)}")
            return None
        
        try:
            # Get average values over time
            left_times = cmds.keyframe(left_curve, query=True, timeChange=True) or []
            right_times = cmds.keyframe(right_curve, query=True, timeChange=True) or []
            
            # Sample a few values
            left_samples = []
            right_samples = []
            
            for time in left_times[:5]:
                try:
                    left_samples.append(cmds.getAttr(left_ry_attr, time=time))
                except Exception:
                    pass
            
            for time in right_times[:5]:
                try:
                    right_samples.append(cmds.getAttr(right_ry_attr, time=time))
                except Exception:
                    pass
            
            if not (left_samples and right_samples):
                return None
            
            left_avg = sum(left_samples) / len(left_samples)
            right_avg = sum(right_samples) / len(right_samples)
            
            if verbose:
                print(f"RotateY averages: L={left_avg:.3f}, R={right_avg:.3f}")
            
            # If rotations have same sign, they might need inversion
            # This is a heuristic - not foolproof
            if (left_avg > 0 and right_avg > 0) or (left_avg < 0 and right_avg < 0):
                return True  # Likely need inversion
            else:
                return False  # Likely already mirrored
                
        except Exception as e:
            if verbose:
                print(f"Error in rotation analysis: {e}")
            return None
    
    def analyze_all_control_pairs(self, verbose=False):
        """Analyze all current left/right control pairs for inversion detection."""
        if not self.left_controls or not self.right_controls:
            cmds.warning("No control pairs to analyze")
            return
        
        results = {}
        count = min(len(self.left_controls), len(self.right_controls))
        
        print(f"Analyzing {count} control pairs for X-axis inversion needs...")
        
        for i in range(count):
            left_ctrl = self.left_controls[i]
            right_ctrl = self.right_controls[i] if i < len(self.right_controls) else self.get_other_side(left_ctrl, True)
            
            if left_ctrl and right_ctrl:
                inversion_needed = self.detect_x_inversion_needed(left_ctrl, right_ctrl, verbose)
                results[f"{left_ctrl}<->{right_ctrl}"] = inversion_needed
        
        # Summary
        invert_count = sum(1 for need_invert in results.values() if need_invert)
        no_invert_count = len(results) - invert_count
        
        print(f"Analysis complete: {invert_count} pairs need inversion, {no_invert_count} pairs don't")
        
        if verbose:
            for pair, needs_invert in results.items():
                print(f"  {pair}: {'INVERT' if needs_invert else 'NO INVERSION'}")
        
        return results

    # =========================================================================
    # SECTION 9: UI CALLBACKS & HELPERS
    # =========================================================================



    # =========================================================================
    # SECTION 2: CONTROL MANAGEMENT (continued)
    # =========================================================================

    def save_presets(self, *_):
        """Save current settings to a JSON preset file."""
        try:
            file_path = cmds.fileDialog2(
                caption="Save Cycle Maker Presets",
                fileMode=0,  # Save file
                fileFilter="JSON Files (*.json)",
                dialogStyle=2
            )
        except Exception as e:
            print(f"File dialog error: {e}")
            cmds.warning(f"File dialog failed: {e}")
            return
        
        if not file_path:
            print("No file selected - user canceled")
            return
            
        print(f"Selected file: {file_path[0]}")
        preset_data = {
            'cycle_maker': {
                'left_controls': self.left_controls[:],
                'right_controls': self.right_controls[:],
                'control_inversions': self.control_inversions[:],
                'spine_controls': self._get_spine_controls(),

            },
            'copy_with_offset': {
                'objects': self.copy_offset_objects[:],
                'time_offsets': self.copy_offset_time_offsets[:],
                'value_offsets': self.copy_offset_value_offsets[:],
                'channel_settings': self.copy_offset_channel_settings[:]
            }
        }
        
        try:
            import json
            with open(file_path[0], 'w') as f:
                json.dump(preset_data, f, indent=4)
            print(f"Saved presets to: {file_path[0]}")
            cmds.confirmDialog(title="Success", message=f"Presets saved successfully!\n{file_path[0]}", button="OK")
        except Exception as e:
            cmds.warning(f"Failed to save presets: {e}")

    def load_presets(self, *_):
        """Load settings from a JSON preset file."""
        try:
            file_path = cmds.fileDialog2(
                caption="Load Cycle Maker Presets",
                fileMode=1,  # Load file
                fileFilter="JSON Files (*.json)",
                dialogStyle=2
            )
        except Exception as e:
            print(f"File dialog error: {e}")
            cmds.warning(f"File dialog failed: {e}")
            return
        
        if not file_path:
            return
            
        try:
            import json
            with open(file_path[0], 'r') as f:
                preset_data = json.load(f)
            
            # Load Cycle Maker data
            if 'cycle_maker' in preset_data:
                cm_data = preset_data['cycle_maker']
                self.left_controls = cm_data.get('left_controls', [])
                self.right_controls = cm_data.get('right_controls', [])
                self.control_inversions = cm_data.get('control_inversions', [])
                self._refresh_control_pairs_ui()
                
                # Load spine controls
                spine_controls = cm_data.get('spine_controls', [])
                if spine_controls:
                    cmds.textScrollList(self.spine_controls_list, edit=True, removeAll=True)
                    for control in spine_controls:
                        cmds.textScrollList(self.spine_controls_list, edit=True, append=control)
                
                # Note: Spine invert settings are now automatic based on forward direction
                # No longer need manual checkbox settings
            
            # Load Copy with Offset data
            if 'copy_with_offset' in preset_data:
                co_data = preset_data['copy_with_offset']
                self.copy_offset_objects = co_data.get('objects', [])
                self.copy_offset_time_offsets = co_data.get('time_offsets', [])
                self.copy_offset_value_offsets = co_data.get('value_offsets', [])
                self.copy_offset_channel_settings = co_data.get('channel_settings', [])
                self._refresh_copy_offset_ui()
            
            print(f"Loaded presets from: {file_path[0]}")
            cmds.confirmDialog(title="Success", message=f"Presets loaded successfully!\n{file_path[0]}", button="OK")
            
        except Exception as e:
            cmds.warning(f"Failed to load presets: {e}")
            cmds.confirmDialog(title="Error", message=f"Failed to load presets:\n{e}", button="OK")

    # ---------------------
    # Actions: Spine inversion pass
    # ---------------------

    def _get_selected_curves_info(self):
        """
        Get information about which curves have selected keyframes and in which half.
        Returns: dict with curve names as keys and direction info as values
        """
        try:
            # Get selected curves from graph editor
            selected_curves = cmds.keyframe(query=True, selected=True, name=True) or []
            
            if not selected_curves:
                # No keyframes selected, return empty dict (will use default behavior)
                return {}
            
            # Get timeline range
            start, end, mid = self._playback_cycle_range()
            
            curve_info = {}
            
            for curve in selected_curves:
                try:
                    # Get selected keyframe times for this specific curve
                    selected_times = cmds.keyframe(curve, query=True, selected=True, timeChange=True) or []
                    
                    if not selected_times:
                        continue
                    
                    # Analyze where most selected keys are located for this curve
                    first_half_count = 0
                    second_half_count = 0
                    
                    for key_time in selected_times:
                        if key_time <= mid:
                            first_half_count += 1
                        else:
                            second_half_count += 1
                    
                    # Determine which half has more selected keys for this curve
                    if first_half_count > second_half_count:
                        direction = 'first'
                    elif second_half_count > first_half_count:
                        direction = 'second'
                    else:
                        # Equal or unclear, use default
                        direction = 'default'
                    
                    curve_info[curve] = direction
                    
                except Exception as e:
                    print(f"Error processing curve {curve}: {e}")
                    continue
            
            return curve_info
                
        except Exception as e:
            print(f"Error detecting selected curves: {e}")
            return {}

    def invert_spine_channels(self, *_):
        """
        Intelligent spine channel cycling based on selected keyframes:
        - If keys selected in first half: copy/invert first → second
        - If keys selected in second half: copy/invert second → first  
        - If whole curve or no selection: copy/invert first → second (default)
        
        Channel behavior:
        - rotateY, rotateZ, translateX, translateZ: antiphase (inverted copy)
        - rotateX, translateY: standard cycle (direct copy)
        """
        # Get information about selected curves and their keyframe locations
        selected_curves_info = self._get_selected_curves_info()
        
        # Check for selected objects first
        sel = cmds.ls(selection=True) or []
        spine_controls = self._get_spine_controls()
        
        if sel:
            # Use selected objects (work with any selection, not just spine controls list)
            print(f"Processing selected objects for spine cycling: {sel}")
        else:
            # Fall back to all spine controls if nothing selected
            if not spine_controls:
                cmds.warning("No spine controls defined. Add controls to the Spine Controls list first.")
                return
            sel = spine_controls
            print(f"No objects selected. Processing all spine controls: {sel}")
        
        if selected_curves_info:
            print(f"Will process only curves with selected keyframes: {list(selected_curves_info.keys())}")
        else:
            print("No keyframes selected - will process all channels with default behavior")
            
        try:
            invert_y = cmds.checkBox(self.invert_y_chk, query=True, value=True)
            invert_z = cmds.checkBox(self.invert_z_chk, query=True, value=True)
        except Exception:
            invert_y = self.spine_invert_y_default
            invert_z = self.spine_invert_z_default

        start, end, mid = self._playback_cycle_range()
        if end <= start:
            cmds.warning("Invalid playback range. Set a valid range (e.g., 0 to 40).")
            return

        # Intelligent channel categorization based on settings
        travel_direction = self.forward_direction      # Travel direction: 'X', 'Y', or 'Z'
        rotation_axis = self.forward_rotation_axis     # Spine rotation axis: 'X', 'Y', or 'Z'
        
        # Translation channels:
        # - Y (up/down): Always double cycle (up-down-up-down per walk cycle)  
        # - Z (forward): Always double cycle (continuous forward movement with variations)
        # - X (side): Always asymmetrical (left step vs right step)
        double_cycle_translate = ["translateY", "translateZ"]
        asymmetrical_translate = ["translateX"]
        
        # Rotation channels based on forward rotation axis:
        # - Forward rotation axis: Double cycle (forward/back rocking with each step)
        # - Other two axes: Asymmetrical (left vs right step creates different twisting)
        if rotation_axis == 'X':
            double_cycle_rotate = ["rotateX"]
            asymmetrical_rotate = ["rotateY", "rotateZ"]
        elif rotation_axis == 'Y':
            double_cycle_rotate = ["rotateY"] 
            asymmetrical_rotate = ["rotateX", "rotateZ"]
        else:  # rotation_axis == 'Z'
            double_cycle_rotate = ["rotateZ"]
            asymmetrical_rotate = ["rotateX", "rotateY"]
        
        # Combine channel lists
        antiphase_attrs = asymmetrical_translate + asymmetrical_rotate  # Channels that get inverted
        standard_attrs = double_cycle_translate + double_cycle_rotate   # Channels that get direct copy
        
        print(f"Travel direction: {travel_direction}, Rotation axis: {rotation_axis}")
        print(f"Asymmetrical (inverted) channels: {antiphase_attrs}")
        print(f"Double cycle (direct copy) channels: {standard_attrs}")

        count = 0
        for node in sel:
            # Process antiphase channels (with inversion)
            for attr in antiphase_attrs:
                plug = f"{node}.{attr}"
                try:
                    if not cmds.objExists(plug):
                        continue
                except Exception:
                    continue
                
                # Get the animation curve for this plug
                anim_curve = self._anim_curve_for_attr(plug)
                if not anim_curve:
                    continue
                
                # Check if this specific curve has selected keyframes
                if selected_curves_info and anim_curve not in selected_curves_info:
                    # Skip curves that don't have selected keyframes
                    continue
                
                # Determine direction for this specific curve
                if selected_curves_info and anim_curve in selected_curves_info:
                    curve_direction = selected_curves_info[anim_curve]
                else:
                    curve_direction = 'default'
                
                # Apply directional cycling based on this curve's keyframe selection
                if curve_direction == 'second':
                    # Copy from second half to first half (inverted)
                    self._rebuild_first_half_antiphase(plug, start, mid, end)
                    direction_msg = "second → first (inverted)"
                else:
                    # Default: Copy from first half to second half (inverted)
                    self._rebuild_second_half_antiphase(plug, start, mid, end)
                    direction_msg = "first → second (inverted)"
                
                print(f"Applied antiphase to {plug}: {direction_msg}")
                
                # Apply curve fitting if enabled in settings
                if self.fit_curve_default:
                    self.contain_curve_within_time_range(plug)
                count += 1
                
            # Process standard cycle channels (direct copy)
            for attr in standard_attrs:
                plug = f"{node}.{attr}"
                try:
                    if not cmds.objExists(plug):
                        continue
                except Exception:
                    continue
                
                # Get the animation curve for this plug
                anim_curve = self._anim_curve_for_attr(plug)
                if not anim_curve:
                    continue
                
                # Check if this specific curve has selected keyframes
                if selected_curves_info and anim_curve not in selected_curves_info:
                    # Skip curves that don't have selected keyframes
                    continue
                
                # Determine direction for this specific curve
                if selected_curves_info and anim_curve in selected_curves_info:
                    curve_direction = selected_curves_info[anim_curve]
                else:
                    curve_direction = 'default'
                
                # Apply directional cycling based on this curve's keyframe selection
                if curve_direction == 'second':
                    # Copy from second half to first half (direct)
                    self._rebuild_first_half_standard(plug, start, mid, end)
                    direction_msg = "second → first (direct)"
                else:
                    # Default: Copy from first half to second half (direct)
                    self._rebuild_second_half_standard(plug, start, mid, end)
                    direction_msg = "first → second (direct)"
                
                print(f"Applied standard cycle to {plug}: {direction_msg}")
                
                # Apply curve fitting if enabled in settings
                if self.fit_curve_default:
                    self.contain_curve_within_time_range(plug)
                count += 1

        if count == 0:
            cmds.warning("No matching spine channels processed. Check selection, spine controls list, and playback range.")
        else:
            cmds.inViewMessage(amg=f"Applied cycle/antiphase to {count} channel(s) over [{start:.0f},{end:.0f}]", pos='midCenter', fade=True)

    def _rebuild_second_half_standard(self, plug, start, mid, end):
        """
        Make [mid,end] a standard cycle (copy of [start,mid]) for the given plug.
        """
        # Anchor values
        try:
            v_start = cmds.getAttr(plug, time=start)
        except Exception:
            v_start = None
        if not self._has_key_at(plug, start):
            self._ensure_key(plug, start, v_start)
        if not self._has_key_at(plug, mid):
            self._ensure_key(plug, mid, v_start if v_start is not None else None)

        # Unlock if needed
        relock = False
        try:
            if cmds.getAttr(plug, lock=True):
                relock = True
                cmds.setAttr(plug, lock=False)
        except Exception:
            pass

        # Clear second half
        try:
            cmds.cutKey(plug, time=(mid, end))
        except Exception:
            pass

        # Copy first half [start, mid) and paste to [mid, end)
        try:
            cmds.copyKey(plug, time=(start, mid), includeUpperBound=False)
        except Exception as e:
            cmds.warning(f"copyKey failed on {plug} [{start},{mid}): {e}")
            return
        try:
            cmds.pasteKey(plug, option='merge', timeOffset=(mid - start))
        except Exception as e:
            try:
                cmds.pasteKey(plug, option='merge')
            except Exception as e2:
                cmds.warning(f"pasteKey failed on {plug}: {e2}")
                return

        # Enforce anchors: end==start, mid==start
        try:
            if v_start is None:
                v_start = cmds.getAttr(plug, time=start)
        except Exception:
            v_start = 0.0
        self._ensure_key(plug, mid, float(v_start))
        self._ensure_key(plug, end, float(v_start))

        # Apply tangent smoothing for spine standard cycles
        self._smooth_spine_transitions(plug, start, mid, end, is_antiphase=False)
        
        # Apply cycle infinity for seamless looping
        self._apply_cycle_infinity(plug)

        # Relock
        if relock:
            try:
                cmds.setAttr(plug, lock=True)
            except Exception:
                pass

    def _rebuild_first_half_antiphase(self, plug, start, mid, end):
        """
        Make [start,mid] equal to the negative of [mid,end] for the given plug.
        (Reverse direction antiphase - copy from second half to first half)
        """
        # Validate that there are keyframes to work with
        try:
            all_keyframes = cmds.keyframe(plug, query=True, timeChange=True) or []
            if not all_keyframes:
                cmds.warning(f"No keyframes found on {plug}. Cannot perform antiphase operation.")
                return
            
            # Check if there are any keyframes in the second half to copy from
            second_half_keys = [t for t in all_keyframes if mid <= t <= end]
            if not second_half_keys:
                cmds.warning(f"No keyframes found in second half [{mid}, {end}] on {plug}. Cannot perform antiphase operation.")
                return
                
        except Exception as e:
            cmds.warning(f"Error checking keyframes on {plug}: {e}")
            return
            
        # Anchor values
        try:
            v_end = cmds.getAttr(plug, time=end)
        except Exception:
            v_end = None
        if not self._has_key_at(plug, end):
            self._ensure_key(plug, end, v_end)
        if not self._has_key_at(plug, mid):
            # Create a temp key at mid to aid paste alignment
            self._ensure_key(plug, mid, v_end if v_end is not None else None)

        # Unlock if needed
        relock = False
        try:
            if cmds.getAttr(plug, lock=True):
                relock = True
                cmds.setAttr(plug, lock=False)
        except Exception:
            pass

        # Clear first half
        try:
            cmds.cutKey(plug, time=(start, mid))
        except Exception:
            pass

        # Copy second half [mid, end] and paste to first half [start, mid]
        try:
            cmds.copyKey(plug, time=(mid, end), includeUpperBound=True)
        except Exception as e:
            cmds.warning(f"copyKey failed on {plug} [{mid},{end}]: {e}")
            return
        try:
            cmds.pasteKey(plug, option='merge', timeOffset=(start - mid))
        except Exception as e:
            try:
                cmds.pasteKey(plug, option='merge')
            except Exception as e2:
                cmds.warning(f"pasteKey failed on {plug}: {e2}")
                return

        # Scale all keys in first half by -1 (invert)
        try:
            cmds.scaleKey(plug, time=(start, mid), valueScale=-1, includeUpperBound=False)
        except Exception as e:
            cmds.warning(f"scaleKey failed on {plug}: {e}")

        # Enforce anchors for proper antiphase symmetry
        try:
            if v_end is None:
                v_end = cmds.getAttr(plug, time=end)
        except Exception:
            v_end = 0.0
        
        # For proper antiphase cycles: start and end have same value, midpoint is inverse
        # This creates perfect symmetrical inversion where mid is opposite of start/end
        self._ensure_key(plug, start, float(v_end))
        self._ensure_key(plug, mid, float(-v_end))

        # Apply tangent smoothing for spine antiphase cycles
        self._smooth_spine_transitions(plug, start, mid, end, is_antiphase=True)
        
        # Apply cycle infinity for seamless looping
        self._apply_cycle_infinity(plug)

        # Relock
        if relock:
            try:
                cmds.setAttr(plug, lock=True)
            except Exception:
                pass

    def _rebuild_first_half_standard(self, plug, start, mid, end):
        """
        Make [start,mid] a standard cycle (copy of [mid,end]) for the given plug.
        (Reverse direction standard - copy from second half to first half)
        """
        # Anchor values
        try:
            v_end = cmds.getAttr(plug, time=end)
        except Exception:
            v_end = None
        if not self._has_key_at(plug, end):
            self._ensure_key(plug, end, v_end)
        if not self._has_key_at(plug, mid):
            self._ensure_key(plug, mid, v_end if v_end is not None else None)

        # Unlock if needed
        relock = False
        try:
            if cmds.getAttr(plug, lock=True):
                relock = True
                cmds.setAttr(plug, lock=False)
        except Exception:
            pass

        # Clear first half
        try:
            cmds.cutKey(plug, time=(start, mid))
        except Exception:
            pass

        # Copy second half [mid, end] and paste to first half [start, mid]
        try:
            cmds.copyKey(plug, time=(mid, end), includeUpperBound=True)
        except Exception as e:
            cmds.warning(f"copyKey failed on {plug} [{mid},{end}]: {e}")
            return
        try:
            cmds.pasteKey(plug, option='merge', timeOffset=(start - mid))
        except Exception as e:
            try:
                cmds.pasteKey(plug, option='merge')
            except Exception as e2:
                cmds.warning(f"pasteKey failed on {plug}: {e2}")
                return

        # Enforce anchors: start==end, mid==end
        try:
            if v_end is None:
                v_end = cmds.getAttr(plug, time=end)
        except Exception:
            v_end = 0.0
        self._ensure_key(plug, start, float(v_end))
        self._ensure_key(plug, mid, float(v_end))

        # Apply tangent smoothing for spine standard cycles
        self._smooth_spine_transitions(plug, start, mid, end, is_antiphase=False)
        
        # Apply cycle infinity for seamless looping
        self._apply_cycle_infinity(plug)

        # Relock
        if relock:
            try:
                cmds.setAttr(plug, lock=True)
            except Exception:
                pass

    # =========================================================================
    # SECTION 10: COPY WITH OFFSET FUNCTIONALITY
    # =========================================================================
    
    def select_all_channels(self, *_):
        """Select all translation and rotation channels."""
        cmds.checkBox(self.translate_x_chk, edit=True, value=True)
        cmds.checkBox(self.translate_y_chk, edit=True, value=True)
        cmds.checkBox(self.translate_z_chk, edit=True, value=True)
        cmds.checkBox(self.rotate_x_chk, edit=True, value=True)
        cmds.checkBox(self.rotate_y_chk, edit=True, value=True)
        cmds.checkBox(self.rotate_z_chk, edit=True, value=True)
    
    def deselect_all_channels(self, *_):
        """Deselect all translation and rotation channels."""
        cmds.checkBox(self.translate_x_chk, edit=True, value=False)
        cmds.checkBox(self.translate_y_chk, edit=True, value=False)
        cmds.checkBox(self.translate_z_chk, edit=True, value=False)
        cmds.checkBox(self.rotate_x_chk, edit=True, value=False)
        cmds.checkBox(self.rotate_y_chk, edit=True, value=False)
        cmds.checkBox(self.rotate_z_chk, edit=True, value=False)
    
    def get_selected_channels(self):
        """Get list of selected channels for copy operation."""
        channels = []
        if cmds.checkBox(self.translate_x_chk, query=True, value=True):
            channels.append('translateX')
        if cmds.checkBox(self.translate_y_chk, query=True, value=True):
            channels.append('translateY')
        if cmds.checkBox(self.translate_z_chk, query=True, value=True):
            channels.append('translateZ')
        if cmds.checkBox(self.rotate_x_chk, query=True, value=True):
            channels.append('rotateX')
        if cmds.checkBox(self.rotate_y_chk, query=True, value=True):
            channels.append('rotateY')
        if cmds.checkBox(self.rotate_z_chk, query=True, value=True):
            channels.append('rotateZ')
        return channels
    
       
    def _toggle_layer_name_field(self, value):
        """Toggle the layer name field based on checkbox state."""
        cmds.textField(self.layer_name_field, edit=True, enable=value)
        # Find and enable/disable the text label
        parent = cmds.textField(self.layer_name_field, query=True, parent=True)
        if parent:
            children = cmds.layout(parent, query=True, childArray=True)
            if children and len(children) > 0:
                # Enable/disable the "Layer Name:" text
                try:
                    cmds.text(children[0], edit=True, enable=value)
                except:
                    pass

    def copy_with_offset(self, *_):
        """Copy animation using per-object offset settings from the object list."""
        if not self.copy_offset_objects:
            cmds.warning("No objects in the Copy with Offset list. Please add objects first.")
            return
        
        if len(self.copy_offset_objects) < 2:
            cmds.warning("Need at least 2 objects in the list. First object is the source.")
            return
        
        # Check if we should copy to a new animation layer
        use_layer = cmds.checkBox(self.copy_to_layer_checkbox, query=True, value=True)
        layer_name = None
        original_layer = None
        source_layer = None
        
        if use_layer:
            # Get the currently selected source layer to copy from
            try:
                all_layers = cmds.ls(type='animLayer')
                if all_layers:
                    for layer in all_layers:
                        if cmds.animLayer(layer, query=True, selected=True):
                            source_layer = layer
                            print(f"Will copy animation from layer: {source_layer}")
                            break
                    
                    if not source_layer:
                        # If no layer selected, check for preferred layer
                        try:
                            source_layer = cmds.animLayer(query=True, root=True, bestLayer=True)
                            if source_layer:
                                print(f"Using preferred layer as source: {source_layer}")
                        except:
                            pass
                
                if not source_layer:
                    print("No source layer selected, will copy from base animation")
            except:
                print("Could not determine source layer, will copy from base animation")
            
            # Enable animation layers if not already enabled
            if not cmds.animLayer(query=True, root=True):
                try:
                    # Create the base animation layer if it doesn't exist
                    mel.eval('animLayerEditorOnlyAnimCurves;')
                except:
                    # Alternative method if the MEL command doesn't exist
                    try:
                        cmds.animLayer('BaseAnimation', override=True, passthrough=True)
                    except:
                        pass
            
            # Get layer name from field
            layer_name = cmds.textField(self.layer_name_field, query=True, text=True)
            if not layer_name:
                layer_name = "OffsetLayer"
            
            # Create new animation layer
            if cmds.animLayer(layer_name, query=True, exists=True):
                # If layer exists, make it unique
                counter = 1
                while cmds.animLayer(f"{layer_name}{counter}", query=True, exists=True):
                    counter += 1
                layer_name = f"{layer_name}{counter}"
            
            # Create the layer - don't add selected objects yet, we'll add them individually
            layer_name = cmds.animLayer(layer_name)
            print(f"Created animation layer: {layer_name}")
            
            # Set layer to override mode (not additive) so values replace base animation
            cmds.animLayer(layer_name, edit=True, override=True)
            
            # Set the new layer as the active layer
            try:
                original_layer = cmds.animLayer(query=True, root=True, bestLayer=True)
            except:
                original_layer = None
            cmds.animLayer(layer_name, edit=True, selected=True, preferred=True)
        
        copied_count = 0
        
        try:
            # Copy sequentially: each object copies from the previous object in the list
            for i in range(1, len(self.copy_offset_objects)):
                source_ctrl = self.copy_offset_objects[i-1]  # Previous object as source
                target_ctrl = self.copy_offset_objects[i]     # Current object as target
                time_offset = self.copy_offset_time_offsets[i] if i < len(self.copy_offset_time_offsets) else 1
                value_offset = self.copy_offset_value_offsets[i] if i < len(self.copy_offset_value_offsets) else 0.0
                channel_settings = self.copy_offset_channel_settings[i] if i < len(self.copy_offset_channel_settings) else {}
                
                # Get enabled channels for this object
                channels = self._get_enabled_channels_for_object(channel_settings)
                if not channels:
                    print(f"Skipping {target_ctrl} - no channels enabled")
                    continue
                
                # If using layers, select the target object before copying
                if use_layer and layer_name:
                    if cmds.objExists(target_ctrl):
                        cmds.select(target_ctrl, replace=True)
                
                # Copy with individual object settings from previous object
                print(f"Copying from {source_ctrl} → {target_ctrl} (time offset: {time_offset}, value offset: {value_offset})")
                success = self.copy_animation_with_offset(source_ctrl, target_ctrl, channels, 
                                                        time_offset, value_offset, 
                                                        target_layer=layer_name if use_layer else None,
                                                        source_layer=source_layer if use_layer else None)
                if success:
                    copied_count += 1
            
            if copied_count > 0:
                message = f"Sequential copy completed: {copied_count} objects with cascading offsets"
                if use_layer:
                    message += f" (on layer: {layer_name})"
                cmds.inViewMessage(amg=message, pos='midCenter', fade=True)
                print(f"🎯 Sequential Copy with Offset completed: {copied_count} objects in chain")
            else:
                cmds.warning("No animation was copied. Check object names and channel settings.")
        
        finally:
            # Restore original layer if we changed it
            if use_layer and original_layer:
                try:
                    cmds.animLayer(original_layer, edit=True, preferred=True)
                except:
                    pass  # Original layer might not be valid anymore

    def _get_enabled_channels_for_object(self, channel_settings):
        """Get list of enabled channels for a specific object."""
        channels = []
        channel_map = {
            'tx': 'translateX', 'ty': 'translateY', 'tz': 'translateZ',
            'rx': 'rotateX', 'ry': 'rotateY', 'rz': 'rotateZ'
        }
        
        for key, maya_channel in channel_map.items():
            if channel_settings.get(key, True):  # Default to True if not specified
                channels.append(maya_channel)
        
        return channels
    
    def copy_animation_with_offset(self, source_ctrl, target_ctrl, channels, time_offset, value_offset, target_layer=None, source_layer=None):
        """Copy animation from source to target with specified offsets, optionally from/to animation layers."""
        if not (cmds.objExists(source_ctrl) and cmds.objExists(target_ctrl)):
            print(f"Controls not found: {source_ctrl} or {target_ctrl}")
            return False
        
        print(f"DEBUG: Attempting to copy channels: {channels}")
        print(f"DEBUG: Source layer: {source_layer}, Target layer: {target_layer}")
        
        copied_channels = 0
        
        for channel in channels:
            # Build the attribute names - include layer if copying from a specific layer
            if source_layer:
                # When copying from a layer, we need to get the layer-specific curve
                source_attr = f"{source_ctrl}.{channel}"
            else:
                source_attr = f"{source_ctrl}.{channel}"
            
            target_attr = f"{target_ctrl}.{channel}"
            
            print(f"DEBUG: Checking {source_attr}")
            
            # Skip if source doesn't have this attribute or it's not animated
            if not cmds.objExists(source_attr):
                print(f"DEBUG: {source_attr} does not exist")
                continue
            
            # Get the animation curve - if source_layer is specified, get it from that layer
            if source_layer:
                try:
                    # Get the curve from the specific animation layer
                    layer_curves = cmds.animLayer(source_layer, query=True, animCurves=True) or []
                    source_curve = None
                    # Find the curve that affects this attribute
                    for curve in layer_curves:
                        try:
                            # Check if this curve is connected to our source attribute
                            connections = cmds.listConnections(curve, plugs=True, destination=True) or []
                            for conn in connections:
                                if source_attr in conn or conn.startswith(f"{source_layer}."):
                                    # Check if this curve affects our attribute
                                    affected_attrs = cmds.listConnections(curve, plugs=True, source=False) or []
                                    for attr in affected_attrs:
                                        if source_ctrl in attr and channel in attr:
                                            source_curve = curve
                                            break
                            if source_curve:
                                break
                        except:
                            continue
                    
                    if not source_curve:
                        # Fallback: try to get curve from the blended result
                        source_curve = self._anim_curve_for_attr(source_attr)
                        
                except Exception as e:
                    print(f"DEBUG: Error getting curve from layer: {e}")
                    source_curve = self._anim_curve_for_attr(source_attr)
            else:
                source_curve = self._anim_curve_for_attr(source_attr)
            
            if not source_curve:
                print(f"DEBUG: {source_attr} has no animation curve")
                continue
            
            print(f"DEBUG: Found animation curve: {source_curve}")
            
            # Skip if source doesn't have this attribute or it's not animated
            if not cmds.objExists(source_attr):
                print(f"DEBUG: {source_attr} does not exist")
                continue
            
            source_curve = self._anim_curve_for_attr(source_attr)
            if not source_curve:
                print(f"DEBUG: {source_attr} has no animation curve")
                continue
            
            print(f"DEBUG: Found animation curve: {source_curve}")
            
            # Skip if target doesn't have this attribute
            if not cmds.objExists(target_attr):
                print(f"DEBUG: {target_attr} does not exist")
                continue
            
            # Check if target attribute is locked - skip if it is
            try:
                if cmds.getAttr(target_attr, lock=True):
                    # Silently skip locked attributes
                    print(f"DEBUG: {target_attr} is locked, skipping")
                    continue
            except Exception:
                pass
            
            # If using animation layer, add the attribute to the layer
            if target_layer:
                # Make sure the target is in the layer
                try:
                    cmds.animLayer(target_layer, edit=True, attribute=target_attr)
                    print(f"DEBUG: Added {target_attr} to layer {target_layer}")
                except Exception as e:
                    # If we can't add to layer (might be locked), skip this attribute
                    print(f"DEBUG: Could not add {target_attr} to layer: {e}")
                    continue
            
            # Get time range from source
            try:
                time_range = cmds.keyframe(source_curve, query=True, timeChange=True)
                if not time_range:
                    continue
                    
                start_t = min(time_range)
                end_t = max(time_range)
                
                # Copy keys from source
                cmds.copyKey(source_attr, time=(start_t, end_t), includeUpperBound=True)
                
                # Paste with offsets
                try:
                    cmds.pasteKey(target_attr, option='replaceCompletely', 
                                timeOffset=time_offset, valueOffset=value_offset)
                except Exception as e:
                    # Fallback paste
                    try:
                        cmds.pasteKey(target_attr, option='replaceCompletely')
                        # Apply offsets manually if paste with offsets failed
                        if time_offset != 0:
                            cmds.keyframe(target_attr, edit=True, relative=True, timeChange=time_offset)
                        if value_offset != 0:
                            cmds.keyframe(target_attr, edit=True, relative=True, valueChange=value_offset)
                    except Exception as e2:
                        cmds.warning(f"Failed to paste keys to {target_attr}: {e2}")
                        continue
                
                copied_channels += 1
                        
            except Exception as e:
                print(f"Error copying {source_attr} to {target_attr}: {e}")
        
        if copied_channels > 0:
            print(f"Successfully copied {copied_channels} channels from {source_ctrl} to {target_ctrl}")
        else:
            print(f"No channels were copied from {source_ctrl} to {target_ctrl}")
        
        return copied_channels > 0

    # =========================================================================
    # SECTION 11: TANGENT SMOOTHING FOR CYCLE CONTINUITY
    # =========================================================================
    
    def _ensure_smooth_cycle_tangents(self, curves, start_time, end_time):
        """Ensure smooth tangent continuity at cycle boundaries for seamless looping."""
        if not curves:
            return
            
        # Normalize to list
        if isinstance(curves, str):
            curves = [curves]
            
        for curve in curves:
            if not curve or not cmds.objExists(curve):
                continue
                
            self._apply_smooth_cycle_tangents_to_curve(curve, start_time, end_time)
    
    def _apply_smooth_cycle_tangents_to_curve(self, curve, start_time, end_time):
        """Apply smooth cycle tangents to a single curve."""
        try:
            # Get all keyframe times on this curve
            key_times = cmds.keyframe(curve, query=True, timeChange=True) or []
            if len(key_times) < 2:
                return
                
            # Find start and end keys (closest to start_time and end_time)
            start_key = min(key_times, key=lambda t: abs(t - start_time))
            end_key = min(key_times, key=lambda t: abs(t - end_time))
            
            if start_key == end_key:
                return
            
            # Ensure values match for perfect cycling
            start_value = cmds.keyframe(curve, time=(start_key, start_key), query=True, valueChange=True)[0]
            end_value = cmds.keyframe(curve, time=(end_key, end_key), query=True, valueChange=True)[0]
            
            if abs(start_value - end_value) > 0.001:  # Small tolerance for floating point
                cmds.keyframe(curve, time=(end_key, end_key), valueChange=start_value)
                print(f"DEBUG: Matched end value to start value for {curve}")
            
            # Apply directional tangent smoothing for natural curve flow + cycle continuity
            self._apply_directional_cycle_tangents(curve, key_times, start_key, end_key)
                
        except Exception as e:
            print(f"DEBUG: Error applying smooth cycle tangents to {curve}: {e}")
    
    def _apply_directional_cycle_tangents(self, curve, key_times, start_key, end_key):
        """Apply tangents with smooth middle keys and inverted start/end for cycling."""
        try:
            # STEP 1: Apply smooth spline tangents to ALL keys first (natural curve flow)
            for key_time in key_times:
                cmds.keyTangent(curve, time=(key_time, key_time), 
                              inTangentType='spline', outTangentType='spline')
            
            print(f"DEBUG: Applied spline tangents to all {len(key_times)} keys")
            
            # STEP 2: Get the smoothed tangent angles from start and end keys
            start_out_angle = cmds.keyTangent(curve, time=(start_key, start_key), query=True, outAngle=True)[0]
            start_out_weight = cmds.keyTangent(curve, time=(start_key, start_key), query=True, outWeight=True)[0]
            
            end_in_angle = cmds.keyTangent(curve, time=(end_key, end_key), query=True, inAngle=True)[0]
            end_in_weight = cmds.keyTangent(curve, time=(end_key, end_key), query=True, inWeight=True)[0]
            
            # STEP 3: Make end key tangents exactly match start key tangents for perfect cycling
            # Get start key's final tangent information (after spline smoothing)
            start_in_angle = cmds.keyTangent(curve, time=(start_key, start_key), query=True, inAngle=True)[0]
            start_in_weight = cmds.keyTangent(curve, time=(start_key, start_key), query=True, inWeight=True)[0]
            start_out_angle = cmds.keyTangent(curve, time=(start_key, start_key), query=True, outAngle=True)[0]
            start_out_weight = cmds.keyTangent(curve, time=(start_key, start_key), query=True, outWeight=True)[0]
            
            # Apply EXACT same tangents to end key (perfect match)
            cmds.keyTangent(curve, time=(end_key, end_key), 
                          inAngle=start_in_angle, inWeight=start_in_weight,
                          outAngle=start_out_angle, outWeight=start_out_weight,
                          inTangentType='fixed', outTangentType='fixed')
            
            # Now make start key in-tangent match end key out-tangent for cycling continuity
            cmds.keyTangent(curve, time=(start_key, start_key), 
                          inAngle=start_out_angle, inWeight=start_out_weight,
                          inTangentType='fixed')
            
            print(f"DEBUG: Applied exact tangent matching:")
            print(f"  End key in/out: {start_in_angle:.1f}°/{start_out_angle:.1f}° (matches start key)")
            print(f"  Start key in: {start_out_angle:.1f}° (matches own out-tangent for cycling)")
            
        except Exception as e:
            print(f"DEBUG: Error in directional cycle tangents: {e}")
    

            
    def copy_with_direction(self, *_):
        """Copy animation based on current selection - left controls copy to right, right controls copy to left."""
        try:
            # Get current selection
            selected_objects = cmds.ls(selection=True, type='transform')
            
            if not selected_objects:
                # No selection - default to left to right
                print("No objects selected. Defaulting to left-to-right copy.")
                self.copy_left_to_right()
                return
            
            # Analyze selection to determine direction
            left_selected = 0
            right_selected = 0
            
            for obj in selected_objects:
                if obj in self.left_controls:
                    left_selected += 1
                elif obj in self.right_controls:
                    right_selected += 1
                else:
                    # Check if it's a left or right control by name patterns
                    if self.is_left(obj):
                        left_selected += 1
                    elif self.is_right(obj):
                        right_selected += 1
            
            # Determine direction based on selection
            if left_selected > right_selected:
                print(f"Left controls selected ({left_selected}). Copying left to right.")
                self.copy_left_to_right()
            elif right_selected > left_selected:
                print(f"Right controls selected ({right_selected}). Copying right to left.")
                self.copy_right_to_left()
            elif left_selected == right_selected and left_selected > 0:
                print(f"Equal left/right selection ({left_selected} each). Defaulting to left-to-right copy.")
                self.copy_left_to_right()
            else:
                # No recognizable left/right controls - default to left to right
                print("No recognizable left/right controls in selection. Defaulting to left-to-right copy.")
                self.copy_left_to_right()
                
        except Exception as e:
            cmds.warning(f"Copy with direction failed: {e}")

    def contain_curve_within_time_range(self, curve_attr):
        """
        Takes a cyclical animation curve and recreates it within the time range using copy/paste operations.
        This maintains the exact same animation look but creates real keys within the time range.
        
        Args:
            curve_attr: The attribute name (e.g., "pCube1.translateX") to process
        """
        
        # Get the current time range
        start_time = int(cmds.playbackOptions(query=True, minTime=True))
        end_time = int(cmds.playbackOptions(query=True, maxTime=True))
        
        print(f"Fitting curve {curve_attr} to time range: {start_time} to {end_time}")
        
        # Get the animation curve for this attribute
        curve_name = self._anim_curve_for_attr(curve_attr)
        if not curve_name:
            print(f"No animation curve found for {curve_attr}")
            return
        
        # Get all keyframes on the curve
        all_times = cmds.keyframe(curve_name, query=True, timeChange=True)
        
        if not all_times:
            print(f"No keyframes found on curve {curve_name}")
            return
        
        print(f"Original curve has {len(all_times)} keyframes from {min(all_times)} to {max(all_times)}")
        
        # First, ensure there's a keyframe at the end of the time range
        # This will sample the curve value at that time and create a key
        try:
            cmds.setKeyframe(curve_attr, time=end_time)
            print(f"Created keyframe at frame {end_time}")
        except Exception as e:
            print(f"Warning: Failed to set keyframe at end time: {e}")
            return
        
        # Refresh the keyframe list to include the new key
        all_times = cmds.keyframe(curve_name, query=True, timeChange=True)
        
        # Find keyframes that are at the end of time range and beyond
        keys_to_copy = []
        for time in all_times:
            if time >= end_time:
                keys_to_copy.append(int(time))
        
        if not keys_to_copy:
            print("No keyframes found at or beyond the end of the time range")
            return
        
        print(f"Found {len(keys_to_copy)} keyframes to copy: {keys_to_copy}")
        
        # Copy the selected keyframes directly from the attribute
        try:
            cmds.copyKey(curve_attr, time=(min(keys_to_copy), max(keys_to_copy)), includeUpperBound=True)
            print("Copied keyframes")
        except Exception as e:
            print(f"Warning: Failed to copy keyframes: {e}")
            return
        
        # Paste the keyframes at start time with merge option
        try:
            cmds.pasteKey(curve_attr, 
                         time=(start_time, start_time),
                         option="merge",
                         copies=1,
                         connect=False,
                         timeOffset=0,
                         floatOffset=0,
                         valueOffset=0)
            print(f"Pasted keyframes at current time {start_time}")
        except Exception as e:
            print(f"Warning: Failed to paste keyframes: {e}")
            return
        
        # Remove keyframes beyond the end time
        keys_beyond_range = []
        all_times = cmds.keyframe(curve_name, query=True, timeChange=True)  # Refresh after paste
        for time in all_times:
            if time > end_time:
                keys_beyond_range.append(time)
        
        if keys_beyond_range:
            print(f"Removing keyframes beyond time range: {keys_beyond_range}")
            try:
                cmds.cutKey(curve_attr, time=(min(keys_beyond_range), max(keys_beyond_range)), clear=True)
                print("Removed keyframes beyond time range")
            except Exception as e:
                print(f"Warning: Could not remove some keyframes: {e}")
        
        print(f"Successfully fitted curve {curve_attr} within time range")

    def open_settings_dialog(self, *_):
        """Open the settings dialog window."""
        settings_window = "CycleMakerSettings"
        
        # Close existing settings window if it exists
        if cmds.window(settings_window, exists=True):
            cmds.deleteUI(settings_window, window=True)
        
        # Create settings window
        cmds.window(settings_window, title="Cycle Maker Settings", widthHeight=(400, 300))
        cmds.columnLayout(adjustableColumn=True, rowSpacing=10, columnOffset=['both', 10])
        
        cmds.text(label="Cycle Maker Settings", font="boldLabelFont", height=30)
        cmds.separator(height=10, style="in")
        
        # Character Setup Settings
        cmds.frameLayout(label="Character Setup", collapsable=False, 
                        marginHeight=8, marginWidth=8, borderVisible=True,
                        backgroundColor=(0.45, 0.42, 0.38))
        cmds.columnLayout(adjustableColumn=True, rowSpacing=8)
        
        # Forward Direction dropdown
        cmds.rowLayout(numberOfColumns=2, columnWidth2=(150, 200))
        cmds.text(label="Forward Direction:", align="left")
        forward_dropdown = cmds.optionMenu()
        cmds.menuItem(label='X')
        cmds.menuItem(label='Y') 
        cmds.menuItem(label='Z')
        cmds.optionMenu(forward_dropdown, edit=True, value=self.forward_direction)
        cmds.setParent('..')
        
        # Forward Rotation Axis dropdown
        cmds.rowLayout(numberOfColumns=2, columnWidth2=(150, 200))
        cmds.text(label="Forward Rotation Axis:", align="left")
        rotation_dropdown = cmds.optionMenu()
        cmds.menuItem(label='X')
        cmds.menuItem(label='Y')
        cmds.menuItem(label='Z')
        cmds.optionMenu(rotation_dropdown, edit=True, value=self.forward_rotation_axis)
        cmds.setParent('..')
        
        cmds.setParent('..')  # columnLayout
        cmds.setParent('..')  # frameLayout
        
        # Animation Options
        cmds.frameLayout(label="Animation Options", collapsable=False, 
                        marginHeight=8, marginWidth=8, borderVisible=True,
                        backgroundColor=(0.42, 0.48, 0.42))
        cmds.columnLayout(adjustableColumn=True, rowSpacing=8)
        
        # Fit Curve to Timeline checkbox
        fit_curve_checkbox = cmds.checkBox(label="Fit Curve to Timeline (Default)", 
                                         value=self.fit_curve_default,
                                         annotation="Default state for automatically fitting animation curves within timeline range")
        
        # Auto-detect inversions checkbox
        auto_detect_checkbox = cmds.checkBox(label="Autodetect Mirrored Axis Alignments", 
                                           value=self.auto_detect_inversions,
                                           annotation="Automatically detect which axes should be inverted for left/right mirroring")
        
        cmds.setParent('..')  # columnLayout  
        cmds.setParent('..')  # frameLayout
        
        cmds.separator(height=15, style="in")
        
        # Buttons
        cmds.rowLayout(numberOfColumns=3, columnWidth3=(120, 120, 120))
        cmds.button(label="Apply", width=110, height=30,
                   backgroundColor=(0.42, 0.48, 0.42),
                   command=lambda x: self._apply_settings(forward_dropdown, rotation_dropdown, fit_curve_checkbox, auto_detect_checkbox, settings_window))
        cmds.button(label="Cancel", width=110, height=30,
                   backgroundColor=(0.48, 0.42, 0.42),
                   command=lambda x: cmds.deleteUI(settings_window, window=True))
        cmds.button(label="Reset to Defaults", width=110, height=30,
                   backgroundColor=(0.48, 0.45, 0.42),
                   command=lambda x: self._reset_settings_to_defaults(forward_dropdown, rotation_dropdown, fit_curve_checkbox, auto_detect_checkbox))
        cmds.setParent('..')
        
        cmds.setParent('..')  # main columnLayout
        cmds.showWindow(settings_window)

    def _apply_settings(self, forward_dropdown, rotation_dropdown, fit_curve_checkbox, auto_detect_checkbox, settings_window):
        """Apply the settings from the dialog."""
        self.forward_direction = cmds.optionMenu(forward_dropdown, query=True, value=True)
        self.forward_rotation_axis = cmds.optionMenu(rotation_dropdown, query=True, value=True)  
        self.fit_curve_default = cmds.checkBox(fit_curve_checkbox, query=True, value=True)
        self.auto_detect_inversions = cmds.checkBox(auto_detect_checkbox, query=True, value=True)
        
        print(f"Settings applied: Forward={self.forward_direction}, Rotation={self.forward_rotation_axis}, FitCurve={self.fit_curve_default}, AutoDetect={self.auto_detect_inversions}")
        cmds.deleteUI(settings_window, window=True)
        
        # Show confirmation
        cmds.inViewMessage(amg="Settings applied successfully", pos='midCenter', fade=True)

    def _reset_settings_to_defaults(self, forward_dropdown, rotation_dropdown, fit_curve_checkbox, auto_detect_checkbox):
        """Reset settings to default values."""
        cmds.optionMenu(forward_dropdown, edit=True, value='Z')
        cmds.optionMenu(rotation_dropdown, edit=True, value='X')
        cmds.checkBox(fit_curve_checkbox, edit=True, value=True)
        cmds.checkBox(auto_detect_checkbox, edit=True, value=True)

# =========================================================================
# MAIN EXECUTION
# =========================================================================

def launch_cycle_maker():
    """Launch the Cycle Maker UI."""
    try:
        # Close existing window if it exists
        if cmds.window("CycleMakerWindow", exists=True):
            cmds.deleteUI("CycleMakerWindow", window=True)
        
        # Create and show the UI
        ui = CycleMakerUI()
        print("Cycle Maker UI launched successfully!")
        return ui
    except Exception as e:
        print(f"Error launching Cycle Maker UI: {e}")
        return None

# For direct execution in Maya
if __name__ == "__main__" or "maya" in globals():
    launch_cycle_maker()
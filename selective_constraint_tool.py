"""
Selective Constraint Tool for Maya
Constrains selected objects to the first selected object with customizable attribute control.
"""

import maya.cmds as cmds

class SelectiveConstraintTool:
    def __init__(self):
        self.window_name = "SelectiveConstraintWin"
        self.window_title = "Selective Constraint Tool"
        
    def create_ui(self):
        if cmds.window(self.window_name, exists=True):
            cmds.deleteUI(self.window_name, window=True)
        
        self.window = cmds.window(
            self.window_name,
            title=self.window_title,
            widthHeight=(400, 500),
            sizeable=True
        )
        
        cmds.columnLayout(adjustableColumn=True, rowSpacing=10, columnAttach=('both', 10))
        
        # Header
        cmds.separator(height=10, style="none")
        cmds.text(label="SELECTIVE CONSTRAINT TOOL", font="boldLabelFont", height=25)
        cmds.separator(height=10, style="in")
        
        # Selection info
        cmds.frameLayout(label="Current Selection", collapsable=False, marginHeight=10, marginWidth=10)
        cmds.columnLayout(adjustableColumn=True, rowSpacing=5)
        self.selection_field = cmds.scrollField(
            wordWrap=True, 
            height=80, 
            editable=False, 
            backgroundColor=(0.2, 0.2, 0.2)
        )
        cmds.button(label="Refresh Selection", command=self.refresh_selection, height=30)
        cmds.setParent('..')
        cmds.setParent('..')
        
        # Translate Constraints
        cmds.frameLayout(label="Translate Constraints", collapsable=False, marginHeight=10, marginWidth=10)
        cmds.columnLayout(adjustableColumn=True, rowSpacing=3)
        cmds.rowLayout(numberOfColumns=4, columnWidth4=(80, 80, 80, 80))
        cmds.text(label="")
        self.translate_x_cb = cmds.checkBox(label="X", value=True)
        self.translate_y_cb = cmds.checkBox(label="Y", value=True)
        self.translate_z_cb = cmds.checkBox(label="Z", value=True)
        cmds.setParent('..')
        cmds.setParent('..')
        cmds.setParent('..')
        
        # Rotate Constraints
        cmds.frameLayout(label="Rotate Constraints", collapsable=False, marginHeight=10, marginWidth=10)
        cmds.columnLayout(adjustableColumn=True, rowSpacing=3)
        cmds.rowLayout(numberOfColumns=4, columnWidth4=(80, 80, 80, 80))
        cmds.text(label="")
        self.rotate_x_cb = cmds.checkBox(label="X", value=True)
        self.rotate_y_cb = cmds.checkBox(label="Y", value=True)
        self.rotate_z_cb = cmds.checkBox(label="Z", value=True)
        cmds.setParent('..')
        cmds.setParent('..')
        cmds.setParent('..')
        
        # Constraint Options
        cmds.frameLayout(label="Options", collapsable=False, marginHeight=10, marginWidth=10)
        cmds.columnLayout(adjustableColumn=True, rowSpacing=5)
        self.maintain_offset_cb = cmds.checkBox(label="Maintain Offset", value=True)
        cmds.setParent('..')
        cmds.setParent('..')
        
        # Action buttons
        cmds.separator(height=10, style="in")
        cmds.button(
            label="Apply Constraints", 
            command=self.apply_constraints, 
            height=40, 
            backgroundColor=[0.3, 0.7, 0.3]
        )
        cmds.separator(height=5, style="none")
        cmds.button(
            label="Close", 
            command=self.close_window, 
            height=30,
            backgroundColor=[0.7, 0.3, 0.3]
        )
        cmds.separator(height=10, style="none")
        
        cmds.showWindow(self.window)
        self.refresh_selection()
    
    def refresh_selection(self, *args):
        """Update the selection display"""
        selection = cmds.ls(selection=True, long=False)
        
        if not selection:
            info = "No objects selected\n\nSelect multiple objects:\n- First object = constraint target\n- Remaining objects = constrained objects"
        elif len(selection) < 2:
            info = f"Selected: {len(selection)} object\n\n{selection[0]}\n\nNeed at least 2 objects:\n- First = target\n- Rest = constrained"
        else:
            info = f"Selected: {len(selection)} objects\n\n"
            info += f"TARGET: {selection[0]}\n\n"
            info += f"CONSTRAIN ({len(selection)-1}):\n"
            for obj in selection[1:6]:
                info += f"  • {obj}\n"
            if len(selection) > 6:
                info += f"  ... and {len(selection) - 6} more"
        
        cmds.scrollField(self.selection_field, edit=True, text=info)
    
    def apply_constraints(self, *args):
        """Apply constraints based on current settings"""
        selection = cmds.ls(selection=True, long=True)
        
        if len(selection) < 2:
            cmds.warning("Need at least 2 objects selected. First = target, rest = constrained.")
            cmds.confirmDialog(
                title="Invalid Selection",
                message="Please select at least 2 objects:\n\n• First object = constraint target\n• Remaining objects = objects to constrain",
                button=["OK"]
            )
            return
        
        # Get the target (first selected)
        target = selection[0]
        objects_to_constrain = selection[1:]
        
        # Get checkbox states
        translate_x = cmds.checkBox(self.translate_x_cb, query=True, value=True)
        translate_y = cmds.checkBox(self.translate_y_cb, query=True, value=True)
        translate_z = cmds.checkBox(self.translate_z_cb, query=True, value=True)
        rotate_x = cmds.checkBox(self.rotate_x_cb, query=True, value=True)
        rotate_y = cmds.checkBox(self.rotate_y_cb, query=True, value=True)
        rotate_z = cmds.checkBox(self.rotate_z_cb, query=True, value=True)
        maintain_offset = cmds.checkBox(self.maintain_offset_cb, query=True, value=True)
        
        # Build skip translate/rotate lists
        skip_translate = []
        if not translate_x:
            skip_translate.append('x')
        if not translate_y:
            skip_translate.append('y')
        if not translate_z:
            skip_translate.append('z')
        
        skip_rotate = []
        if not rotate_x:
            skip_rotate.append('x')
        if not rotate_y:
            skip_rotate.append('y')
        if not rotate_z:
            skip_rotate.append('z')
        
        # Check if any constraints are enabled
        has_translate = translate_x or translate_y or translate_z
        has_rotate = rotate_x or rotate_y or rotate_z
        
        if not has_translate and not has_rotate:
            cmds.warning("No constraint axes selected. Please enable at least one axis.")
            cmds.confirmDialog(
                title="No Constraints",
                message="Please enable at least one translate or rotate axis.",
                button=["OK"]
            )
            return
        
        # Apply constraints
        constrained_count = 0
        constraint_list = []
        
        for obj in objects_to_constrain:
            try:
                # Apply point constraint if any translate axes are enabled
                if has_translate:
                    point_constraint = cmds.pointConstraint(
                        target, 
                        obj, 
                        maintainOffset=maintain_offset,
                        skip=skip_translate
                    )
                    constraint_list.extend(point_constraint)
                
                # Apply orient constraint if any rotate axes are enabled
                if has_rotate:
                    orient_constraint = cmds.orientConstraint(
                        target, 
                        obj, 
                        maintainOffset=maintain_offset,
                        skip=skip_rotate
                    )
                    constraint_list.extend(orient_constraint)
                
                constrained_count += 1
                
            except Exception as e:
                cmds.warning(f"Could not constrain {obj.split('|')[-1]}: {e}")
        
        # Report results
        target_short = target.split('|')[-1]
        message = f"Constrained {constrained_count} object(s) to '{target_short}'\n\n"
        
        if has_translate:
            axes = [ax.upper() for ax in ['x', 'y', 'z'] if ax not in skip_translate]
            message += f"Point Constraint: {', '.join(axes)}\n"
        
        if has_rotate:
            axes = [ax.upper() for ax in ['x', 'y', 'z'] if ax not in skip_rotate]
            message += f"Orient Constraint: {', '.join(axes)}\n"
        
        message += f"\nMaintain Offset: {'Yes' if maintain_offset else 'No'}"
        message += f"\n\nCreated {len(constraint_list)} constraint(s)"
        
        print(f"\n=== Selective Constraint Tool ===")
        print(message.replace('\n', '\n'))
        
        cmds.confirmDialog(
            title="Constraints Applied",
            message=message,
            button=["OK"]
        )
        
        # Select the created constraints
        if constraint_list:
            cmds.select(constraint_list, replace=True)
    
    def close_window(self, *args):
        """Close the window"""
        if cmds.window(self.window_name, exists=True):
            cmds.deleteUI(self.window_name, window=True)

def show_selective_constraint_tool():
    """Launch the Selective Constraint Tool"""
    tool = SelectiveConstraintTool()
    tool.create_ui()

# Launch the tool
if __name__ == "__main__":
    show_selective_constraint_tool()
else:
    show_selective_constraint_tool()

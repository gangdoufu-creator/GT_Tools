"""
Constraint Detective
Detects and displays objects constrained to/by the selected object.
Shows parent, point, orient, scale, and aim constraints in both directions.
"""

import maya.cmds as cmds


def get_constraint_info(obj):
    """
    Get all constraint information for an object.
    
    Args:
        obj (str): Object to analyze
    
    Returns:
        dict: Dictionary with 'constrained_to' and 'constrained_by' lists
    """
    info = {
        'constrained_to': [],      # Objects that constrain this object
        'constrained_by': []        # Objects that this object constrains
    }
    
    constraint_types = ['parentConstraint', 'pointConstraint', 'orientConstraint', 
                        'scaleConstraint', 'aimConstraint', 'poleVectorConstraint']
    
    # Find constraints ON this object (what constrains it)
    # Check if this object has any constraint nodes as children
    relatives = cmds.listRelatives(obj, type=constraint_types, fullPath=False) or []
    seen_targets = set()
    
    for constraint in relatives:
        constraint_type = cmds.nodeType(constraint)
        constraint_name = constraint_type.replace('Constraint', '')
        
        # Get target list - these are the objects constraining this object
        target_list = cmds.listConnections(constraint + '.target', source=True, destination=False) or []
        
        for target in target_list:
            # Filter out the constraint node itself and the constrained object
            if target != obj and target != constraint and (target, constraint) not in seen_targets:
                seen_targets.add((target, constraint))
                info['constrained_to'].append({
                    'object': target,
                    'constraint_type': constraint_name,
                    'constraint_node': constraint
                })
    
    # Find objects that THIS object constrains (where this object is a target)
    # Search all constraints in the scene
    all_constraints = cmds.ls(type=constraint_types) or []
    seen_constrained = set()
    
    for constraint in all_constraints:
        # Get the constrained object (parent of the constraint node)
        parent = cmds.listRelatives(constraint, parent=True, fullPath=False)
        if not parent:
            continue
        
        constrained_obj = parent[0]
        
        # Check if our object is in the target list of this constraint
        target_list = cmds.listConnections(constraint + '.target', source=True, destination=False) or []
        
        if obj in target_list and constrained_obj != obj and (constrained_obj, constraint) not in seen_constrained:
            seen_constrained.add((constrained_obj, constraint))
            constraint_type = cmds.nodeType(constraint)
            constraint_name = constraint_type.replace('Constraint', '')
            
            info['constrained_by'].append({
                'object': constrained_obj,
                'constraint_type': constraint_name,
                'constraint_node': constraint
            })
    
    return info


class ConstraintDetectiveUI:
    def __init__(self):
        self.window = 'constraintDetectiveWindow'
        self.title = 'Constraint Detective'
        self.size = (500, 500)
        self.current_object = None
        self.constrained_to_list = None
        self.constrained_by_list = None
    
    def show(self):
        if cmds.window(self.window, exists=True):
            cmds.deleteUI(self.window)
        self.build_ui()
        cmds.showWindow(self.window)
    
    def build_ui(self):
        self.window = cmds.window(self.window, title=self.title, widthHeight=self.size, sizeable=True)
        main_layout = cmds.columnLayout(adjustableColumn=True, rowSpacing=5)
        
        cmds.separator(height=10, style="none")
        cmds.text(label='Constraint Detective', font='boldLabelFont', height=30)
        cmds.separator(height=10)
        
        # Selected object display
        cmds.rowLayout(numberOfColumns=3, columnWidth3=(120, 280, 80), adjustableColumn=2)
        cmds.text(label='Selected Object:', align='left')
        self.object_field = cmds.textField(editable=False, text='None')
        cmds.button(label='Analyze', command=self.analyze_selection, backgroundColor=[0.3, 0.6, 0.3])
        cmds.setParent('..')
        
        cmds.separator(height=10)
        
        # Constrained TO (what constrains this object)
        cmds.text(label='Constrained TO (objects constraining selected):', font='boldLabelFont', align='left')
        cmds.separator(height=5, style="none")
        
        cmds.rowLayout(numberOfColumns=2, columnWidth2=(400, 80))
        self.constrained_to_list = cmds.textScrollList(
            height=150,
            allowMultiSelection=True,
            selectCommand=self.on_to_select
        )
        
        cmds.columnLayout(adjustableColumn=False, rowSpacing=5)
        cmds.button(label='Select', width=80, command=self.select_constrained_to)
        cmds.button(label='Select All', width=80, command=self.select_all_constrained_to)
        cmds.button(label='Highlight', width=80, command=self.highlight_constrained_to, 
                   backgroundColor=[0.4, 0.5, 0.6])
        cmds.setParent('..')
        cmds.setParent('..')
        
        cmds.separator(height=10)
        
        # Constrained BY (what this object constrains)
        cmds.text(label='Constrained BY (objects constrained by selected):', font='boldLabelFont', align='left')
        cmds.separator(height=5, style="none")
        
        cmds.rowLayout(numberOfColumns=2, columnWidth2=(400, 80))
        self.constrained_by_list = cmds.textScrollList(
            height=150,
            allowMultiSelection=True,
            selectCommand=self.on_by_select
        )
        
        cmds.columnLayout(adjustableColumn=False, rowSpacing=5)
        cmds.button(label='Select', width=80, command=self.select_constrained_by)
        cmds.button(label='Select All', width=80, command=self.select_all_constrained_by)
        cmds.button(label='Highlight', width=80, command=self.highlight_constrained_by,
                   backgroundColor=[0.4, 0.5, 0.6])
        cmds.setParent('..')
        cmds.setParent('..')
        
        cmds.separator(height=10)
        
        # Info text
        cmds.text(label='Tip: Select an object and click Analyze to see its constraints', 
                 font='smallPlainLabelFont', align='center')
    
    def analyze_selection(self, *args):
        """Analyze the currently selected object."""
        sel = cmds.ls(selection=True)
        if not sel:
            cmds.warning('Please select an object to analyze.')
            return
        
        self.current_object = sel[0]
        cmds.textField(self.object_field, edit=True, text=self.current_object)
        
        # Get constraint info
        info = get_constraint_info(self.current_object)
        
        # Clear lists
        cmds.textScrollList(self.constrained_to_list, edit=True, removeAll=True)
        cmds.textScrollList(self.constrained_by_list, edit=True, removeAll=True)
        
        # Populate constrained TO list
        if info['constrained_to']:
            for item in info['constrained_to']:
                display = f"{item['object']} [{item['constraint_type']}] ({item['constraint_node']})"
                cmds.textScrollList(self.constrained_to_list, edit=True, append=display)
        else:
            cmds.textScrollList(self.constrained_to_list, edit=True, 
                               append='--- No constraints found ---')
        
        # Populate constrained BY list
        if info['constrained_by']:
            for item in info['constrained_by']:
                display = f"{item['object']} [{item['constraint_type']}] ({item['constraint_node']})"
                cmds.textScrollList(self.constrained_by_list, edit=True, append=display)
        else:
            cmds.textScrollList(self.constrained_by_list, edit=True, 
                               append='--- Not constraining anything ---')
        
        print(f"\n=== Constraint Analysis for: {self.current_object} ===")
        print(f"Constrained TO: {len(info['constrained_to'])} objects")
        print(f"Constrained BY: {len(info['constrained_by'])} objects")
    
    def on_to_select(self):
        """Called when items in constrained_to list are selected."""
        pass
    
    def on_by_select(self):
        """Called when items in constrained_by list are selected."""
        pass
    
    def select_constrained_to(self, *args):
        """Select the chosen constrained_to objects."""
        selected_items = cmds.textScrollList(self.constrained_to_list, query=True, selectItem=True)
        if selected_items and selected_items[0] != '--- No constraints found ---':
            objects = [item.split(' [')[0] for item in selected_items]
            cmds.select(objects, replace=True)
    
    def select_all_constrained_to(self, *args):
        """Select all constrained_to objects."""
        all_items = cmds.textScrollList(self.constrained_to_list, query=True, allItems=True)
        if all_items and all_items[0] != '--- No constraints found ---':
            objects = [item.split(' [')[0] for item in all_items]
            cmds.select(objects, replace=True)
    
    def highlight_constrained_to(self, *args):
        """Add constrained_to objects to current selection."""
        selected_items = cmds.textScrollList(self.constrained_to_list, query=True, selectItem=True)
        if selected_items and selected_items[0] != '--- No constraints found ---':
            objects = [item.split(' [')[0] for item in selected_items]
            cmds.select(objects, add=True)
    
    def select_constrained_by(self, *args):
        """Select the chosen constrained_by objects."""
        selected_items = cmds.textScrollList(self.constrained_by_list, query=True, selectItem=True)
        if selected_items and selected_items[0] != '--- Not constraining anything ---':
            objects = [item.split(' [')[0] for item in selected_items]
            cmds.select(objects, replace=True)
    
    def select_all_constrained_by(self, *args):
        """Select all constrained_by objects."""
        all_items = cmds.textScrollList(self.constrained_by_list, query=True, allItems=True)
        if all_items and all_items[0] != '--- Not constraining anything ---':
            objects = [item.split(' [')[0] for item in all_items]
            cmds.select(objects, replace=True)
    
    def highlight_constrained_by(self, *args):
        """Add constrained_by objects to current selection."""
        selected_items = cmds.textScrollList(self.constrained_by_list, query=True, selectItem=True)
        if selected_items and selected_items[0] != '--- Not constraining anything ---':
            objects = [item.split(' [')[0] for item in selected_items]
            cmds.select(objects, add=True)


def show_constraint_detective():
    """Launch the Constraint Detective UI."""
    ui = ConstraintDetectiveUI()
    ui.show()


# Execute when script is run directly
if __name__ == "__main__":
    show_constraint_detective()

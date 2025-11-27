"""
Constraint Manager
A professional tool for managing constraints in Maya scenes.

Features:
- Select constraining (source) objects from selected targets
- Select constraint nodes on selected objects
- Delete constraints with safety checks
- Undo support and comprehensive feedback

Author: Professional Pipeline Tools
"""

import maya.cmds as cmds


# ========================================
# Core Constraint Functions
# ========================================

def get_constraints_on_objects(objects):
    """
    Get all constraint nodes connected to the specified objects.
    
    Args:
        objects (list): List of Maya objects to check for constraints
        
    Returns:
        list: Constraint node names (long names)
    """
    if not objects:
        return []
    
    constraint_nodes = set()
    for obj in objects:
        # Get all constraint nodes connected to this object
        constraints = cmds.listConnections(
            obj, 
            type='constraint', 
            source=True, 
            destination=True
        ) or []
        
        # Convert to long names and add to set
        if constraints:
            long_names = cmds.ls(constraints, long=True)
            constraint_nodes.update(long_names)
    
    return list(constraint_nodes)


def select_constraint_sources():
    """
    For each selected object, finds and selects all source (driver) objects that constrain it.
    Only selects constraining objects, not the constraint node or the target itself.
    
    Returns:
        list: List of selected source objects
    """
    selection = cmds.ls(selection=True, long=True)
    if not selection:
        cmds.warning("Constraint Manager: Nothing selected. Please select constrained objects.")
        return []

    source_objs = set()
    selection_long = set(cmds.ls(selection, long=True))
    
    for obj in selection:
        # Get all constraints affecting this object
        constraints = cmds.listConnections(
            obj, 
            type='constraint', 
            destination=True, 
            source=False
        ) or []
        
        for constraint in constraints:
            # Try to get drivers from the target attribute
            drivers = cmds.listConnections(
                constraint + ".target", 
                source=True, 
                destination=False
            ) or []
            
            # Fallback: get all transform connections to the constraint
            if not drivers:
                drivers = cmds.listConnections(
                    constraint, 
                    source=True, 
                    destination=False, 
                    type='transform'
                ) or []
            
            # Filter to only valid source transforms
            drivers_long = cmds.ls(drivers, long=True) if drivers else []
            for drv in drivers_long:
                if drv not in selection_long and cmds.objExists(drv):
                    if cmds.nodeType(drv) == 'transform':
                        source_objs.add(drv)

    # Select the source constraining objects
    if source_objs:
        cmds.select(list(source_objs), replace=True)
        cmds.inViewMessage(
            amg=f'<hl>Selected {len(source_objs)} constraining object(s)</hl>', 
            pos='topCenter', 
            fade=True,
            fadeStayTime=2000,
            fadeOutTime=500
        )
    else:
        cmds.select(clear=True)
        cmds.warning("Constraint Manager: No constraining objects found for the selected object(s).")
    
    return list(source_objs)


def select_constraint_nodes():
    """
    Select all constraint nodes connected to the currently selected objects.
    
    Returns:
        list: List of selected constraint nodes
    """
    selection = cmds.ls(selection=True, long=True)
    if not selection:
        cmds.warning("Constraint Manager: Nothing selected. Please select objects to find their constraints.")
        return []
    
    constraints = get_constraints_on_objects(selection)
    
    if constraints:
        cmds.select(constraints, replace=True)
        cmds.inViewMessage(
            amg=f'<hl>Selected {len(constraints)} constraint node(s)</hl>', 
            pos='topCenter', 
            fade=True,
            fadeStayTime=2000,
            fadeOutTime=500
        )
    else:
        cmds.select(clear=True)
        cmds.warning("Constraint Manager: No constraints found on selected objects.")
    
    return constraints


def delete_constraints_safe(constraint_nodes, open_undo=True):
    """
    Safely delete constraint nodes with proper error handling.
    Skips constraints that are referenced or locked.
    
    Args:
        constraint_nodes (list): List of constraint nodes to delete
        open_undo (bool): Whether to open an undo chunk
        
    Returns:
        dict: Dictionary with 'deleted' and 'skipped' lists
    """
    if not constraint_nodes:
        return {'deleted': [], 'skipped': []}
    
    deleted = []
    skipped = []
    
    if open_undo:
        cmds.undoInfo(openChunk=True, chunkName='Delete Constraints')
    
    try:
        for node in constraint_nodes:
            if not cmds.objExists(node):
                skipped.append(node)
                continue
            
            # Check if referenced
            if cmds.referenceQuery(node, isNodeReferenced=True):
                cmds.warning(f"Constraint Manager: Skipping referenced constraint: {node}")
                skipped.append(node)
                continue
            
            # Check if locked
            if cmds.lockNode(node, query=True, lock=True)[0]:
                cmds.warning(f"Constraint Manager: Skipping locked constraint: {node}")
                skipped.append(node)
                continue
            
            try:
                cmds.delete(node)
                deleted.append(node)
            except Exception as e:
                cmds.warning(f"Constraint Manager: Could not delete {node}: {str(e)}")
                skipped.append(node)
    
    finally:
        if open_undo:
            cmds.undoInfo(closeChunk=True)
    
    return {'deleted': deleted, 'skipped': skipped}


def delete_constraints_on_selection():
    """
    Delete all constraints on the currently selected objects.
    
    Returns:
        dict: Results of deletion operation
    """
    selection = cmds.ls(selection=True, long=True)
    if not selection:
        cmds.warning("Constraint Manager: Nothing selected. Please select objects to delete their constraints.")
        return {'deleted': [], 'skipped': []}
    
    # Get all constraints on selection
    constraints = get_constraints_on_objects(selection)
    
    if not constraints:
        cmds.warning("Constraint Manager: No constraints found on selected objects.")
        return {'deleted': [], 'skipped': []}
    
    # Delete the constraints
    result = delete_constraints_safe(constraints)
    
    # Provide feedback
    msg_parts = []
    if result['deleted']:
        msg_parts.append(f"{len(result['deleted'])} constraint(s) deleted")
    if result['skipped']:
        msg_parts.append(f"{len(result['skipped'])} skipped")
    
    if msg_parts:
        cmds.inViewMessage(
            amg=f'<hl>{", ".join(msg_parts)}</hl>', 
            pos='topCenter', 
            fade=True,
            fadeStayTime=2500,
            fadeOutTime=500
        )
    
    # Reselect original objects
    valid_selection = [obj for obj in selection if cmds.objExists(obj)]
    if valid_selection:
        cmds.select(valid_selection, replace=True)
    
    return result


def delete_selected_constraints():
    """
    Delete the currently selected constraint nodes.
    Only deletes nodes that are actually constraint types.
    
    Returns:
        dict: Results of deletion operation
    """
    selection = cmds.ls(selection=True, long=True)
    if not selection:
        cmds.warning("Constraint Manager: Nothing selected. Please select constraint nodes to delete.")
        return {'deleted': [], 'skipped': []}
    
    # Filter to only constraint nodes
    constraint_nodes = []
    for node in selection:
        if cmds.objExists(node):
            node_type = cmds.nodeType(node)
            if 'Constraint' in node_type or node_type == 'constraint':
                constraint_nodes.append(node)
    
    if not constraint_nodes:
        cmds.warning("Constraint Manager: No constraint nodes in selection. Please select constraint nodes.")
        return {'deleted': [], 'skipped': []}
    
    # Delete the constraints
    result = delete_constraints_safe(constraint_nodes)
    
    # Provide feedback
    msg_parts = []
    if result['deleted']:
        msg_parts.append(f"{len(result['deleted'])} constraint(s) deleted")
    if result['skipped']:
        msg_parts.append(f"{len(result['skipped'])} skipped")
    
    if msg_parts:
        cmds.inViewMessage(
            amg=f'<hl>{", ".join(msg_parts)}</hl>', 
            pos='topCenter', 
            fade=True,
            fadeStayTime=2500,
            fadeOutTime=500
        )
    
    return result


# ========================================
# UI
# ========================================

def launch_constraint_manager_ui():
    """
    Launch the Constraint Manager UI.
    A professional tool for managing constraints in Maya scenes.
    """
    win = 'constraintManagerUI'
    
    # Close existing window
    if cmds.window(win, exists=True):
        cmds.deleteUI(win)
    
    # Create window
    cmds.window(
        win, 
        title='Constraint Manager', 
        widthHeight=(380, 220),
        sizeable=True
    )
    
    # Main layout
    main_layout = cmds.columnLayout(
        adjustableColumn=True, 
        rowSpacing=8, 
        columnOffset=('both', 12)
    )
    
    # Header
    cmds.separator(height=8, style='none')
    cmds.text(
        label='Constraint Manager', 
        font='boldLabelFont',
        align='center',
        height=25
    )
    cmds.separator(height=10, style='in')
    
    # Selection section
    cmds.text(
        label='Selection Tools:', 
        font='boldLabelFont',
        align='left',
        height=20
    )
    
    cmds.button(
        label='Select Constraining Objects', 
        height=35,
        backgroundColor=[0.28, 0.45, 0.65],
        annotation='Select all objects that are constraining the selected objects (drivers/sources)',
        command=lambda *_: select_constraint_sources()
    )
    
    cmds.button(
        label='Select Constraint Nodes', 
        height=35,
        backgroundColor=[0.35, 0.50, 0.60],
        annotation='Select all constraint nodes connected to the selected objects',
        command=lambda *_: select_constraint_nodes()
    )
    
    cmds.separator(height=10, style='in')
    
    cmds.separator(height=5, style='none')
    
    # Close button
    cmds.button(
        label='Close', 
        height=30,
        backgroundColor=[0.25, 0.25, 0.25],
        command=lambda *_: cmds.deleteUI(win)
    )
    
    cmds.separator(height=8, style='none')
    
    # Show window
    cmds.showWindow(win)


# ========================================
# Launch Function (for backwards compatibility)
# ========================================

def launch_constraint_source_ui():
    """Legacy function name - redirects to new UI."""
    launch_constraint_manager_ui()

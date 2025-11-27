"""
Character Time Warp Tool for Maya
Creates time warp nodes to non-linearly remap animation timing per character.

Usage:
    Select controls/objects from one or more characters, then run:
    import character_time_warp
    character_time_warp.ui()
"""

import maya.cmds as mc
from maya import OpenMaya

def get_namespaces_from_selection():
    """Get unique namespaces from current selection"""
    sel = mc.ls(sl=True)
    if not sel:
        return []
    
    namespaces = set()
    for obj in sel:
        if ':' in obj:
            namespace = obj.rsplit(':', 1)[0]
            namespaces.add(namespace)
        else:
            namespaces.add(':root')
    
    return sorted(list(namespaces))

def get_all_namespaces():
    """Get all namespaces in the scene"""
    all_ns = mc.namespaceInfo(listOnlyNamespaces=True, recurse=True) or []
    # Filter out UI and shared namespaces
    filtered = [ns for ns in all_ns if not ns.startswith('UI') and not ns.startswith('shared')]
    return filtered

def get_anim_curves_for_objects(objects):
    """Get all animation curves for given objects"""
    anim_curves = []
    for obj in objects:
        # Get all animation curves connected to this object
        curves = mc.listConnections(obj, type='animCurve', source=True, destination=False) or []
        anim_curves.extend(curves)
    
    return list(set(anim_curves))

def get_anim_curves_for_namespace(namespace):
    """Get all animation curves for objects in a namespace"""
    if namespace == ':root':
        # Get objects without namespace
        all_objects = mc.ls(transforms=True)
        objects = [obj for obj in all_objects if ':' not in obj]
    else:
        objects = mc.ls(namespace + ':*', type='transform')
    
    return get_anim_curves_for_objects(objects)

def create_time_warp(namespace=None, objects=None, name=None):
    """
    Create a time warp node and connect it to all animation curves for objects or namespace
    Uses Maya's built-in timeWarp node (from Bonus Tools) if available, otherwise animCurveTU
    
    Args:
        namespace: Character namespace (e.g., 'char1')
        objects: List of objects to apply timeWarp to (alternative to namespace)
        name: Custom name for the timeWarp node
    
    Returns: (timeWarp node name, number of curves connected)
    """
    # Determine what we're working with
    if objects:
        # Working with direct object selection
        if not name:
            name = 'timeWarp_selection'
        anim_curves = get_anim_curves_for_objects(objects)
        label = f'{len(objects)} selected objects'
    elif namespace:
        # Working with namespace
        if not name:
            clean_ns = namespace.replace(':', '_')
            name = f'timeWarp_{clean_ns}'
        anim_curves = get_anim_curves_for_namespace(namespace)
        label = f'namespace: {namespace}'
    else:
        OpenMaya.MGlobal.displayWarning('Must provide either objects or namespace.')
        return None, 0
    
    # Check if timeWarp already exists
    if mc.objExists(name):
        OpenMaya.MGlobal.displayWarning(f'TimeWarp node {name} already exists.')
        return name, 0
    
    if not anim_curves:
        OpenMaya.MGlobal.displayWarning(f'No animation curves found for {label}')
        return None, 0
    
    # Create animCurveTU node for time remapping
    # This creates an easily editable curve in the Graph Editor
    time_warp = mc.createNode('animCurveTU', name=name)
    
    # Set up default linear time warp curve (1:1 mapping)
    start_frame = mc.playbackOptions(query=True, minTime=True)
    end_frame = mc.playbackOptions(query=True, maxTime=True)
    
    # Set keyframes directly on the curve
    mc.setKeyframe(time_warp, time=start_frame, value=start_frame)
    mc.setKeyframe(time_warp, time=end_frame, value=end_frame)
    mc.keyTangent(time_warp, inTangentType='linear', outTangentType='linear')
    
    # Connect time1 to curve input
    mc.connectAttr('time1.outTime', f'{time_warp}.input', force=True)
    output_attr = f'{time_warp}.output'
    
    # Redirect each animation curve's input through the time warp
    connected_count = 0
    for curve in anim_curves:
        try:
            # Disconnect the original time connection
            time_conn = mc.listConnections(f'{curve}.input', source=True, destination=False, plugs=True)
            if time_conn:
                mc.disconnectAttr(time_conn[0], f'{curve}.input')
            
            # Connect time warp output to curve input
            mc.connectAttr(output_attr, f'{curve}.input', force=True)
            connected_count += 1
        except Exception as e:
            print(f'Warning: Could not connect {curve}: {e}')
    
    # Select the time warp curve so it can be edited in Graph Editor
    mc.select(time_warp)
    
    print(f'Created timeWarp: {time_warp} ({connected_count} curves connected)')
    print(f'Time warp curve selected. Open Graph Editor to edit the curve.')
    return time_warp, connected_count

def remove_time_warp(time_warp_node):
    """
    Remove a timeWarp node and restore direct time connections to animation curves
    
    Returns: number of curves reconnected
    """
    if not mc.objExists(time_warp_node):
        OpenMaya.MGlobal.displayWarning(f'TimeWarp node {time_warp_node} does not exist.')
        return 0
    
    # Get all animation curves connected to this timeWarp
    anim_curves = mc.listConnections(f'{time_warp_node}.output', source=False, destination=True, type='animCurve') or []
    
    reconnected_count = 0
    for curve in anim_curves:
        try:
            # Disconnect timeWarp
            mc.disconnectAttr(f'{time_warp_node}.output', f'{curve}.input')
            
            # Reconnect to time1
            mc.connectAttr('time1.outTime', f'{curve}.input', force=True)
            reconnected_count += 1
        except:
            pass
    
    # Delete the timeWarp node
    mc.delete(time_warp_node)
    
    print(f'Removed timeWarp: {time_warp_node} ({reconnected_count} curves reconnected)')
    return reconnected_count

def edit_time_warp_curve(time_warp_node):
    """Open the Graph Editor to edit the timeWarp curve"""
    if not mc.objExists(time_warp_node):
        OpenMaya.MGlobal.displayWarning(f'TimeWarp node {time_warp_node} does not exist.')
        return
    
    # Select the timeWarp node
    mc.select(time_warp_node, replace=True)
    
    # Open Graph Editor and isolate the curve
    try:
        # Open or focus Graph Editor
        graph_editor = mc.getPanel(scriptType='graphEditor')
        if not graph_editor:
            mc.GraphEditor()
        else:
            # Get the first graph editor panel
            mc.scriptedPanel(graph_editor[0], edit=True, control=True)
        
        print(f'Selected {time_warp_node} - you can now edit it in the Graph Editor')
    except Exception as e:
        print(f'Could not open Graph Editor: {e}')

def bake_time_warp(namespace, time_warp_node):
    """
    Bake the time-warped animation back to the original curves and remove the timeWarp
    
    Returns: number of curves baked
    """
    if not mc.objExists(time_warp_node):
        OpenMaya.MGlobal.displayWarning(f'TimeWarp node {time_warp_node} does not exist.')
        return 0
    
    # Get frame range
    start_frame = int(mc.playbackOptions(query=True, minTime=True))
    end_frame = int(mc.playbackOptions(query=True, maxTime=True))
    
    # Get all objects in namespace
    if namespace == ':root':
        all_objects = mc.ls(transforms=True)
        objects = [obj for obj in all_objects if ':' not in obj]
    else:
        objects = mc.ls(namespace + ':*', type='transform')
    
    if not objects:
        OpenMaya.MGlobal.displayWarning(f'No objects found for namespace: {namespace}')
        return 0
    
    # Bake simulation on all objects
    try:
        mc.bakeResults(objects, 
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
                      shape=False)
        
        # Remove the timeWarp
        num_curves = remove_time_warp(time_warp_node)
        
        print(f'Baked animation for {len(objects)} objects, removed timeWarp')
        return num_curves
    except Exception as e:
        OpenMaya.MGlobal.displayWarning(f'Failed to bake: {e}')
        return 0

def list_time_warps():
    """List all timeWarp nodes in the scene (animCurveTU nodes starting with 'timeWarp_')"""
    all_curves = mc.ls(type='animCurveTU') or []
    time_warps = [curve for curve in all_curves if curve.startswith('timeWarp_')]
    return time_warps

def ui():
    """User interface for Character Time Warp tool"""
    window_name = 'characterTimeWarp_UI'
    
    if mc.window(window_name, exists=True):
        mc.deleteUI(window_name)
    
    window = mc.window(window_name, title='Character Time Warp', width=400, height=500)
    
    main_layout = mc.columnLayout(adjustableColumn=True, rowSpacing=5)
    
    # Header
    mc.text(label='Character Time Warp Tool', font='boldLabelFont', height=30)
    mc.text(label='Apply non-linear time remapping to character animation using timeWarp nodes.')
    mc.separator(height=10)
    
    # Section 1: Create Time Warp
    mc.frameLayout(label='1. Create Time Warp', collapsable=True, collapse=False)
    mc.columnLayout(adjustableColumn=True, rowSpacing=3)
    
    mc.text(label='Select controls from character(s), then:', align='left')
    mc.button(label='Create Time Warp from Selection', 
              command=lambda *args: create_from_selection(),
              height=30,
              backgroundColor=[0.3, 0.6, 0.3])
    
    mc.separator(height=5)
    mc.text(label='Or create for all namespaces:', align='left')
    mc.button(label='Create Time Warp for All Characters',
              command=lambda *args: create_for_all(),
              height=25)
    
    mc.setParent('..')
    mc.setParent('..')
    
    # Section 2: Manage Time Warps
    mc.frameLayout(label='2. Manage Time Warps', collapsable=True, collapse=False)
    mc.columnLayout(adjustableColumn=True, rowSpacing=3)
    
    mc.text(label='Existing Time Warps:', align='left')
    
    # List of timeWarps
    global time_warp_list
    time_warp_list = mc.textScrollList('timeWarpList', 
                                       numberOfRows=8,
                                       allowMultiSelection=False,
                                       selectCommand=lambda: select_time_warp())
    
    mc.button(label='Refresh List', command=lambda *args: refresh_list())
    
    mc.separator(height=5)
    
    mc.rowLayout(numberOfColumns=2, columnWidth2=(195, 195), adjustableColumn=1)
    mc.button(label='Edit Curve (Graph Editor)',
              command=lambda *args: edit_selected_curve(),
              backgroundColor=[0.4, 0.5, 0.6])
    mc.button(label='Select TimeWarp Node',
              command=lambda *args: select_time_warp())
    mc.setParent('..')
    
    mc.separator(height=5)
    
    mc.rowLayout(numberOfColumns=2, columnWidth2=(195, 195), adjustableColumn=1)
    mc.button(label='Remove Time Warp',
              command=lambda *args: remove_selected(),
              backgroundColor=[0.6, 0.4, 0.3])
    mc.button(label='Bake and Remove',
              command=lambda *args: bake_selected(),
              backgroundColor=[0.5, 0.5, 0.3])
    mc.setParent('..')
    
    mc.setParent('..')
    mc.setParent('..')
    
    # Section 3: Info
    mc.frameLayout(label='Info', collapsable=True, collapse=True)
    mc.columnLayout(adjustableColumn=True)
    
    info_text = (
        "Time Warp allows you to speed up, slow down, or reverse animation.\n\n"
        "• The warpValue curve maps input time (X) to output time (Y)\n"
        "• Linear diagonal = normal speed\n"
        "• Steep slope = fast motion\n"
        "• Shallow slope = slow motion\n"
        "• Negative slope = reverse\n\n"
        "Workflow:\n"
        "1. Create timeWarp for your character(s)\n"
        "2. Edit the curve in Graph Editor\n"
        "3. Preview the results\n"
        "4. Bake when satisfied (optional)"
    )
    
    mc.text(label=info_text, align='left', wordWrap=True)
    
    mc.setParent('..')
    mc.setParent('..')
    
    mc.separator(height=10)
    mc.button(label='Close', command=lambda *args: mc.deleteUI(window), height=25)
    
    mc.showWindow(window)
    mc.window(window, edit=True, width=400, height=500)
    
    # Initial refresh
    refresh_list()

def create_from_selection():
    """Create timeWarp nodes for selected objects or namespaces"""
    selection = mc.ls(sl=True, type='transform')
    
    if not selection:
        OpenMaya.MGlobal.displayWarning('No objects selected.')
        return
    
    # First try to create timeWarp directly from selected objects
    anim_curves = get_anim_curves_for_objects(selection)
    
    if anim_curves:
        # Create a single timeWarp for the selected objects
        result = create_time_warp(objects=selection)
        if result[0]:
            mc.confirmDialog(title='Success', 
                            message=f'Created timeWarp node: {result[0]}\nAffecting {result[1]} animation curves',
                            button=['OK'])
            refresh_list()
        else:
            mc.confirmDialog(title='Warning',
                            message='No timeWarp node created. Check Script Editor for details.',
                            button=['OK'])
    else:
        # Fallback: try to get namespaces from selection
        namespaces = get_namespaces_from_selection()
        
        if not namespaces:
            OpenMaya.MGlobal.displayWarning('No animation curves found on selected objects and no namespaces detected.')
            return
        
        created = []
        for ns in namespaces:
            result = create_time_warp(namespace=ns)
            if result[0]:
                created.append(result[0])
        
        if created:
            mc.confirmDialog(title='Success', 
                            message=f'Created {len(created)} timeWarp node(s):\n' + '\n'.join(created),
                            button=['OK'])
            refresh_list()
        else:
            mc.confirmDialog(title='Warning',
                            message='No timeWarp nodes created. Check Script Editor for details.',
                            button=['OK'])

def create_for_all():
    """Create timeWarp for all namespaces in scene"""
    namespaces = get_all_namespaces()
    
    if not namespaces:
        mc.confirmDialog(title='Info',
                        message='No namespaces found in scene.',
                        button=['OK'])
        return
    
    created = []
    for ns in namespaces:
        result = create_time_warp(ns)
        if result[0]:
            created.append(result[0])
    
    if created:
        mc.confirmDialog(title='Success',
                        message=f'Created {len(created)} timeWarp node(s):\n' + '\n'.join(created),
                        button=['OK'])
        refresh_list()

def refresh_list():
    """Refresh the list of timeWarp nodes"""
    time_warps = list_time_warps()
    mc.textScrollList('timeWarpList', edit=True, removeAll=True)
    
    if time_warps:
        for tw in time_warps:
            # Get number of connected curves
            curves = mc.listConnections(f'{tw}.output', source=False, destination=True, type='animCurve') or []
            label = f'{tw} ({len(curves)} curves)'
            mc.textScrollList('timeWarpList', edit=True, append=label)

def get_selected_time_warp():
    """Get the selected timeWarp node from the list"""
    sel = mc.textScrollList('timeWarpList', query=True, selectItem=True)
    if not sel:
        OpenMaya.MGlobal.displayWarning('Please select a timeWarp from the list.')
        return None
    
    # Extract node name (remove curve count)
    node_name = sel[0].split(' (')[0]
    return node_name

def select_time_warp():
    """Select the timeWarp node in Maya"""
    node = get_selected_time_warp()
    if node:
        mc.select(node, replace=True)

def edit_selected_curve():
    """Edit the selected timeWarp curve"""
    node = get_selected_time_warp()
    if node:
        edit_time_warp_curve(node)

def remove_selected():
    """Remove the selected timeWarp"""
    node = get_selected_time_warp()
    if not node:
        return
    
    result = mc.confirmDialog(title='Confirm',
                              message=f'Remove timeWarp: {node}?',
                              button=['Yes', 'Cancel'],
                              defaultButton='Yes',
                              cancelButton='Cancel')
    
    if result == 'Yes':
        remove_time_warp(node)
        refresh_list()

def bake_selected():
    """Bake and remove the selected timeWarp"""
    node = get_selected_time_warp()
    if not node:
        return
    
    # Extract namespace from node name
    namespace = node.replace('timeWarp_', '').replace('_', ':')
    
    result = mc.confirmDialog(title='Confirm',
                              message=f'Bake animation and remove timeWarp: {node}?\nThis cannot be undone.',
                              button=['Yes', 'Cancel'],
                              defaultButton='Cancel',
                              cancelButton='Cancel')
    
    if result == 'Yes':
        bake_time_warp(namespace, node)
        refresh_list()
        mc.confirmDialog(title='Success',
                        message='Animation baked and timeWarp removed.',
                        button=['OK'])

# Launch UI when run as main
if __name__ == '__main__':
    ui()

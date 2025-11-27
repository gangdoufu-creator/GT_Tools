"""
Time Warp Tool
Create and manage time warp nodes for selected animated objects
"""

import maya.cmds as mc

# Global variables
WINDOW_NAME = 'timeWarpToolWindow'

def get_anim_curves_for_objects(objects):
    """Get all animation curves connected to given objects"""
    anim_curves = []
    for obj in objects:
        # Get curves connected directly or through attributes
        curves = mc.listConnections(obj, type='animCurve', source=True, destination=False) or []
        anim_curves.extend(curves)
        
        # Also check all attributes for animation curves
        attrs = mc.listAttr(obj, keyable=True) or []
        for attr in attrs:
            try:
                curve_conn = mc.listConnections(f'{obj}.{attr}', type='animCurve', source=True, destination=False) or []
                anim_curves.extend(curve_conn)
            except:
                pass
    
    return list(set(anim_curves))

def list_time_warps():
    """List all timeWarp nodes in the scene"""
    all_curves = mc.ls(type='animCurveTU') or []
    time_warps = [curve for curve in all_curves if curve.startswith('timeWarp_')]
    return time_warps

def create_time_warp_from_selection():
    """Create a time warp node for selected objects' animation curves"""
    selection = mc.ls(sl=True, type='transform')
    
    if not selection:
        mc.warning("Please select animated objects.")
        return None
    
    # Get all animation curves from selection
    anim_curves = get_anim_curves_for_objects(selection)
    
    if not anim_curves:
        mc.warning(f"No animation curves found on {len(selection)} selected object(s).")
        return None
    
    # Create a unique name
    time_warp_name = "timeWarp_selection"
    if mc.objExists(time_warp_name):
        time_warp_name = mc.createNode('animCurveTU', name="timeWarp_selection_#")
    else:
        time_warp_name = mc.createNode('animCurveTU', name=time_warp_name)
    
    # Set up default linear time warp curve (1:1 mapping)
    start_frame = mc.playbackOptions(query=True, minTime=True)
    end_frame = mc.playbackOptions(query=True, maxTime=True)
    
    mc.setKeyframe(time_warp_name, time=start_frame, value=start_frame)
    mc.setKeyframe(time_warp_name, time=end_frame, value=end_frame)
    mc.keyTangent(time_warp_name, inTangentType='linear', outTangentType='linear')
    
    # Connect time1 to curve input
    mc.connectAttr('time1.outTime', f'{time_warp_name}.input', force=True)
    
    # Redirect animation curves through the time warp
    connected_count = 0
    for curve in anim_curves:
        try:
            # Disconnect the original time connection
            time_conn = mc.listConnections(f'{curve}.input', source=True, destination=False, plugs=True)
            if time_conn:
                mc.disconnectAttr(time_conn[0], f'{curve}.input')
            
            # Connect time warp output to curve input
            mc.connectAttr(f'{time_warp_name}.output', f'{curve}.input', force=True)
            connected_count += 1
        except Exception as e:
            print(f'Warning: Could not connect {curve}: {e}')
    
    # Select the time warp curve
    mc.select(time_warp_name)
    
    print(f'Created timeWarp: {time_warp_name} ({connected_count} curves connected)')
    print(f'Open Graph Editor to edit the time warp curve')
    
    refresh_list()
    refresh_objects_list()
    return time_warp_name

def get_objects_from_time_warp(time_warp_node):
    """Get all objects affected by a time warp node"""
    if not mc.objExists(time_warp_node):
        return []
    
    # Get all animation curves connected to this timeWarp
    anim_curves = mc.listConnections(f'{time_warp_node}.output', source=False, destination=True, type='animCurve') or []
    
    # Get objects from curves
    objects_set = set()
    for curve in anim_curves:
        # Get the attribute/object this curve is connected to
        connections = mc.listConnections(curve, source=False, destination=True, plugs=True) or []
        for conn in connections:
            obj = conn.split('.')[0]
            # Only add transform nodes (not constraint nodes or other utility nodes)
            if mc.objExists(obj):
                node_type = mc.nodeType(obj)
                if node_type == 'transform' or mc.listRelatives(obj, parent=True):
                    objects_set.add(obj)
    
    return sorted(list(objects_set))

def remove_objects_from_time_warp(time_warp_node, objects):
    """Remove specific objects from a time warp (restore their direct time connection)"""
    if not mc.objExists(time_warp_node):
        mc.warning(f'TimeWarp node {time_warp_node} does not exist.')
        return 0
    
    # Get all animation curves connected to the time warp
    time_warp_curves = mc.listConnections(f'{time_warp_node}.output', source=False, destination=True, type='animCurve') or []
    print(f'Time warp has {len(time_warp_curves)} curves connected: {time_warp_curves[:5]}...')
    
    # Get animation curves for the specified objects
    object_curves = get_anim_curves_for_objects(objects)
    print(f'Selected objects have {len(object_curves)} curves: {object_curves[:5]}...')
    
    # Find curves that are both on the objects AND connected to the time warp
    curves_to_reconnect = [curve for curve in object_curves if curve in time_warp_curves]
    print(f'Found {len(curves_to_reconnect)} matching curves to reconnect')
    
    reconnected_count = 0
    for curve in curves_to_reconnect:
        try:
            # Disconnect timeWarp from curve
            mc.disconnectAttr(f'{time_warp_node}.output', f'{curve}.input')
            
            # Reconnect time1 directly to curve
            mc.connectAttr('time1.outTime', f'{curve}.input', force=True)
            reconnected_count += 1
        except Exception as e:
            print(f'Warning: Could not reconnect {curve}: {e}')
    
    if reconnected_count == 0:
        mc.warning(f'No animation curves found on selected objects that are connected to {time_warp_node}')
    else:
        print(f'Removed {len(objects)} object(s) from timeWarp: {time_warp_node} ({reconnected_count} curves reconnected)')
    
    return reconnected_count

def remove_time_warp(time_warp_node):
    """Remove a timeWarp node and restore direct time connections"""
    if not mc.objExists(time_warp_node):
        mc.warning(f'TimeWarp node {time_warp_node} does not exist.')
        return 0
    
    # Get all animation curves connected to this timeWarp
    anim_curves = mc.listConnections(f'{time_warp_node}.output', source=False, destination=True, type='animCurve') or []
    
    reconnected_count = 0
    for curve in anim_curves:
        try:
            # Disconnect timeWarp from curve
            mc.disconnectAttr(f'{time_warp_node}.output', f'{curve}.input')
            
            # Reconnect time1 directly to curve
            mc.connectAttr('time1.outTime', f'{curve}.input', force=True)
            reconnected_count += 1
        except Exception as e:
            print(f'Warning: Could not reconnect {curve}: {e}')
    
    # Delete the timeWarp node
    mc.delete(time_warp_node)
    
    print(f'Removed timeWarp: {time_warp_node} ({reconnected_count} curves reconnected)')
    refresh_list()
    return reconnected_count

def bake_time_warp(time_warp_node):
    """Bake animation through time warp and remove the time warp"""
    if not mc.objExists(time_warp_node):
        mc.warning(f'TimeWarp node {time_warp_node} does not exist.')
        return 0
    
    # Get frame range first
    start_frame = int(mc.playbackOptions(query=True, minTime=True))
    end_frame = int(mc.playbackOptions(query=True, maxTime=True))
    
    # The time warp connects to unitToTimeConversion nodes, which then connect to animation curves
    # We need to follow the chain: timeWarp -> unitToTimeConversion -> animCurve -> object
    
    # Get what's connected to the timeWarp output
    downstream_nodes = mc.listConnections(f'{time_warp_node}.output', source=False, destination=True) or []
    
    if not downstream_nodes:
        mc.warning(f'No nodes connected to {time_warp_node}')
        return 0
    
    print(f'TimeWarp connects to {len(downstream_nodes)} downstream nodes')
    
    # Follow through unitToTimeConversion nodes to find animation curves
    anim_curves = []
    for node in downstream_nodes:
        # Check if this is a unitToTimeConversion node
        if mc.nodeType(node) == 'unitToTimeConversion':
            # Get what this conversion node connects to (should be animation curves)
            curves = mc.listConnections(node, source=False, destination=True, type='animCurve') or []
            anim_curves.extend(curves)
        elif mc.nodeType(node).startswith('animCurve'):
            # Direct connection to anim curve
            anim_curves.append(node)
    
    anim_curves = list(set(anim_curves))
    print(f'Found {len(anim_curves)} animation curves through the chain')
    
    if not anim_curves:
        mc.warning(f'No animation curves found downstream of {time_warp_node}')
        return 0
    
    # Get unique objects from these curves
    objects = set()
    for curve in anim_curves:
        # Get what this curve is driving (output connections)
        connections = mc.listConnections(curve, source=False, destination=True, plugs=True) or []
        for conn in connections:
            obj = conn.split('.')[0]
            if mc.objExists(obj):
                node_type = mc.nodeType(obj)
                if node_type == 'transform':
                    objects.add(obj)
    
    objects = list(objects)
    
    if not objects:
        mc.warning(f'No objects found for time warp: {time_warp_node}')
        return 0
    
    print(f'Baking {len(objects)} objects from frame {start_frame} to {end_frame}: {objects}')
    
    # Bake the objects
    try:
        mc.bakeResults(objects,
                      time=(start_frame, end_frame),
                      sampleBy=1)
        
        print(f'Bake complete!')
        
        # Remove the timeWarp node if it still exists (bakeResults might have already removed it)
        if mc.objExists(time_warp_node):
            mc.delete(time_warp_node)
            print(f'Removed timeWarp node: {time_warp_node}')
        else:
            print(f'TimeWarp node was automatically cleaned up during bake')
        
        refresh_list()
        print(f'Success! Baked {len(objects)} object(s)')
        return len(objects)
    except Exception as e:
        mc.warning(f'Failed to bake: {e}')
        return 0

def select_time_warp():
    """Select the time warp node from the list"""
    selected = mc.textScrollList('timeWarpList', query=True, selectItem=True)
    if selected:
        mc.select(selected[0], replace=True)
        print(f'Selected: {selected[0]}')

def edit_time_warp():
    """Select the time warp and open Graph Editor"""
    selected = mc.textScrollList('timeWarpList', query=True, selectItem=True)
    if not selected:
        mc.warning("Please select a time warp from the list.")
        return
    
    time_warp_node = selected[0]
    mc.select(time_warp_node, replace=True)
    
    # Open Graph Editor
    try:
        graph_editor = mc.getPanel(scriptType='graphEditor')
        if not graph_editor:
            mc.GraphEditor()
        print(f'Selected {time_warp_node} - edit it in the Graph Editor')
    except:
        print(f'Selected {time_warp_node} - open Graph Editor (Windows > Animation Editors > Graph Editor)')

def remove_selected_objects_from_time_warp():
    """Remove currently selected objects from the time warp"""
    tw_selected = mc.textScrollList('timeWarpList', query=True, selectItem=True)
    if not tw_selected:
        mc.warning("Please select a time warp from the list.")
        return
    
    selection = mc.ls(sl=True, type='transform')
    if not selection:
        mc.warning("Please select objects to remove from the time warp.")
        return
    
    result = mc.confirmDialog(
        title='Confirm Remove Objects',
        message=f'Remove {len(selection)} selected object(s) from {tw_selected[0]}?',
        button=['Yes', 'No'],
        defaultButton='Yes',
        cancelButton='No',
        dismissString='No'
    )
    
    if result == 'Yes':
        remove_objects_from_time_warp(tw_selected[0], selection)
        refresh_objects_list()
        mc.confirmDialog(title='Success', message='Objects removed from time warp.', button=['OK'])

def remove_selected_time_warp():
    """Remove the selected time warp from the list"""
    selected = mc.textScrollList('timeWarpList', query=True, selectItem=True)
    if not selected:
        mc.warning("Please select a time warp from the list to remove.")
        return
    
    result = mc.confirmDialog(
        title='Confirm Remove',
        message=f'Remove time warp: {selected[0]}?\n\nThis will restore direct time connections.',
        button=['Yes', 'No'],
        defaultButton='Yes',
        cancelButton='No',
        dismissString='No'
    )
    
    if result == 'Yes':
        remove_time_warp(selected[0])

def bake_selected_time_warp():
    """Bake the selected time warp"""
    selected = mc.textScrollList('timeWarpList', query=True, selectItem=True)
    if not selected:
        mc.warning("Please select a time warp from the list to bake.")
        return
    
    result = mc.confirmDialog(
        title='Confirm Bake',
        message=f'Bake animation through {selected[0]}?\n\nThis will bake the time-warped animation\nand remove the time warp node.',
        button=['Yes', 'No'],
        defaultButton='Yes',
        cancelButton='No',
        dismissString='No'
    )
    
    if result == 'Yes':
        bake_time_warp(selected[0])
        refresh_list()
        refresh_objects_list()
        mc.confirmDialog(title='Success', message='Animation baked and time warp removed.', button=['OK'])

def refresh_list():
    """Refresh the time warp list"""
    if mc.textScrollList('timeWarpList', exists=True):
        mc.textScrollList('timeWarpList', edit=True, removeAll=True)
        time_warps = list_time_warps()
        if time_warps:
            for tw in time_warps:
                mc.textScrollList('timeWarpList', edit=True, append=tw)

def refresh_objects_list():
    """Refresh the objects list for selected time warp"""
    if not mc.textScrollList('objectsList', exists=True):
        return
    
    mc.textScrollList('objectsList', edit=True, removeAll=True)
    
    tw_selected = mc.textScrollList('timeWarpList', query=True, selectItem=True)
    if not tw_selected:
        return
    
    objects = get_objects_from_time_warp(tw_selected[0])
    if objects:
        for obj in objects:
            mc.textScrollList('objectsList', edit=True, append=obj)

def on_time_warp_selected():
    """Called when a time warp is selected from the list"""
    select_time_warp()
    refresh_objects_list()

def create_ui():
    """Create the Time Warp Tool UI"""
    # Delete existing window
    if mc.window(WINDOW_NAME, exists=True):
        mc.deleteUI(WINDOW_NAME)
    
    # Create window
    window = mc.window(WINDOW_NAME, title='Time Warp Tool', widthHeight=(350, 400))
    
    mc.columnLayout(adjustableColumn=True, rowSpacing=5, columnAttach=('both', 5))
    
    mc.text(label='', height=5)
    mc.text(label='Time Warp Nodes in Scene', font='boldLabelFont')
    mc.text(label='', height=5)
    
    # List of time warps
    mc.textScrollList('timeWarpList', numberOfRows=6, allowMultiSelection=False,
                     selectCommand=on_time_warp_selected)
    
    mc.text(label='', height=5)
    mc.text(label='Objects Affected by Selected Time Warp', font='boldLabelFont')
    mc.text(label='', height=3)
    
    # List of objects affected by time warp
    mc.textScrollList('objectsList', numberOfRows=5, allowMultiSelection=False)
    
    mc.text(label='', height=5)
    
    # Create button
    mc.button(label='Create Time Warp from Selection', 
             command=lambda x: create_time_warp_from_selection(),
             height=30, backgroundColor=[0.4, 0.6, 0.4])
    
    mc.text(label='', height=5)
    
    # Management buttons
    mc.rowColumnLayout(numberOfColumns=2, columnSpacing=[(2, 5)])
    mc.button(label='Edit Curve', command=lambda x: edit_time_warp(), height=30)
    mc.button(label='Bake & Remove', command=lambda x: bake_selected_time_warp(), height=30, backgroundColor=[0.5, 0.6, 0.7])
    mc.setParent('..')
    
    mc.text(label='', height=3)
    
    mc.rowColumnLayout(numberOfColumns=2, columnSpacing=[(2, 5)])
    mc.button(label='Remove Objects from Time Warp', command=lambda x: remove_selected_objects_from_time_warp(), height=30)
    mc.button(label='Remove Time Warp', command=lambda x: remove_selected_time_warp(), height=30, backgroundColor=[0.7, 0.4, 0.4])
    mc.setParent('..')
    
    mc.text(label='', height=10)
    mc.separator(style='in')
    mc.text(label='', height=5)
    
    # Info section
    mc.frameLayout(label='Instructions', collapsable=True, collapse=False, marginHeight=5, marginWidth=5)
    mc.columnLayout(adjustableColumn=True, rowSpacing=3)
    mc.text(label='Create:', align='left', font='boldLabelFont')
    mc.text(label='  • Select animated objects and click "Create Time Warp"', align='left')
    mc.text(label='', height=3)
    mc.text(label='Edit:', align='left', font='boldLabelFont')
    mc.text(label='  • Select time warp from list, click "Edit Curve"', align='left')
    mc.text(label='  • Modify curve in Graph Editor to remap time', align='left')
    mc.text(label='', height=3)
    mc.text(label='Remove:', align='left', font='boldLabelFont')
    mc.text(label='  • "Remove Objects" - select objects first, removes from time warp', align='left')
    mc.text(label='  • "Remove Time Warp" - removes time warp, restores connections', align='left')
    mc.text(label='  • "Bake & Remove" - bakes warped animation, removes time warp', align='left')
    mc.setParent('..')
    mc.setParent('..')
    
    mc.text(label='', height=5)
    
    # Refresh button
    mc.button(label='Refresh List', command=lambda x: refresh_list(), height=25)
    
    mc.showWindow(window)
    
    # Initial refresh
    refresh_list()

# Run the UI
if __name__ == '__main__':
    create_ui()

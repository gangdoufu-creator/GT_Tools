import maya.cmds as cmds
import json
import os

def masterCamBuilderUI():
    if cmds.window("masterCamBuilderWin", exists=True):
        cmds.deleteUI("masterCamBuilderWin")

    window = cmds.window("masterCamBuilderWin", title="Master Camera Builder", widthHeight=(400, 550))
    cmds.columnLayout(adjustableColumn=True, rowSpacing=8)

    # === Master Camera ===
    cmds.text(label="Select Master Camera:")
    master_field = cmds.textFieldButtonGrp(label="", buttonLabel="Pick", cw3=[0, 200, 60])
    cmds.textFieldButtonGrp(master_field, e=True, bc=lambda: selectCamera(master_field))

    cmds.separator(h=10, style='in')

    # === Shot Cameras ===
    cmds.text(label="Shot Cameras and Frame Ranges:")
    shot_list = cmds.textScrollList(height=120)

    # Frame range input row with handles
    cmds.rowColumnLayout(numberOfColumns=6, columnWidth=[(1, 100), (2, 60), (3, 60), (4, 55), (5, 60), (6, 60)], columnSpacing=[(1, 5), (2, 5), (3, 5), (4, 5), (5, 5), (6, 5)])
    cmds.text(label="Frame Range:")
    cmds.text(label="Start:")
    start_field = cmds.intField(value=1001, width=60)
    cmds.text(label="End:")
    end_field = cmds.intField(value=1050, width=60)
    cmds.text(label="")
    cmds.setParent('..')
    
    # Handle frames row
    cmds.rowColumnLayout(numberOfColumns=3, columnWidth=[(1, 100), (2, 60), (3, 250)], columnSpacing=[(1, 5), (2, 5), (3, 5)])
    cmds.text(label="Handle Frames:")
    handle_field = cmds.intField(value=10, width=60, annotation="Number of handle frames to exclude from start/end of animation")
    cmds.text(label="(frames to exclude from animation range)", align="left", font="smallPlainLabelFont")
    cmds.setParent('..')

    # Buttons under list
    cmds.rowLayout(numberOfColumns=3, columnWidth3=(127, 127, 127), columnAttach3=("both", "both", "both"))
    cmds.button(label="Add Camera", bgc=(0.5, 0.7, 0.5), c=lambda *_: addSelectedCameras(shot_list, start_field, end_field, handle_field))
    cmds.button(label="Edit Time Range", bgc=(0.6, 0.6, 0.8), c=lambda *_: editSelectedShot(shot_list, start_field, end_field))
    cmds.button(label="Remove Selected", c=lambda *_: removeShot(shot_list))
    cmds.setParent('..')

    # Save/Load buttons
    cmds.rowLayout(numberOfColumns=2, columnWidth2=(190, 190), columnAttach2=("both", "both"))
    cmds.button(label="Save Shot List", bgc=(0.6, 0.7, 0.6), c=lambda *_: saveShotList(shot_list))
    cmds.button(label="Load Shot List", bgc=(0.7, 0.7, 0.6), c=lambda *_: loadShotList(shot_list))
    cmds.setParent('..')

    cmds.separator(h=10, style='in')

    # === Attributes ===
    cmds.text(label="Camera Attributes to Copy:")
    attr_scroll = cmds.textScrollList(numberOfRows=8, allowMultiSelection=True)
    attrs = [
        "focalLength",
        "horizontalFilmAperture",
        "verticalFilmAperture",
        "filmFit",
        "filmTranslateH",
        "filmTranslateV",
        "focusDistance",
        "fStop",
        "depthOfField",
        "nearClipPlane",
        "farClipPlane"
    ]
    for a in attrs:
        cmds.textScrollList(attr_scroll, e=True, append=a)
    cmds.textScrollList(attr_scroll, e=True, selectIndexedItem=range(1, len(attrs)+1))

    cmds.separator(h=10, style='in')

    # === Run Button ===
    cmds.button(label="Build Master Camera", bgc=(0.4, 0.8, 0.4),
                c=lambda *_: buildMasterCamera(master_field, shot_list, attr_scroll))

    cmds.setParent('..')
    cmds.showWindow(window)


# =========================================================
# Helper functions
# =========================================================
def selectCamera(field):
    sel = cmds.ls(sl=True)
    if sel:
        cmds.textFieldButtonGrp(field, e=True, text=sel[0])
    else:
        cmds.warning("Please select a camera in the scene first.")


def addSelectedCameras(listWidget, startField, endField, handleField):
    """Add all selected cameras to the shot list in selection order"""
    sel = cmds.ls(sl=True, type='transform')
    if not sel:
        cmds.warning("Please select one or more cameras to add.")
        return
    
    # Get manual frame values as fallback
    manual_start = cmds.intField(startField, q=True, value=True)
    manual_end = cmds.intField(endField, q=True, value=True)
    handle_frames = cmds.intField(handleField, q=True, value=True)
    
    added_count = 0
    for cam in sel:
        # Check if it's a camera or has a camera shape
        shapes = cmds.listRelatives(cam, shapes=True, type='camera') or []
        if not shapes:
            cmds.warning(f"{cam} is not a camera, skipping.")
            continue
        
        # Try to auto-detect frame range from animation
        start, end = get_camera_animation_range(cam, handle_frames)
        
        # If no animation found, use manual values
        if start is None or end is None:
            start = manual_start
            end = manual_end
            print(f"No animation found on {cam}, using manual range: {start}-{end}")
        else:
            print(f"Auto-detected range for {cam}: {start}-{end} (with {handle_frames} frame handles)")
            # Update the UI fields with the detected range for reference
            cmds.intField(startField, e=True, value=start)
            cmds.intField(endField, e=True, value=end)
        
        entry = f"{cam} | {start}-{end}"
        cmds.textScrollList(listWidget, e=True, append=entry)
        added_count += 1
    
    if added_count > 0:
        print(f"Added {added_count} camera(s) to the shot list.")
    else:
        cmds.warning("No cameras were added. Please select camera transforms.")


def get_camera_animation_range(cam, handle_frames=0):
    """
    Get the animation range for a camera based on its transform keyframes.
    Returns (start, end) with handles applied, or (None, None) if no animation found.
    
    Logic:
    - First keyframe + handles = start frame
    - Last keyframe - handles = end frame
    """
    # Attributes to check for animation
    transform_attrs = [
        'translateX', 'translateY', 'translateZ',
        'rotateX', 'rotateY', 'rotateZ'
    ]
    
    all_keys = []
    
    # Collect all keyframe times from transform attributes
    for attr in transform_attrs:
        attr_name = f"{cam}.{attr}"
        if cmds.objExists(attr_name):
            # Check if there's an animation curve connected (works even if locked)
            connections = cmds.listConnections(attr_name, source=True, destination=False, type='animCurve')
            if connections:
                anim_curve = connections[0]
                # Query keyframes directly from the animation curve
                keys = cmds.keyframe(anim_curve, query=True, timeChange=True)
                if keys:
                    all_keys.extend(keys)
                    print(f"DEBUG: Found {len(keys)} keys on {attr} (via {anim_curve})")
    
    if not all_keys:
        print(f"DEBUG: No animation keys found on {cam}")
        return None, None
    
    # Get the first and last keyframe
    first_key = int(min(all_keys))
    last_key = int(max(all_keys))
    
    print(f"DEBUG: {cam} - First key: {first_key}, Last key: {last_key}, Handles: {handle_frames}")
    
    # Apply handle logic:
    # Start = first keyframe + handles
    # End = last keyframe - handles
    start_frame = first_key + handle_frames
    end_frame = last_key - handle_frames
    
    # Make sure we have a valid range
    if start_frame >= end_frame:
        cmds.warning(f"{cam}: Handle frames ({handle_frames}) result in invalid range. First key: {first_key}, Last key: {last_key}")
        # Return the raw range without handles
        return first_key, last_key
    
    print(f"DEBUG: {cam} - Calculated range: {start_frame} to {end_frame}")
    return start_frame, end_frame


def removeShot(listWidget):
    selected = cmds.textScrollList(listWidget, q=True, si=True)
    if selected:
        for item in selected:
            cmds.textScrollList(listWidget, e=True, removeItem=item)


def saveShotList(listWidget):
    """Save the shot list to a JSON file"""
    all_items = cmds.textScrollList(listWidget, q=True, allItems=True) or []
    
    print(f"DEBUG: Found {len(all_items)} items in list")
    for item in all_items:
        print(f"  - {item}")
    
    if not all_items:
        cmds.warning("No shots to save.")
        return
    
    # Parse shots into structured data
    shots = []
    for item in all_items:
        try:
            cam, frame_range = item.split("|")
            cam = cam.strip()
            start, end = [int(x) for x in frame_range.strip().split("-")]
            shots.append({'camera': cam, 'start': start, 'end': end})
            print(f"DEBUG: Parsed - Camera: {cam}, Start: {start}, End: {end}")
        except Exception as e:
            cmds.warning(f"Could not parse entry: {item} - Error: {e}")
            continue
    
    if not shots:
        cmds.warning("No valid shots to save.")
        return
    
    # Get save file path
    file_path = cmds.fileDialog2(
        dialogStyle=2,  # Use OS native dialog
        fileMode=0,  # Any file (new or existing)
        caption="Save Shot List",
        fileFilter="JSON Files (*.json);;All Files (*.*)",
        startingDirectory=cmds.workspace(query=True, directory=True)
    )
    
    if not file_path:
        print("DEBUG: User cancelled file dialog")
        return
    
    file_path = file_path[0]
    
    # Ensure .json extension
    if not file_path.lower().endswith('.json'):
        file_path += '.json'
    
    print(f"DEBUG: Saving to: {file_path}")
    
    # Save to JSON
    try:
        with open(file_path, 'w') as f:
            json.dump(shots, f, indent=4)
        print(f"✅ Saved {len(shots)} shots to: {file_path}")
        cmds.inViewMessage(amg=f"✅ Saved {len(shots)} shots", pos="midCenter", fade=True)
    except Exception as e:
        cmds.error(f"Failed to save shot list: {e}")


def loadShotList(listWidget):
    """Load a shot list from a JSON file"""
    # Get load file path
    file_path = cmds.fileDialog2(
        dialogStyle=2,  # Use OS native dialog
        fileMode=1,  # Single existing file
        caption="Load Shot List",
        fileFilter="JSON Files (*.json);;All Files (*.*)",
        startingDirectory=cmds.workspace(query=True, directory=True)
    )
    
    if not file_path:
        print("DEBUG: User cancelled file dialog")
        return
    
    file_path = file_path[0]
    print(f"DEBUG: Loading from: {file_path}")
    
    if not os.path.exists(file_path):
        cmds.warning(f"File does not exist: {file_path}")
        return
    
    # Load from JSON
    try:
        with open(file_path, 'r') as f:
            shots = json.load(f)
        
        print(f"DEBUG: Loaded {len(shots)} shots from JSON")
        for shot in shots:
            print(f"  - Camera: {shot.get('camera')}, Start: {shot.get('start')}, End: {shot.get('end')}")
        
        # Clear existing list
        cmds.textScrollList(listWidget, e=True, removeAll=True)
        
        # Add shots to list
        loaded_count = 0
        for shot in shots:
            cam = shot.get('camera', '')
            start = shot.get('start', 1001)
            end = shot.get('end', 1050)
            entry = f"{cam} | {start}-{end}"
            cmds.textScrollList(listWidget, e=True, append=entry)
            loaded_count += 1
            print(f"DEBUG: Added to list: {entry}")
        
        print(f"✅ Loaded {loaded_count} shots from: {file_path}")
        cmds.inViewMessage(amg=f"✅ Loaded {loaded_count} shots", pos="midCenter", fade=True)
    except Exception as e:
        cmds.error(f"Failed to load shot list: {e}")


def editSelectedShot(listWidget, startField, endField):
    """Edit the frame range of the selected shot in the list"""
    selected = cmds.textScrollList(listWidget, q=True, selectItem=True)
    if not selected or len(selected) != 1:
        cmds.warning("Please select exactly one shot to edit.")
        return
    
    selected_index = cmds.textScrollList(listWidget, q=True, selectIndexedItem=True)[0]
    entry = selected[0]
    
    try:
        cam, frame_range = entry.split("|")
        cam = cam.strip()
    except:
        cmds.warning(f"Could not parse entry: {entry}")
        return
    
    # Get new frame values
    new_start = cmds.intField(startField, q=True, value=True)
    new_end = cmds.intField(endField, q=True, value=True)
    
    # Create updated entry
    new_entry = f"{cam} | {new_start}-{new_end}"
    
    # Get all items
    all_items = cmds.textScrollList(listWidget, q=True, allItems=True) or []
    
    # Update the item at the selected index
    all_items[selected_index - 1] = new_entry
    
    # Clear and repopulate the list
    cmds.textScrollList(listWidget, e=True, removeAll=True)
    for item in all_items:
        cmds.textScrollList(listWidget, e=True, append=item)
    
    # Reselect the edited item
    cmds.textScrollList(listWidget, e=True, selectIndexedItem=selected_index)
    
    print(f"Updated shot: {new_entry}")


def get_shape(cam):
    shapes = cmds.listRelatives(cam, shapes=True, fullPath=True) or []
    return shapes[0] if shapes else None


def buildMasterCamera(master_field, shot_list, attr_scroll):
    master_cam = cmds.textFieldButtonGrp(master_field, q=True, text=True)
    if not master_cam:
        cmds.warning("Please specify a master camera.")
        return

    master_shape = get_shape(master_cam)
    if not master_shape:
        cmds.warning("Master camera has no shape node.")
        return

    entries = cmds.textScrollList(shot_list, q=True, allItems=True) or []
    if not entries:
        cmds.warning("No shots defined.")
        return

    selected_attrs = cmds.textScrollList(attr_scroll, q=True, si=True) or []

    # Clear any existing animation on master camera
    cmds.cutKey(master_cam, clear=True)
    if master_shape:
        cmds.cutKey(master_shape, clear=True)

    # Parse and validate all entries first
    shot_data = []
    for entry in entries:
        try:
            cam, frame_range = entry.split("|")
            cam = cam.strip()
            start, end = [int(x) for x in frame_range.strip().split("-")]
        except:
            cmds.warning(f"Could not parse entry: {entry}")
            continue

        # Check if camera exists
        if not cmds.objExists(cam):
            cmds.warning(f"Camera '{cam}' does not exist in the scene. Skipping.")
            continue

        shot_shape = get_shape(cam)
        if not shot_shape:
            cmds.warning(f"{cam} has no shape node, skipping.")
            continue
            
        shot_data.append({'cam': cam, 'shape': shot_shape, 'start': start, 'end': end})

    if not shot_data:
        cmds.warning("No valid shots to process.")
        return

    print(f"\n{'='*60}")
    print(f"Building Master Camera - {len(shot_data)} shots")
    print(f"{'='*60}")

    # Disable viewport refresh for faster processing
    cmds.refresh(suspend=True)
    
    try:
        # === Process each camera once ===
        for i, shot in enumerate(shot_data):
            cam = shot['cam']
            shot_shape = shot['shape']
            start = shot['start']
            end = shot['end']
            
            print(f"\nShot {i+1}/{len(shot_data)}: {cam} (frames {start}-{end})")
            
            # Create constraint
            constraint = cmds.parentConstraint(cam, master_cam, maintainOffset=False)[0]
            
            # Bake transforms for this frame range (one pass only)
            cmds.bakeResults(
                master_cam,
                time=(start, end),
                sampleBy=1,
                simulation=False,  # Changed to False - faster, no physics simulation needed
                preserveOutsideKeys=True,
                sparseAnimCurveBake=False,
                removeBakedAnimFromLayer=False,
                bakeOnOverrideLayer=False,
                minimizeRotation=True,
                controlPoints=False,
                shape=False
            )
            
            # Delete constraint immediately
            cmds.delete(constraint)
            
            # Copy camera attributes for this range
            if selected_attrs:
                for attr in selected_attrs:
                    try:
                        source_attr = f"{shot_shape}.{attr}"
                        target_attr = f"{master_shape}.{attr}"
                        
                        # Check if the attribute has animation
                        anim_curve = cmds.listConnections(source_attr, type='animCurve', source=True, destination=False)
                        
                        if anim_curve:
                            # Attribute is animated - copy all keyframes in the range
                            all_keys = cmds.keyframe(source_attr, query=True, time=(start, end), timeChange=True)
                            
                            if all_keys:
                                for frame in all_keys:
                                    value = cmds.keyframe(source_attr, query=True, time=(frame, frame), eval=True)[0]
                                    cmds.setKeyframe(target_attr, time=frame, value=value)
                                print(f"  ✓ Copied {len(all_keys)} keyframes for {attr}")
                        else:
                            # Attribute is NOT animated - set constant value with stepped tangent
                            static_value = cmds.getAttr(source_attr)
                            cmds.setKeyframe(target_attr, time=start, value=static_value)
                            cmds.keyTangent(target_attr, time=(start, start), outTangentType='step')
                            print(f"  ✓ Set static {attr} = {static_value}")
                            
                    except Exception as e:
                        print(f"  ⚠ Warning: Could not copy attribute {attr}: {e}")
    
    finally:
        # Re-enable viewport refresh
        cmds.refresh(suspend=False)
        cmds.refresh()

    print(f"\n{'='*60}")
    print(f"✅ Master camera build complete! Processed {len(shot_data)} shots.")
    print(f"{'='*60}\n")
    
    cmds.inViewMessage(amg="✅ Master camera built successfully!", pos="midCenter", fade=True)


# =========================================================
# Run it
# =========================================================
masterCamBuilderUI()

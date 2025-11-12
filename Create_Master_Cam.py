import maya.cmds as cmds

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

    # Shot input row
    cmds.rowColumnLayout(numberOfColumns=7, columnWidth=[(1, 55), (2, 90), (3, 40), (4, 45), (5, 60), (6, 45), (7, 60)], columnSpacing=[(1, 5), (2, 5), (3, 5), (4, 5), (5, 5), (6, 5), (7, 5)])
    cmds.text(label="Shot Cam:")
    shot_cam_field = cmds.textField()
    cmds.button(label="Pick", width=40, c=lambda *_: pickShotCamera(shot_cam_field))
    cmds.text(label="Start:")
    start_field = cmds.intField(value=1001)
    cmds.text(label="End:")
    end_field = cmds.intField(value=1050)
    cmds.setParent('..')

    # Buttons under list
    cmds.rowLayout(numberOfColumns=4, columnWidth4=(95, 95, 95, 95), columnAttach4=("both", "both", "both", "both"))
    cmds.button(label="Add Shot", c=lambda *_: addShot(shot_list, shot_cam_field, start_field, end_field))
    cmds.button(label="Add Selected", bgc=(0.5, 0.7, 0.5), c=lambda *_: addSelectedCameras(shot_list, start_field, end_field))
    cmds.button(label="Edit Selected", bgc=(0.6, 0.6, 0.8), c=lambda *_: editSelectedShot(shot_list, start_field, end_field))
    cmds.button(label="Remove Selected", c=lambda *_: removeShot(shot_list))
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


def pickShotCamera(field):
    sel = cmds.ls(sl=True)
    if sel:
        cmds.textField(field, e=True, text=sel[0])
    else:
        cmds.warning("Please select a camera in the scene first.")


def addShot(listWidget, camField, startField, endField):
    cam = cmds.textField(camField, q=True, text=True)
    start = cmds.intField(startField, q=True, value=True)
    end = cmds.intField(endField, q=True, value=True)
    if cam:
        entry = f"{cam} | {start}-{end}"
        cmds.textScrollList(listWidget, e=True, append=entry)
    else:
        cmds.warning("Enter a camera name first.")


def addSelectedCameras(listWidget, startField, endField):
    """Add all selected cameras to the shot list in selection order"""
    sel = cmds.ls(sl=True, type='transform')
    if not sel:
        cmds.warning("Please select one or more cameras to add.")
        return
    
    start = cmds.intField(startField, q=True, value=True)
    end = cmds.intField(endField, q=True, value=True)
    
    added_count = 0
    for cam in sel:
        # Check if it's a camera or has a camera shape
        shapes = cmds.listRelatives(cam, shapes=True, type='camera') or []
        if shapes:
            entry = f"{cam} | {start}-{end}"
            cmds.textScrollList(listWidget, e=True, append=entry)
            added_count += 1
        else:
            cmds.warning(f"{cam} is not a camera, skipping.")
    
    if added_count > 0:
        print(f"Added {added_count} camera(s) to the shot list.")
    else:
        cmds.warning("No cameras were added. Please select camera transforms.")


def removeShot(listWidget):
    selected = cmds.textScrollList(listWidget, q=True, si=True)
    if selected:
        for item in selected:
            cmds.textScrollList(listWidget, e=True, removeItem=item)


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

    # Process each shot - constrain, bake, delete constraint individually
    for i, shot in enumerate(shot_data):
        cam = shot['cam']
        shot_shape = shot['shape']
        start = shot['start']
        end = shot['end']
        
        print(f"Processing shot {i+1}/{len(shot_data)}: {cam} (frames {start}-{end})")
        
        # Create parent constraint
        constraint = cmds.parentConstraint(cam, master_cam, maintainOffset=False)[0]
        
        # Bake just this frame range
        cmds.bakeResults(
            master_cam,
            time=(start, end),
            sampleBy=1,
            simulation=True,
            preserveOutsideKeys=True,
            sparseAnimCurveBake=False,
            removeBakedAnimFromLayer=False,
            bakeOnOverrideLayer=False,
            minimizeRotation=True,
            controlPoints=False,
            shape=False
        )
        
        # Delete constraint
        cmds.delete(constraint)
        
        # Handle camera attributes - copy all keyframes or bake if animated
        if selected_attrs:
            for attr in selected_attrs:
                try:
                    source_attr = f"{shot_shape}.{attr}"
                    target_attr = f"{master_shape}.{attr}"
                    
                    # Check if the attribute has animation
                    anim_curve = cmds.listConnections(source_attr, type='animCurve', source=True, destination=False)
                    
                    if anim_curve:
                        # Attribute is animated - copy all keyframes in the range
                        print(f"  Copying animated {attr} from {cam}")
                        
                        # Get all keyframes from source in this range
                        all_keys = cmds.keyframe(source_attr, query=True, time=(start, end), timeChange=True)
                        
                        if all_keys:
                            for frame in all_keys:
                                cmds.currentTime(frame)
                                value = cmds.getAttr(source_attr)
                                cmds.setKeyframe(target_attr, time=frame, value=value)
                    else:
                        # Attribute is NOT animated - set constant value for entire range
                        static_value = cmds.getAttr(source_attr)
                        print(f"  Setting static {attr} = {static_value} for frames {start}-{end}")
                        
                        # Set keyframe at start with the value
                        cmds.setKeyframe(target_attr, time=start, value=static_value)
                        
                        # Set stepped tangent so it holds the value (no interpolation)
                        cmds.keyTangent(target_attr, time=(start, start), outTangentType='step')
                        
                except Exception as e:
                    print(f"Warning: Could not copy attribute {attr}: {e}")

    cmds.inViewMessage(amg="✅ Master camera built successfully!", pos="midCenter", fade=True)
    print("✅ Master camera build complete!")
    print(f"Processed {len(shot_data)} shots total.")


# =========================================================
# Run it
# =========================================================
masterCamBuilderUI()

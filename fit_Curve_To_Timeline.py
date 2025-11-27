import maya.cmds as cmds

def contain_curve_within_time_range():
    """
    Takes a cyclical animation curve that exists outside the time range and 
    recreates it within the time range using copy/paste operations similar to the MEL workflow.
    
    This maintains the exact same animation look but creates real keys within the time range.
    Works on the currently selected channel in the Graph Editor.
    """
    
    # Get the current time range
    start_time = int(cmds.playbackOptions(query=True, minTime=True))
    end_time = int(cmds.playbackOptions(query=True, maxTime=True))
    
    print(f"Time range: {start_time} to {end_time}")
    
    # Get selected curves from Graph Editor
    selected_curves = cmds.keyframe(query=True, selected=True, name=True)
    
    if not selected_curves:
        cmds.warning("No animation curves selected in Graph Editor. Please select a curve.")
        return
    
    if len(selected_curves) > 1:
        cmds.warning("Multiple curves selected. Please select only one curve for this operation.")
        return
    
    curve_name = selected_curves[0]
    print(f"Processing curve: {curve_name}")
    
    # Get all keyframes on the curve
    all_times = cmds.keyframe(curve_name, query=True, timeChange=True)
    
    if not all_times:
        cmds.warning(f"No keyframes found on curve {curve_name}")
        return
    
    print(f"Original curve has {len(all_times)} keyframes from {min(all_times)} to {max(all_times)}")
    
    # First, ensure there's a keyframe at the end of the time range
    # This will sample the curve value at that time and create a key
    print(f"Setting keyframe at end of time range: {end_time}")
    try:
        cmds.setKeyframe(curve_name, time=end_time)
        print(f"Created keyframe at frame {end_time}")
    except Exception as e:
        cmds.warning(f"Failed to set keyframe at end time: {e}")
        return
    
    # Refresh the keyframe list to include the new key
    all_times = cmds.keyframe(curve_name, query=True, timeChange=True)
    print(f"Updated curve has {len(all_times)} keyframes")
    
    # Find keyframes that are at the end of time range and beyond
    keys_to_copy = []
    for time in all_times:
        if time >= end_time:
            keys_to_copy.append(int(time))
    
    if not keys_to_copy:
        print("No keyframes found at or beyond the end of the time range")
        return
    
    print(f"Found {len(keys_to_copy)} keyframes to copy: {keys_to_copy}")
    
    # Clear any existing selection
    cmds.selectKey(clear=True)
    
    # Select the keyframes we want to copy (from end_time onwards)
    for key_time in keys_to_copy:
        cmds.selectKey(curve_name, add=True, time=(key_time, key_time))
    
    print(f"Selected keyframes at times: {keys_to_copy}")
    
    # Copy the selected keyframes
    try:
        cmds.copyKey()
        print("Copied keyframes")
    except Exception as e:
        cmds.warning(f"Failed to copy keyframes: {e}")
        return
    
    # Set current time to start of range for pasting (like your MEL: currentTime 1000)
    cmds.currentTime(start_time)
    print(f"Set current time to {start_time}")
    
    # Paste the keyframes at current time with merge option (like your MEL)
    # This mimics: pasteKey -time 1000 -float 1000 -option merge -copies 1 -connect 0 -timeOffset 0 -floatOffset 0 -valueOffset 0 -selectPasted 1
    try:
        cmds.pasteKey(
            time=(start_time, start_time),  # Maya expects tuple format
            float=(start_time, start_time),  # Maya expects tuple format
            option="merge",
            copies=1,
            connect=False,
            timeOffset=0,  # No time offset, let Maya handle the positioning
            floatOffset=0,
            valueOffset=0,
            selectPasted=True
        )
        print(f"Pasted keyframes at current time {start_time}")
    except Exception as e:
        cmds.warning(f"Failed to paste keyframes: {e}")
        return
    
    # Now remove the original keyframes that were outside the time range
    # Clear selection first
    cmds.selectKey(clear=True)
    
    # Select keyframes beyond the end time (but not including end_time if it has a key we want to keep)
    keys_beyond_range = []
    for time in all_times:
        if time > end_time:  # Only keys BEYOND the end time
            keys_beyond_range.append(int(time))
    
    if keys_beyond_range:
        print(f"Removing keyframes beyond time range: {keys_beyond_range}")
        
        # Select and delete these keyframes
        for key_time in keys_beyond_range:
            cmds.selectKey(curve_name, add=True, time=(key_time, key_time))
        
        try:
            cmds.cutKey(animation="keys", clear=True)
            print("Removed keyframes beyond time range")
        except Exception as e:
            print(f"Warning: Could not remove some keyframes: {e}")
    
    # Set infinity to cycle for the curve
    try:
        cmds.selectKey(clear=True)
        cmds.selectKey(curve_name, add=True)
        cmds.setInfinity(preInfinity="cycle", postInfinity="cycle")
        print("Set infinity to cycle")
    except Exception as e:
        print(f"Warning: Could not set infinity: {e}")
    
    print("Successfully contained curve within time range using copy/paste method")

# Run the function
if __name__ == "__main__":
    contain_curve_within_time_range()
